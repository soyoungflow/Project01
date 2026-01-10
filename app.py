# app.py
# 역할: Streamlit UI 담당 (입력/필터/표/차트/예산 관제)
# 모든 MVP 기능 및 선택 기능 구현 완료

import os
import json
from copy import deepcopy
from datetime import date

import pandas as pd
import streamlit as st
import plotly.express as px

# ledger 패키지에서 필요한 함수들 import
from ledger.services import (
    calc_summary,
    calc_detailed_summary,
    calc_category_expense,
    calc_budget_status,
)
from ledger.utils import format_currency

# =============================
# (0) 기본 설정
# =============================
st.set_page_config(page_title="나만의 미니 가계부", layout="wide")

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

DATA_PATH = os.path.join(DATA_DIR, "ledger.csv")
BUDGET_PATH = os.path.join(DATA_DIR, "budgets.json")


# =============================
# (1) 파일 처리 함수들 (F4. 저장/불러오기)
# =============================
def _ensure_ledger_file_exists() -> None:
    """CSV가 없으면 빈 CSV를 만들어서 앱이 항상 정상 실행되게 한다."""
    if not os.path.exists(DATA_PATH):
        # 헤더만 있는 CSV 파일 생성
        with open(DATA_PATH, 'w', encoding='utf-8-sig') as f:
            f.write("date,type,category,description,amount\n")
    else:
        # 파일이 비어있는지 확인
        if os.path.getsize(DATA_PATH) == 0:
            with open(DATA_PATH, 'w', encoding='utf-8-sig') as f:
                f.write("date,type,category,description,amount\n")


def load_df() -> pd.DataFrame:
    """CSV에서 거래 데이터를 읽어온다."""
    _ensure_ledger_file_exists()

    try:
        df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        # 파일이 비어있으면 헤더만 다시 쓰고 빈 DataFrame 반환
        with open(DATA_PATH, 'w', encoding='utf-8-sig') as f:
            f.write('date,type,category,description,amount\n')
        df = pd.DataFrame(columns=["date", "type", "category", "description", "amount"])
    except UnicodeDecodeError:
        try:
            df = pd.read_csv(DATA_PATH, encoding="utf-8")
        except:
            # 어떤 인코딩도 안되면 새로 생성
            with open(DATA_PATH, 'w', encoding='utf-8-sig') as f:
                f.write('date,type,category,description,amount\n')
            df = pd.DataFrame(columns=["date", "type", "category", "description", "amount"])
    except Exception as e:
        # 그 외 모든 오류는 새 DataFrame으로
        st.warning(f"CSV 파일 읽기 오류: {e}. 새로운 파일을 생성합니다.")
        with open(DATA_PATH, 'w', encoding='utf-8-sig') as f:
            f.write('date,type,category,description,amount\n')
        df = pd.DataFrame(columns=["date", "type", "category", "description", "amount"])

    # 컬럼 보정
    for col in ["date", "type", "category", "description", "amount"]:
        if col not in df.columns:
            df[col] = None

    # 타입 정리
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["type"] = df["type"].astype(str).fillna("")
    df["category"] = df["category"].astype(str).fillna("")
    df["description"] = df["description"].astype(str).fillna("")
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0).astype(int)

    # 날짜 최신순 정렬
    df = df.sort_values(["date"], ascending=[False]).reset_index(drop=True)
    return df


def save_df(df: pd.DataFrame) -> None:
    """CSV로 저장한다."""
    if df is None or len(df) == 0:
        # 빈 DataFrame이면 헤더만 저장
        with open(DATA_PATH, 'w', encoding='utf-8-sig', newline='') as f:
            f.write('date,type,category,description,amount\n')
        return
    
    out = df.copy()
    
    # 날짜 처리: 이미 date 타입이면 그대로, 아니면 변환
    if not out["date"].empty:
        if pd.api.types.is_object_dtype(out["date"]) or pd.api.types.is_datetime64_any_dtype(out["date"]):
            out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.date
    
    out["type"] = out["type"].astype(str).fillna("")
    out["category"] = out["category"].astype(str).fillna("")
    out["description"] = out["description"].astype(str).fillna("")
    out["amount"] = pd.to_numeric(out["amount"], errors="coerce").fillna(0).astype(int)
    
    # CSV 저장 (newline='' 추가로 줄바꿈 문제 방지)
    out.to_csv(DATA_PATH, index=False, encoding="utf-8-sig", lineterminator='\n')
    
    # 저장 확인 (디버깅용)
    if os.path.exists(DATA_PATH):
        size = os.path.getsize(DATA_PATH)
        if size > 50:  # 헤더만 있으면 약 40바이트
            # 정상 저장됨
            pass


def load_budgets() -> dict:
    """예산 설정을 JSON에서 읽어온다."""
    if not os.path.exists(BUDGET_PATH):
        return {"전체": 0, "식비": 0, "교통": 0, "통신": 0, "생활": 0, "기타": 0}

    try:
        with open(BUDGET_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}

    base = {"전체": 0, "식비": 0, "교통": 0, "통신": 0, "생활": 0, "기타": 0}
    base.update({k: int(v) if str(v).isdigit() else 0 for k, v in data.items()})
    return base


def save_budgets(budgets: dict) -> None:
    """예산 설정을 JSON으로 저장한다."""
    with open(BUDGET_PATH, "w", encoding="utf-8") as f:
        json.dump(budgets, f, ensure_ascii=False, indent=2)


# =============================
# (2) 세션 히스토리 관리 (Undo 기능)
# =============================
def push_history():
    """Undo를 위해 현재 df를 히스토리에 저장한다."""
    st.session_state["history"].append(deepcopy(st.session_state["df"]))


def pop_history():
    """Undo 실행: 히스토리에서 되돌린다."""
    if st.session_state["history"]:
        st.session_state["df"] = st.session_state["history"].pop()
        save_df(st.session_state["df"])


# =============================
# (3) 세션 초기화
# =============================
if "df" not in st.session_state:
    st.session_state["df"] = load_df()

if "history" not in st.session_state:
    st.session_state["history"] = []

if "budgets" not in st.session_state:
    st.session_state["budgets"] = load_budgets()


# =============================
# (4) 다크 테마 CSS
# =============================
st.markdown(
    """
<style>
.stApp {
  background: radial-gradient(1200px 700px at 35% 0%, rgba(130, 88, 255, 0.35), rgba(10, 12, 18, 0.98) 60%);
  color: #EDEDF4;
}

/* 전역 텍스트 색상 */
h1, h2, h3, h4, h5, h6, p, div, span, label {
  color: #EDEDF4 !important;
}

/* Selectbox 팝업 메뉴만 검은색 강제 적용 */
[class*="st-emotion-cache"] [role="listbox"],
[class*="st-emotion-cache"] [role="listbox"] *,
ul[role="listbox"],
ul[role="listbox"] *,
div[data-baseweb="popover"],
div[data-baseweb="popover"] * {
  color: #1E1E1E !important;
}

:root {
  --box-bg: rgba(58, 61, 70, 0.78);
  --box-border: rgba(210, 210, 230, 0.18);
  --box-radius: 26px;
  --input-text-color: #1E1E1E;  /* 어두운 글자색 */
}

/* Text Input, Number Input, Date Input */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stDateInput"] input {
  background: rgba(255, 255, 255, 0.95) !important;  /* 밝은 배경 */
  border: 1px solid var(--box-border) !important;
  border-radius: var(--box-radius) !important;
  color: var(--input-text-color) !important;  /* 어두운 글자 */
  font-weight: 500;
}

/* Placeholder 텍스트도 보이게 */
div[data-testid="stTextInput"] input::placeholder,
div[data-testid="stNumberInput"] input::placeholder {
  color: rgba(30, 30, 30, 0.5) !important;
  opacity: 1;
}

/* Select Box (드롭다운) */
div[data-baseweb="select"] > div {
  background: rgba(255, 255, 255, 0.95) !important;  /* 밝은 배경 */
  border: 1px solid var(--box-border) !important;
  border-radius: var(--box-radius) !important;
  color: var(--input-text-color) !important;  /* 어두운 글자 */
}

/* Select Box 내부 텍스트 */
div[data-baseweb="select"] span {
  color: var(--input-text-color) !important;
}

div[data-baseweb="select"] * {
  color: var(--input-text-color) !important;
}

/* Select Box 드롭다운 메뉴 - 더 구체적으로 */
div[role="listbox"] {
  background: rgba(255, 255, 255, 0.98) !important;
}

div[role="listbox"] * {
  color: var(--input-text-color) !important;
}

/* 드롭다운 옵션들 - 모든 가능한 선택자 */
div[role="option"],
li[role="option"],
div[data-baseweb="menu-item"],
ul[role="listbox"] li,
div[role="listbox"] > div,
div[role="listbox"] li {
  color: var(--input-text-color) !important;  /* 검은색 글자 */
  background: transparent !important;
}

div[role="option"] *,
li[role="option"] *,
div[data-baseweb="menu-item"] * {
  color: var(--input-text-color) !important;
}

div[role="option"]:hover,
li[role="option"]:hover,
div[data-baseweb="menu-item"]:hover {
  background: rgba(130, 88, 255, 0.15) !important;
  color: var(--input-text-color) !important;  /* hover 시에도 검은색 */
}

div[role="option"]:hover *,
li[role="option"]:hover *,
div[data-baseweb="menu-item"]:hover * {
  color: var(--input-text-color) !important;
}

/* 선택된 옵션 */
div[role="option"][aria-selected="true"],
li[role="option"][aria-selected="true"],
div[data-baseweb="menu-item"][aria-selected="true"] {
  background: rgba(130, 88, 255, 0.25) !important;
  color: var(--input-text-color) !important;
}

div[role="option"][aria-selected="true"] *,
li[role="option"][aria-selected="true"] *,
div[data-baseweb="menu-item"][aria-selected="true"] * {
  color: var(--input-text-color) !important;
}

/* 헤더 영역 스타일 추가 */
.stApp > header {
  background: transparent !important;
}

/* Streamlit 기본 헤더 숨기기 */
header[data-testid="stHeader"] {
  background: transparent !important;
}

/* 메인 컨텐츠 영역 */
.main .block-container {
  padding-top: 2rem;
}

/* Sidebar */
section[data-testid="stSidebar"] {
  background: rgba(10, 12, 18, 0.55) !important;
}

/* 사이드바 Input도 밝은 배경 */
section[data-testid="stSidebar"] div[data-testid="stTextInput"] input,
section[data-testid="stSidebar"] div[data-testid="stDateInput"] input {
  background: rgba(255, 255, 255, 0.95) !important;
  color: var(--input-text-color) !important;
}

section[data-testid="stSidebar"] div[data-baseweb="select"] > div {
  background: rgba(255, 255, 255, 0.95) !important;
  color: var(--input-text-color) !important;
}

section[data-testid="stSidebar"] div[data-baseweb="select"] span {
  color: var(--input-text-color) !important;
}

/* Button */
.stButton > button {
  border-radius: 18px;
  padding: 10px 16px;
  border: 1px solid rgba(160,120,255,0.35);
  background: rgba(128, 77, 255, 0.35);
  color: #EDEDF4;
  font-weight: 700;
}

.stButton > button:hover {
  background: rgba(128, 77, 255, 0.55);
  border: 1px solid rgba(160,120,255,0.55);
}
</style>
""",
    unsafe_allow_html=True,
)


# =============================
# (5) 헤더
# =============================
st.markdown(
    """
<div style="
  display:flex; 
  align-items:flex-start; 
  gap:14px; 
  margin-bottom:20px;
  padding: 24px 32px;
  background: linear-gradient(135deg, rgba(130, 88, 255, 0.15), rgba(85, 60, 200, 0.08));
  border-radius: 20px;
  border: 1px solid rgba(160, 120, 255, .25);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.2);
">
  <div style="font-size:46px; line-height:1;">🧾</div>
  <div>
    <div style="font-size:44px; font-weight:900; letter-spacing:-0.6px; color:#EDEDF4;">나만의 미니 가계부</div>
    <div style="opacity:0.75; margin-top:4px; color:#EDEDF4;">✅ 모든 MVP 및 선택 기능 구현 완료</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)


# =============================
# (6) 사이드바 필터 (D1. 기간 필터 + D2. 메모 검색)
# =============================
with st.sidebar:
    st.markdown("## 🔎 필터")

    # D1. 기간 필터
    today = pd.Timestamp.today().date()
    start_date, end_date = st.date_input(
        "기간 선택",
        value=(today, today),
        help="이 기간에 해당하는 데이터만 보여줍니다.",
    )

    # D2. 메모 검색 (키워드 필터)
    keyword = st.text_input("검색어", value="", placeholder="예) 점심, 지하철 ...")
    
    type_filter = st.selectbox("구분", ["전체", "지출", "수입"], index=0)

    # 카테고리 목록
    base_categories = ["식비", "교통", "통신", "생활", "기타"]
    data_categories = sorted([c for c in st.session_state["df"]["category"].unique().tolist() if c])
    categories = ["전체"] + sorted(list(set(base_categories + data_categories)))
    category_filter = st.selectbox("카테고리", categories, index=0)


# =============================
# (7) 필터 적용
# =============================
df_all = st.session_state["df"].copy()
df_all["번호"] = range(len(df_all))

# D1. 기간 필터 적용
df_f = df_all.dropna(subset=["date"]).copy()
df_f = df_f[(df_f["date"] >= start_date) & (df_f["date"] <= end_date)].copy()

# 구분 필터
if type_filter != "전체":
    df_f = df_f[df_f["type"] == type_filter].copy()

# 카테고리 필터
if category_filter != "전체":
    df_f = df_f[df_f["category"] == category_filter].copy()

# D2. 메모 검색 (키워드 필터)
if keyword.strip():
    df_f = df_f[df_f["description"].astype(str).str.contains(keyword.strip(), na=False)].copy()

# 화면용 컬럼명
df_view = df_f.rename(
    columns={
        "date": "날짜",
        "type": "구분",
        "category": "카테고리",
        "description": "내용",
        "amount": "금액",
    }
)[["번호", "날짜", "구분", "카테고리", "내용", "금액"]].copy()


# =============================
# (8) F1. 새 거래 등록 (입력 기능)
# =============================
st.markdown("### ➕ 새 거래 등록")

col_a, col_b, col_c = st.columns([1.4, 1.0, 1.0])
with col_a:
    in_date = st.date_input("날짜", value=today)
with col_b:
    in_type = st.selectbox("구분", ["지출", "수입"], index=0, key="input_type")
with col_c:
    in_category = st.selectbox("카테고리", ["식비", "교통", "통신", "생활", "기타"], index=0, key="input_category")

in_desc = st.text_input("내용", value="", placeholder="예) 지하철 / 점심 / 통신요금 ...")
in_amount = st.number_input("금액(원)", min_value=0, step=1000, value=0)

if st.button("등록", key="register_btn"):
    # 금액 검증 (요구사항: 숫자가 아니면 추가 안됨)
    if in_amount <= 0:
        st.error("❌ 금액은 0보다 커야 합니다!")
    else:
        try:
            push_history()  # Undo 가능하게
            
            # 새 거래 생성
            new_row = pd.DataFrame(
                [
                    {
                        "date": in_date,
                        "type": in_type,
                        "category": in_category,
                        "description": str(in_desc),
                        "amount": int(in_amount),
                    }
                ]
            )
            
            # DataFrame에 추가 (최신이 맨 위로)
            st.session_state["df"] = pd.concat([new_row, st.session_state["df"]], ignore_index=True)
            
            # 즉시 CSV에 저장
            save_df(st.session_state["df"])
            
            # 저장 확인
            saved_df = load_df()
            if len(saved_df) > 0:
                st.success(f"✅ 저장 완료! (현재 {len(saved_df)}건)")
                st.session_state["df"] = saved_df  # 저장된 데이터로 세션 업데이트
            else:
                st.error("❌ 저장은 했지만 불러오기에 실패했습니다.")
            
            # 화면 새로고침
            st.rerun()
            
        except Exception as e:
            st.error(f"❌ 저장 중 오류 발생: {e}")
            import traceback
            st.code(traceback.format_exc())


# =============================
# (9) 탭
# =============================
tab_summary, tab_data, tab_chart, tab_budget = st.tabs(["📈 요약 통계", "📄 목록 조회", "📊 차트", "🚨 예산 관제"])


# =============================
# (9-1) F3. 요약 통계 탭
# =============================
with tab_summary:
    st.markdown("## 📊 요약 통계")
    
    # F2. 목록 조회: 거래가 없으면 안내 메시지
    if len(df_f) == 0:
        st.info("📭 등록된 거래가 없습니다. 새 거래를 등록해주세요!")
    else:
        # F3. 요약 통계: calc_summary() 사용
        transactions_list = df_f.to_dict('records')
        
        # 기본 요약
        income, expense, balance = calc_summary(transactions_list)
        
        # 상세 요약
        detailed = calc_detailed_summary(transactions_list)
        
        # st.metric()으로 한눈에 보기
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                label="💰 총 수입",
                value=format_currency(income),
                delta=f"{detailed['income_count']}건"
            )
        
        with col2:
            st.metric(
                label="💸 총 지출",
                value=format_currency(expense),
                delta=f"{detailed['expense_count']}건"
            )
        
        with col3:
            balance_delta = "흑자" if balance >= 0 else "적자"
            st.metric(
                label="💵 현재 잔액",
                value=format_currency(balance),
                delta=balance_delta,
                delta_color="normal" if balance >= 0 else "inverse"
            )
        
        # 추가 통계
        st.markdown("---")
        st.markdown("### 📌 상세 통계")
        
        col4, col5 = st.columns(2)
        with col4:
            if detailed['income_count'] > 0:
                st.write(f"**평균 수입:** {format_currency(detailed['avg_income'])}")
            else:
                st.write("**평균 수입:** -")
        
        with col5:
            if detailed['expense_count'] > 0:
                st.write(f"**평균 지출:** {format_currency(detailed['avg_expense'])}")
            else:
                st.write("**평균 지출:** -")
        
        # 기간 정보
        st.markdown(f"**조회 기간:** {start_date} ~ {end_date}")
        
        if keyword.strip():
            st.markdown(f"**검색어:** '{keyword.strip()}'")


# =============================
# (9-2) F2. 데이터 탭 (목록 조회)
# =============================
with tab_data:
    st.markdown("## 📌 거래 목록 조회")

    b1, b2, b3, b4 = st.columns(4)

    with b1:
        if st.button("🧯 실행 취소(Undo)"):
            pop_history()
            st.rerun()

    with b2:
        if st.button("↩️ 마지막 1건 삭제"):
            if len(st.session_state["df"]) > 0:
                push_history()
                st.session_state["df"] = st.session_state["df"].iloc[1:].reset_index(drop=True)
                save_df(st.session_state["df"])
                st.warning("마지막 1건 삭제 완료")
                st.rerun()

    # F2. 목록 조회: 데이터가 없으면 안내 메시지
    if len(df_view) == 0:
        st.info("📭 등록된 거래가 없습니다.")
    else:
        df_edit = df_view.copy()
        df_edit.insert(0, "삭제", False)

        edited = st.data_editor(
            df_edit,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
        )

        with b3:
            if st.button("🗑️ 체크된 항목 선택 삭제"):
                checked = edited[edited["삭제"] == True]  # noqa: E712
                if len(checked) == 0:
                    st.info("체크된 항목이 없습니다.")
                else:
                    push_history()
                    del_numbers = checked["번호"].tolist()

                    df_now = st.session_state["df"].copy()
                    df_now["번호"] = range(len(df_now))
                    df_now = df_now[~df_now["번호"].isin(del_numbers)].drop(columns=["번호"]).reset_index(drop=True)

                    st.session_state["df"] = df_now
                    save_df(st.session_state["df"])
                    st.success(f"{len(del_numbers)}건 삭제 완료")
                    st.rerun()

        with b4:
            if st.button("💾 수정사항 저장(편집 저장)"):
                push_history()

                df_now = st.session_state["df"].copy()
                df_now["번호"] = range(len(df_now))

                edited2 = edited.copy()
                if "삭제" in edited2.columns:
                    edited2 = edited2.drop(columns=["삭제"])

                edited2 = edited2.rename(
                    columns={
                        "날짜": "date",
                        "구분": "type",
                        "카테고리": "category",
                        "내용": "description",
                        "금액": "amount",
                    }
                )

                for _, row in edited2.iterrows():
                    n = int(row["번호"])
                    mask = df_now["번호"] == n
                    if mask.any():
                        df_now.loc[mask, "date"] = row["date"]
                        df_now.loc[mask, "type"] = str(row["type"])
                        df_now.loc[mask, "category"] = str(row["category"])
                        df_now.loc[mask, "description"] = str(row["description"])
                        df_now.loc[mask, "amount"] = int(pd.to_numeric(row["amount"], errors="coerce") or 0)

                df_now = df_now.drop(columns=["번호"]).reset_index(drop=True)
                st.session_state["df"] = df_now
                save_df(st.session_state["df"])
                st.success("편집 저장 완료")
                st.rerun()

        # D2. 검색어 통계
        if keyword.strip():
            df_kw = df_f.copy()
            df_kw = df_kw[df_kw["type"] == "지출"].copy()

            cnt = int(len(df_kw))
            total = int(df_kw["amount"].sum()) if cnt > 0 else 0

            st.markdown(f'🧾 **검색어 "{keyword.strip()}" 포함 지출: {cnt}건 / {format_currency(total)}**')


# =============================
# (9-3) F5. 차트 탭 (카테고리 통계)
# =============================
with tab_chart:
    st.markdown("## 📊 카테고리별 지출 통계")

    # type == "지출"만 대상
    df_exp = df_f[df_f["type"] == "지출"].copy()

    if len(df_exp) == 0:
        st.info("📭 표시할 지출 데이터가 없습니다.")
    else:
        # F5. 카테고리별 지출 합계
        transactions_list = df_exp.to_dict('records')
        category_totals = calc_category_expense(transactions_list)
        
        # DataFrame으로 변환
        cat_sum = pd.DataFrame(
            list(category_totals.items()),
            columns=["category", "amount"]
        ).sort_values("amount", ascending=False)

        # 그래프 시각화
        color_seq = ["#9B7BFF", "#6FA8FF", "#58D6C9", "#FFC857", "#FF6B9E", "#B7B7C9"]

        fig = px.bar(
            cat_sum,
            x="category",
            y="amount",
            color="category",
            color_discrete_sequence=color_seq,
            text="amount",
        )

        fig.update_layout(
            template="plotly_dark",
            title={"text": "카테고리별 지출 통계", "x": 0.5, "font": {"size": 22, "color": "#EDEDF4"}},
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )
        fig.update_xaxes(
            title={"text": "카테고리", "font": {"color": "#EDEDF4", "size": 16}},
            tickfont={"color": "#EDEDF4", "size": 14},
        )
        fig.update_yaxes(
            title={"text": "금액(원)", "font": {"color": "#EDEDF4", "size": 16}},
            tickfont={"color": "#EDEDF4", "size": 14},
            tickformat=",d",
        )
        fig.update_traces(
            texttemplate="%{text:,}",
            textposition="outside",
        )

        st.plotly_chart(fig, use_container_width=True)

        # 인사이트
        total_exp = int(cat_sum["amount"].sum())
        if total_exp > 0:
            top_cat = cat_sum.iloc[0]["category"]
            top_amt = int(cat_sum.iloc[0]["amount"])
            top_pct = int(round((top_amt / total_exp) * 100))

            st.markdown("### 🧠 인사이트")
            st.markdown(f"**이번 기간 지출 TOP: {top_cat} ({top_pct}%)**")
            st.markdown(f"- {top_cat}에 총 {format_currency(top_amt)} 지출")
            st.markdown(f"- 전체 지출의 {top_pct}%를 차지합니다")


# =============================
# (9-4) D4. 예산 관제 탭 (지출 한도 알림)
# =============================
with tab_budget:
    st.markdown("## 🚨 예산 관리 (지출 한도 알림)")

    now = pd.Timestamp.today()
    month_start = now.replace(day=1).date()
    month_end = (now + pd.offsets.MonthEnd(0)).date()
    st.markdown(f"이번 달 기준: **{month_start} ~ {month_end}**")

    st.markdown("### 📌 카테고리별 예산 설정(원)")

    budgets = st.session_state["budgets"]
    budget_keys = ["전체", "식비", "교통", "통신", "생활", "기타"]

    cols = st.columns(len(budget_keys))
    for i, k in enumerate(budget_keys):
        with cols[i]:
            budgets[k] = st.number_input(k, min_value=0, step=10000, value=int(budgets.get(k, 0)), key=f"budget_{k}")

    if st.button("💾 예산 저장"):
        st.session_state["budgets"] = budgets
        save_budgets(budgets)
        st.success("예산 저장 완료")

    st.markdown("---")
    st.markdown("### ✅ 이번 달 전체 관제")

    # 이번 달 지출 계산
    df_month = st.session_state["df"].copy()
    df_month = df_month.dropna(subset=["date"])
    df_month = df_month[(df_month["date"] >= month_start) & (df_month["date"] <= month_end)]
    df_month_exp = df_month[df_month["type"] == "지출"].copy()

    total_spent = int(df_month_exp["amount"].sum())
    total_budget = int(budgets.get("전체", 0))

    # D4. 예산 관리: calc_budget_status 사용
    ratio, status, message = calc_budget_status(total_spent, total_budget)
    
    st.progress(min(1.0, ratio))
    st.markdown(f"**총 지출: {format_currency(total_spent)} / 총 예산: {format_currency(total_budget)}**")

    # D4. 지출 한도 알림
    if status == "초과":
        st.error(message)
    elif status == "경고":
        st.warning(message)  # 80% 이상 경고
    elif status == "정상":
        st.success(message)
    else:
        st.info(message)

    st.markdown("---")
    st.markdown("### 📊 카테고리별 관제")

    for k in ["식비", "교통", "통신", "생활", "기타"]:
        cat_spent = int(df_month_exp[df_month_exp["category"] == k]["amount"].sum())
        cat_budget = int(budgets.get(k, 0))

        st.markdown(f"**{k} | 지출 {format_currency(cat_spent)} / 예산 {format_currency(cat_budget)}**")

        # D4. 지출 한도 알림 (카테고리별)
        cat_ratio, cat_status, cat_message = calc_budget_status(cat_spent, cat_budget)
        
        st.progress(min(1.0, cat_ratio))

        if cat_status == "초과":
            st.error(f"🚨 {k} 예산 초과!")
        elif cat_status == "경고":
            st.warning(f"⚠️ {k} {cat_message}")  # 80% 경고
        elif cat_status == "정상":
            st.success(f"✅ {k} 정상")
        else:
            st.info(f"{k} {cat_message}")


# =============================
# 하단 정보
# =============================
st.markdown("---")
st.markdown(
    """
<div style="text-align:center; opacity:0.6; font-size:14px;">
✅ <strong>회고 1조 </strong>
</div>
""",
    unsafe_allow_html=True,
)
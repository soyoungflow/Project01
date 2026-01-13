# app.py  # Streamlit UI 담당 (입력/필터/표/차트/예산 관제)  # ← "UI는 여기서만", 로직은 최대한 단순하게

import os  # 파일 경로 만들 때 사용
import json  # 예산(설정값) 저장/로드용
from copy import deepcopy  # Undo(실행 취소)에서 안전하게 복사할 때 사용

import pandas as pd  # 표/필터/그룹 집계용
import streamlit as st  # Streamlit UI 프레임워크
import plotly.express as px  # 차트(Plotly)

# =============================
# (0) 기본 설정
# =============================
st.set_page_config(page_title="나만의 미니 가계부", layout="wide")  # 화면 넓게 쓰기

DATA_DIR = "data"  # 데이터 폴더
os.makedirs(DATA_DIR, exist_ok=True)  # 없으면 폴더 생성

DATA_PATH = os.path.join(DATA_DIR, "ledger.csv")  # 거래 내역 CSV 경로
BUDGET_PATH = os.path.join(DATA_DIR, "budgets.json")  # 예산 저장 JSON 경로


# =============================
# (1) 공통 유틸 함수들
# =============================
def _ensure_ledger_file_exists() -> None:
    """CSV가 없으면 빈 CSV를 만들어서 앱이 항상 정상 실행되게 한다."""
    if not os.path.exists(DATA_PATH):
        df0 = pd.DataFrame(columns=["date", "type", "category", "desc", "amount"])
        df0.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")


def load_df() -> pd.DataFrame:
    """
    CSV에서 거래 데이터를 읽어온다.
    - '내용(텍스트)'이 재실행 때 사라지는 문제는 대부분 인코딩/NaN 처리에서 터짐.
    - 그래서 utf-8-sig로 읽고, desc는 무조건 문자열로 고정한다.
    """
    _ensure_ledger_file_exists()

    try:
        df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    except UnicodeDecodeError:
        # 혹시 팀원이 다른 인코딩으로 저장했을 때를 대비한 안전장치
        df = pd.read_csv(DATA_PATH, encoding="utf-8")

    # 컬럼이 없거나 이름이 달라졌을 때도 앱이 죽지 않게 보정
    for col in ["date", "type", "category", "desc", "amount"]:
        if col not in df.columns:
            df[col] = None

    # 타입 정리 (중요: desc는 문자열 고정)
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.date
    df["type"] = df["type"].astype(str).fillna("")
    df["category"] = df["category"].astype(str).fillna("")
    df["desc"] = df["desc"].astype(str).fillna("")  # ← "내용" 사라짐 방지 핵심
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0).astype(int)

    # 보기 좋게 정렬 (날짜 최신순, 같은 날짜는 최근 입력이 아래로 가도 상관없음)
    df = df.sort_values(["date"], ascending=[False]).reset_index(drop=True)
    return df


def save_df(df: pd.DataFrame) -> None:
    """
    CSV로 저장한다.
    - utf-8-sig로 저장해서 한글/내용(텍스트) 깨짐이나 공백화 이슈를 최대한 차단한다.
    """
    out = df.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.date
    out["type"] = out["type"].astype(str).fillna("")
    out["category"] = out["category"].astype(str).fillna("")
    out["desc"] = out["desc"].astype(str).fillna("")  # ← 저장 시에도 문자열 고정
    out["amount"] = pd.to_numeric(out["amount"], errors="coerce").fillna(0).astype(int)

    out.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")


def load_budgets() -> dict:
    """예산 설정을 JSON에서 읽어온다. 파일이 없으면 기본값을 만든다."""
    if not os.path.exists(BUDGET_PATH):
        return {"전체": 0, "식비": 0, "교통": 0, "통신": 0, "생활": 0, "기타": 0}

    try:
        with open(BUDGET_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}

    # 키 누락 방지(앱이 죽지 않게)
    base = {"전체": 0, "식비": 0, "교통": 0, "통신": 0, "생활": 0, "기타": 0}
    base.update({k: int(v) if str(v).isdigit() else 0 for k, v in data.items()})
    return base


def save_budgets(budgets: dict) -> None:
    """예산 설정을 JSON으로 저장한다."""
    with open(BUDGET_PATH, "w", encoding="utf-8") as f:
        json.dump(budgets, f, ensure_ascii=False, indent=2)


def push_history():
    """Undo를 위해 현재 df를 히스토리에 저장한다."""
    st.session_state["history"].append(deepcopy(st.session_state["df"]))


def pop_history():
    """Undo 실행: 히스토리에서 되돌린다."""
    if st.session_state["history"]:
        st.session_state["df"] = st.session_state["history"].pop()
        save_df(st.session_state["df"])


def fmt_won(x: int) -> str:
    """원 단위 보기 좋게 찍기"""
    try:
        return f"{int(x):,}원"
    except Exception:
        return "0원"


# =============================
# (2) 세션 초기화 (Streamlit은 재실행이 잦아서 상태를 세션에 넣어야 UI가 안정적임)
# =============================
if "df" not in st.session_state:
    st.session_state["df"] = load_df()  # 앱 시작 시 CSV를 읽어서 메모리에 올린다

if "history" not in st.session_state:
    st.session_state["history"] = []  # Undo 스택

if "budgets" not in st.session_state:
    st.session_state["budgets"] = load_budgets()  # 예산 설정 로드


# =============================
# (3) 다크 테마 + 입력 박스 디자인 통일 CSS
# =============================
st.markdown(
    """
<style>
/* 전체 배경(그라데이션) */
.stApp {
  background: radial-gradient(1200px 700px at 35% 0%, rgba(130, 88, 255, 0.35), rgba(10, 12, 18, 0.98) 60%);
  color: #EDEDF4;
}

/* 제목/텍스트 기본 톤 */
h1, h2, h3, h4, h5, h6, p, div, span, label {
  color: #EDEDF4 !important;
}

/* “보라색 헤더 바(박스)” */
.purple-bar {
  border-radius: 999px;
  padding: 18px 22px;
  background: linear-gradient(90deg, rgba(128, 77, 255, 0.35), rgba(85, 60, 200, 0.18));
  border: 1px solid rgba(160, 120, 255, 0.35);
  box-shadow: 0 8px 24px rgba(0,0,0,0.35);
}

/* 헤더 바 안의 텍스트 */
.purple-bar-title {
  font-size: 36px;
  font-weight: 800;
  letter-spacing: -0.4px;
  display: flex;
  align-items: center;
  gap: 12px;
}

/* 입력 박스 톤(왼쪽 필터/가운데 입력/예산 입력 통일) */
:root {
  --box-bg: rgba(58, 61, 70, 0.78);
  --box-border: rgba(210, 210, 230, 0.18);
  --box-border-strong: rgba(210, 210, 230, 0.26);
  --box-radius: 26px;
}

/* text_input / number_input / date_input 공통 느낌 */
div[data-testid="stTextInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stDateInput"] input {
  background: var(--box-bg) !important;
  border: 1px solid var(--box-border) !important;
  border-radius: var(--box-radius) !important;
  color: #EDEDF4 !important;
  box-shadow: inset 0 0 0 1px rgba(255,255,255,0.03);
}

/* selectbox(구분/카테고리)과 같은 톤으로 통일 */
div[data-baseweb="select"] > div {
  background: var(--box-bg) !important;
  border: 1px solid var(--box-border) !important;
  border-radius: var(--box-radius) !important;
  color: #EDEDF4 !important;
}
div[data-baseweb="select"] span { color: #EDEDF4 !important; }

/* 사이드바도 같은 톤 */
section[data-testid="stSidebar"] {
  background: rgba(10, 12, 18, 0.55) !important;
  border-right: 1px solid rgba(255,255,255,0.06);
}

/* 버튼 */
.stButton > button {
  border-radius: 18px;
  padding: 10px 16px;
  border: 1px solid rgba(160,120,255,0.35);
  background: rgba(128, 77, 255, 0.35);
  color: #EDEDF4;
  font-weight: 700;
}
.stButton > button:hover {
  border: 1px solid rgba(160,120,255,0.55);
  background: rgba(128, 77, 255, 0.45);
}

/* 데이터테이블(에디터) 톤 */
div[data-testid="stDataFrame"] {
  border-radius: 18px;
  overflow: hidden;
  border: 1px solid rgba(255,255,255,0.08);
}
</style>
""",
    unsafe_allow_html=True,
)


# =============================
# (4) 헤더(타이틀)
# =============================
st.markdown(
    """
<div style="display:flex; align-items:flex-start; gap:14px; margin-bottom:8px;">
  <div style="font-size:46px; line-height:1;">🧾</div>
  <div>
    <div style="font-size:44px; font-weight:900; letter-spacing:-0.6px;">나만의 미니 가계부 (지출 관리 서비스)</div>
    <div style="opacity:0.75; margin-top:4px;">입력 → 저장 → 즉시 반영되는 MVP 가계부</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)


# =============================
# (5) 왼쪽 필터(기간/검색어/구분/카테고리)
# =============================
with st.sidebar:
    st.markdown("## 🔎 필터")

    # 기간 선택(시작~끝)
    min_date = pd.to_datetime("2000-01-01").date()
    max_date = pd.to_datetime("2100-12-31").date()

    # 기본값: 오늘 하루
    today = pd.Timestamp.today().date()

    start_date, end_date = st.date_input(
        "기간 선택",
        value=(today, today),
        min_value=min_date,
        max_value=max_date,
        help="이 기간에 해당하는 데이터만 보여줍니다.",
    )
    if isinstance(start_date, (list, tuple)) and len(start_date) == 2:
        # 일부 환경에서 date_input이 튜플이 아닌 리스트로 들어오는 경우 대응
        start_date, end_date = start_date[0], start_date[1]

    keyword = st.text_input("검색어(내용 포함)", value="", placeholder="예) 점심, 지하철 ...")

    type_filter = st.selectbox("구분", ["전체", "지출", "수입"], index=0)

    # 카테고리 목록은 데이터에서 자동 생성(없으면 기본 5개)
    base_categories = ["식비", "교통", "통신", "생활", "기타"]
    data_categories = sorted([c for c in st.session_state["df"]["category"].unique().tolist() if c])
    categories = ["전체"] + sorted(list(set(base_categories + data_categories)))

    category_filter = st.selectbox("카테고리", categories, index=0)


# =============================
# (6) 필터 적용
# =============================
df_all = st.session_state["df"].copy()

# 번호(사용자용 컬럼): 내부 index 대신 사람이 이해하는 “번호”
df_all["번호"] = range(len(df_all))

# 날짜 필터 (date가 비어있으면 제외)
df_f = df_all.dropna(subset=["date"]).copy()
df_f = df_f[(df_f["date"] >= start_date) & (df_f["date"] <= end_date)].copy()

# 구분 필터
if type_filter != "전체":
    df_f = df_f[df_f["type"] == type_filter].copy()

# 카테고리 필터
if category_filter != "전체":
    df_f = df_f[df_f["category"] == category_filter].copy()

# 내용(검색어) 필터
if keyword.strip():
    df_f = df_f[df_f["desc"].astype(str).str.contains(keyword.strip(), na=False)].copy()

# 화면용 컬럼명(KR)
df_view = df_f.rename(
    columns={
        "date": "날짜",
        "type": "구분",
        "category": "카테고리",
        "desc": "내용",
        "amount": "금액",
    }
)[["번호", "날짜", "구분", "카테고리", "내용", "금액"]].copy()


# =============================
# (7) 새 거래 등록(상단 입력 폼)
# =============================
st.markdown(
    """
<div class="purple-bar" style="margin-top:14px; margin-bottom:12px;">
  <div class="purple-bar-title">➕ 새 거래 등록</div>
</div>
""",
    unsafe_allow_html=True,
)

# 입력 폼(여기서 등록 버튼 누르면 df에 추가하고 즉시 저장)
col_a, col_b, col_c = st.columns([1.4, 1.0, 1.0])
with col_a:
    in_date = st.date_input("날짜", value=today)
with col_b:
    in_type = st.selectbox("구분", ["지출", "수입"], index=0)
with col_c:
    in_category = st.selectbox("카테고리", ["식비", "교통", "통신", "생활", "기타"], index=0)

in_desc = st.text_input("내용", value="", placeholder="예) 지하철 / 점심 / 통신요금 ...")
in_amount = st.number_input("금액(원)", min_value=0, step=1000, value=0)

if st.button("등록"):
    push_history()  # ← Undo 가능하게 등록 전에 저장

    new_row = pd.DataFrame(
        [
            {
                "date": in_date,
                "type": in_type,
                "category": in_category,
                "desc": str(in_desc),  # ← 문자열 고정
                "amount": int(in_amount),
            }
        ]
    )
    st.session_state["df"] = pd.concat([new_row, st.session_state["df"]], ignore_index=True)
    save_df(st.session_state["df"])
    st.success("저장 완료! (즉시 반영됨)")
    st.rerun()  # UI 즉시 갱신


# =============================
# (8) 탭(데이터 / 차트 / 관제(예산))
# =============================
tab_data, tab_chart, tab_budget = st.tabs(["📄 데이터", "📊 차트", "🚨 관제(예산)"])


# =============================
# (8-1) 데이터 탭
# =============================
with tab_data:
    st.markdown("## 📌 필터 결과 데이터")

    # 버튼 4개를 한 줄로 (요구사항)
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
            else:
                st.info("삭제할 데이터가 없습니다.")

    # 데이터 에디터용: 삭제 체크 컬럼 추가
    df_edit = df_view.copy()
    df_edit.insert(0, "삭제", False)  # ← 체크박스

    edited = st.data_editor(
        df_edit,
        use_container_width=True,
        hide_index=True,
        num_rows="fixed",
        disabled=[],  # 전체 수정 가능(원하면 특정 컬럼만 막을 수도 있음)
    )

    # 체크된 삭제 버튼
    with b3:
        if st.button("🗑️ 체크된 항목 선택 삭제"):
            checked = edited[edited["삭제"] == True]  # noqa: E712
            if len(checked) == 0:
                st.info("체크된 항목이 없습니다.")
            else:
                push_history()
                del_numbers = checked["번호"].tolist()

                # df_all의 “번호”와 매칭해서 제거
                df_now = st.session_state["df"].copy()
                df_now["번호"] = range(len(df_now))
                df_now = df_now[~df_now["번호"].isin(del_numbers)].drop(columns=["번호"]).reset_index(drop=True)

                st.session_state["df"] = df_now
                save_df(st.session_state["df"])
                st.success(f"{len(del_numbers)}건 삭제 완료")
                st.rerun()

    # 편집 저장 버튼
    with b4:
        if st.button("💾 수정사항 저장(편집 저장)"):
            push_history()

            # 사용자가 수정한 값들을 “번호” 기준으로 원본 df에 반영
            df_now = st.session_state["df"].copy()
            df_now["번호"] = range(len(df_now))

            # 삭제 체크 컬럼 제거 후, 컬럼명 원복
            edited2 = edited.copy()
            if "삭제" in edited2.columns:
                edited2 = edited2.drop(columns=["삭제"])

            edited2 = edited2.rename(
                columns={
                    "날짜": "date",
                    "구분": "type",
                    "카테고리": "category",
                    "내용": "desc",
                    "금액": "amount",
                }
            )

            # 번호 매칭해서 값 업데이트
            for _, row in edited2.iterrows():
                n = int(row["번호"])
                mask = df_now["번호"] == n
                if mask.any():
                    df_now.loc[mask, "date"] = row["date"]
                    df_now.loc[mask, "type"] = str(row["type"])
                    df_now.loc[mask, "category"] = str(row["category"])
                    df_now.loc[mask, "desc"] = str(row["desc"])  # ← 내용은 무조건 문자열
                    df_now.loc[mask, "amount"] = int(pd.to_numeric(row["amount"], errors="coerce") or 0)

            df_now = df_now.drop(columns=["번호"]).reset_index(drop=True)
            st.session_state["df"] = df_now
            save_df(st.session_state["df"])
            st.success("편집 저장 완료")
            st.rerun()

    # 검색어 통계(표 아래)
    if keyword.strip():
        # "현재 필터 결과(df_f)"에서 검색어가 포함된 지출만 따로 통계
        df_kw = df_f.copy()
        df_kw = df_kw[df_kw["type"] == "지출"].copy()
        df_kw = df_kw[df_kw["desc"].astype(str).str.contains(keyword.strip(), na=False)].copy()

        cnt = int(len(df_kw))
        total = int(df_kw["amount"].sum()) if cnt > 0 else 0

        st.markdown(
            f"""
🧾 **검색어 "{keyword.strip()}" 포함 지출: {cnt}건 / {total:,}원**
""".strip()
        )


# =============================
# (8-2) 차트 탭
# =============================
with tab_chart:
    st.markdown("## 📊 카테고리별 지출 통계")

    # 차트는 “지출”만 의미가 있으니 지출만 집계
    df_exp = df_f[df_f["type"] == "지출"].copy()

    if len(df_exp) == 0:
        st.info("표시할 지출 데이터가 없습니다. (필터를 넓히거나 지출을 입력하세요)")
    else:
        cat_sum = (
            df_exp.groupby("category", as_index=False)["amount"]
            .sum()
            .sort_values("amount", ascending=False)
        )

        # 카테고리별 컬러(각각 다르게)
        # - 색이 너무 못생겼던 문제를 줄이려고, 다크테마에서 안정적으로 보이는 세트로 제한
        color_seq = [
            "#9B7BFF",  # 보라
            "#6FA8FF",  # 블루
            "#58D6C9",  # 민트
            "#FFC857",  # 옐로
            "#FF6B9E",  # 핑크
            "#B7B7C9",  # 그레이
        ]

        fig = px.bar(
            cat_sum,
            x="category",
            y="amount",
            color="category",
            color_discrete_sequence=color_seq,
            text="amount",
        )

        # ===== 축 글자 안 나오던 문제 해결 포인트 =====
        # 1) plotly_dark + 글자색을 명시(white)
        # 2) x/y 축 title은 titlefont 같은 잘못된 속성 쓰지 말고 title=dict(font=...)로 써야 함
        fig.update_layout(
            template="plotly_dark",
            title={"text": "카테고리별 지출 통계", "x": 0.5, "font": {"size": 22, "color": "#EDEDF4"}},
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
            margin=dict(l=40, r=20, t=70, b=40),
        )
        fig.update_xaxes(
            title={"text": "카테고리", "font": {"color": "#EDEDF4", "size": 16}},
            tickfont={"color": "#EDEDF4", "size": 14},
            showgrid=False,
        )
        fig.update_yaxes(
            title={"text": "금액(원)", "font": {"color": "#EDEDF4", "size": 16}},
            tickfont={"color": "#EDEDF4", "size": 14},
            tickformat=",d",  # 5k 같은 축약 대신 5000 스타일
            gridcolor="rgba(255,255,255,0.12)",
        )
        fig.update_traces(
            texttemplate="%{text:,}",  # 막대 위 숫자도 1,000 스타일
            textposition="outside",
            cliponaxis=False,
        )

        st.plotly_chart(fig, use_container_width=True)

        # 인사이트(그래프 아래): TOP1 카테고리와 비율
        total_exp = int(cat_sum["amount"].sum())
        top_cat = cat_sum.iloc[0]["category"]
        top_amt = int(cat_sum.iloc[0]["amount"])
        top_pct = int(round((top_amt / total_exp) * 100)) if total_exp > 0 else 0

        st.markdown("### 🧠 인사이트(간단)")
        st.markdown(f"**이번 달 지출 TOP: {top_cat}({top_pct}%)**")


# =============================
# (8-3) 관제(예산) 탭
# =============================
with tab_budget:
    st.markdown("## 🚨 관제(예산)")

    # “이번 달 기준” 표기용 기간(현재 달)
    now = pd.Timestamp.today()
    month_start = now.replace(day=1).date()
    month_end = (now + pd.offsets.MonthEnd(0)).date()
    st.markdown(f"이번 달 기준: **{month_start} ~ {month_end}**")

    st.markdown("### 📌 카테고리별 예산 설정(원)")

    # 예산 입력도 “구분/카테고리” 셀렉트박스와 같은 톤으로 보이게 CSS 이미 통일됨.
    budgets = st.session_state["budgets"]

    # 순서 고정: 전체가 맨 앞
    budget_keys = ["전체", "식비", "교통", "통신", "생활", "기타"]

    # 한 줄로 쭉 배치
    cols = st.columns(len(budget_keys))
    for i, k in enumerate(budget_keys):
        with cols[i]:
            budgets[k] = st.number_input(k, min_value=0, step=10000, value=int(budgets.get(k, 0)))

    # 저장 버튼
    if st.button("💾 예산 저장"):
        st.session_state["budgets"] = budgets
        save_budgets(budgets)
        st.success("예산 저장 완료")

    st.markdown("---")
    st.markdown("### ✅ 이번 달 전체 관제")

    # 이번 달 지출 합계
    df_month = st.session_state["df"].copy()
    df_month = df_month.dropna(subset=["date"])
    df_month = df_month[(df_month["date"] >= month_start) & (df_month["date"] <= month_end)]
    df_month_exp = df_month[df_month["type"] == "지출"].copy()

    total_spent = int(df_month_exp["amount"].sum())
    total_budget = int(budgets.get("전체", 0))

    # 진행률(예산이 0이면 0으로 처리)
    ratio = (total_spent / total_budget) if total_budget > 0 else 0.0
    ratio = max(0.0, min(1.0, ratio))  # 0~1로 고정

    st.progress(ratio)
    st.markdown(f"**총 지출: {total_spent:,}원 / 총 예산: {total_budget:,}원**")

    # 상태 메시지 + (요구사항) 80% 경고 메시지
    if total_budget > 0:
        if total_spent >= total_budget:
            st.error("🚨 예산을 초과했습니다! 지금부터는 지출을 강하게 줄여야 합니다.")
        elif total_spent >= int(total_budget * 0.8):
            # ✅ 요구사항: 이 경고가 다시 뜨게
            st.warning("⚠️ 예산의 80%를 사용했습니다!")
        else:
            st.success("👍 예산 범위 내에서 관리 중입니다.")
    else:
        st.info("전체 예산(전체)을 설정하면 관제 경고/진행률이 정확해집니다.")

    st.markdown("---")
    st.markdown("### 📊 카테고리별 관제")

    # 카테고리별: (지출/예산) 진행률 표시
    for k in ["식비", "교통", "통신", "생활", "기타"]:
        cat_spent = int(df_month_exp[df_month_exp["category"] == k]["amount"].sum())
        cat_budget = int(budgets.get(k, 0))

        st.markdown(f"**{k} | 지출 {cat_spent:,}원 / 예산 {cat_budget:,}원**")

        if cat_budget > 0:
            cat_ratio = max(0.0, min(1.0, cat_spent / cat_budget))
        else:
            cat_ratio = 0.0

        st.progress(cat_ratio)

        if cat_budget > 0:
            if cat_spent >= cat_budget:
                st.error(f"🚨 {k} 예산 초과")
            elif cat_spent >= int(cat_budget * 0.8):
                st.warning(f"⚠️ {k} 예산의 80%를 사용했습니다!")
            else:
                st.success(f"✅ {k} 정상")
        else:
            st.info(f"{k} 예산을 설정하면 카테고리 관제가 더 정확해집니다.")

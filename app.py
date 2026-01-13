# app.py
# Streamlit UI 담당 파일 (입력/필터/표/차트/예산/Undo/삭제/편집저장)
# ✅ 팀 공통 규칙: "UI는 app.py, 로직은 ledger/* 모듈"을 지키기 위해
#    app.py는 '불러오기/보여주기/버튼 처리'만 하고, 저장/통계 계산은 모듈 함수 호출로 처리한다.

import os
import copy
import pandas as pd
import streamlit as st

import plotly.express as px  # ✅ Plotly로 차트(다크테마 + 축 글자 안정적으로 표시)

# 팀원이 만든 로직 모듈 import (이 이름이 다르면 ImportError 터짐)
from ledger.repository import load_transactions, save_transactions
from ledger.services import calc_summary, calc_category_expense


# =============================
# 0) 기본 설정 (앱 전체)
# =============================
st.set_page_config(page_title="나만의 미니 가계부", layout="wide")

DATA_PATH = os.path.join("data", "ledger.csv")

# ✅ 카테고리 고정 리스트 (필터/입력폼/차트/예산 모두 동일하게 사용)
#    "한 군데만 수정하면 전체가 같이 바뀌게" → 유지보수 쉬워짐
CATEGORIES = ["식비", "교통", "통신", "생활", "기타"]
TYPES = ["수입", "지출"]

# ✅ 카테고리별 색상(Plotly용)
#    색은 취향이지만 "카테고리→색" 매핑을 고정하면 사용자가 한눈에 이해함
CATEGORY_COLORS = {
    "식비": "#A78BFA",   # 보라
    "교통": "#60A5FA",   # 파랑
    "통신": "#34D399",   # 초록
    "생활": "#FBBF24",   # 노랑
    "기타": "#F87171",   # 빨강
}

# =============================
# 1) CSS (보라 테마)
# =============================
# ✅ UI가 예쁘게 보이도록 카드/버튼/탭 컬러를 보라 기반으로 통일
PURPLE_CSS = """
<style>
/* 전체 배경 */
.stApp {
  background: radial-gradient(1200px 600px at 30% 0%, rgba(124, 58, 237, 0.18), rgba(0,0,0,0) 60%),
              radial-gradient(1200px 600px at 80% 30%, rgba(124, 58, 237, 0.10), rgba(0,0,0,0) 65%),
              #0b0f17;
}

/* 사이드바 */
section[data-testid="stSidebar"] {
  background: #0b0f17;
  border-right: 1px solid rgba(255,255,255,0.06);
}

/* 타이틀 느낌 */
h1, h2, h3, h4 {
  letter-spacing: -0.02em;
}

/* 보라 헤더 박스 (새 거래 등록 제목줄) */
.purple-banner {
  padding: 16px 18px;
  border-radius: 18px;
  background: linear-gradient(90deg, rgba(124,58,237,0.35), rgba(124,58,237,0.08));
  border: 1px solid rgba(167,139,250,0.35);
  box-shadow: 0 0 22px rgba(124,58,237,0.16);
  margin: 10px 0 12px 0;
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 800;
  font-size: 20px;
}

/* 버튼 색감 보라 */
.stButton > button {
  border-radius: 16px !important;
  border: 1px solid rgba(167,139,250,0.35) !important;
  background: linear-gradient(180deg, rgba(124,58,237,0.95), rgba(124,58,237,0.65)) !important;
  color: white !important;
  padding: 10px 16px !important;
  font-weight: 800 !important;
  box-shadow: 0 8px 22px rgba(124,58,237,0.16) !important;
}

/* 데이터프레임 둥글게 */
[data-testid="stDataFrame"] {
  border-radius: 16px;
  overflow: hidden;
}

/* 탭 밑줄 강조 */
.stTabs [data-baseweb="tab"] {
  font-weight: 800;
}
</style>
"""
st.markdown(PURPLE_CSS, unsafe_allow_html=True)


# =============================
# 2) 유틸 함수 (app.py 내부 "UI 보조용"만 둠)
# =============================
def ensure_dataframe(transactions: list[dict]) -> pd.DataFrame:
    """
    ✅ transactions(list[dict]) → DataFrame 변환 + 컬럼 정리 + date를 datetime으로 강제
    - 우리가 겪었던 .dt 에러를 '여기서 원천 차단'한다.
    """
    if not transactions:
        # 데이터가 아예 없을 때도 안정적으로 돌아가게 "빈 DF"를 표준 컬럼으로 만들어 둔다.
        df = pd.DataFrame(columns=["date", "type", "category", "content", "amount"])
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        return df

    df = pd.DataFrame(transactions)

    # 혹시 컬럼명이 살짝 달라져도(팀원이 실수해도) 최소한 앱이 터지지 않게 안전장치
    for col in ["date", "type", "category", "content", "amount"]:
        if col not in df.columns:
            df[col] = None

    # ✅ 핵심: date를 무조건 datetime으로 바꿔야 df["date"].dt 가 안전함
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # amount는 숫자로
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0).astype(int)

    # 보기 좋게 정렬(최신 날짜 위)
    df = df.sort_values(by=["date"], ascending=False).reset_index(drop=True)
    return df


def within_date_range(df: pd.DataFrame, start_date, end_date) -> pd.DataFrame:
    """
    ✅ 기간 필터 (선택 기간 데이터만 표시)
    - df["date"]가 datetime이 아닐 때 .dt 쓰면 바로 에러 → ensure_dataframe에서 해결됨
    """
    if df.empty:
        return df

    # 날짜가 NaT(비정상)인 행은 필터 전에 제거(안그러면 비교연산이 꼬일 수 있음)
    df2 = df.dropna(subset=["date"]).copy()
    if df2.empty:
        return df2

    mask = (df2["date"].dt.date >= start_date) & (df2["date"].dt.date <= end_date)
    return df2.loc[mask].copy()


def apply_filters(df: pd.DataFrame, start_date, end_date, keyword: str, type_filter: str, category_filter: str) -> pd.DataFrame:
    """
    ✅ 사이드바 필터 전체 적용
    """
    df2 = within_date_range(df, start_date, end_date)

    if df2.empty:
        return df2

    # 구분 필터
    if type_filter != "전체":
        df2 = df2[df2["type"] == type_filter]

    # 카테고리 필터
    if category_filter != "전체":
        df2 = df2[df2["category"] == category_filter]

    # 검색어(내용 포함)
    kw = (keyword or "").strip()
    if kw:
        df2 = df2[df2["content"].fillna("").str.contains(kw, case=False, na=False)]

    return df2.copy()


def month_window_from_end(end_date):
    """
    ✅ '이번 달' 판단 기준을 통일:
    - 사용자가 고른 기간의 '끝 날짜(end_date)'가 속한 달을 "이번 달"로 본다.
    """
    end = pd.to_datetime(end_date)
    month_start = end.replace(day=1).date()
    month_end = (end + pd.offsets.MonthEnd(0)).date()
    return month_start, month_end


def format_won(x: int) -> str:
    """원 단위 포맷(쉼표)"""
    try:
        return f"{int(x):,}"
    except Exception:
        return "0"


# =============================
# 3) 데이터 로드 + 세션 상태(Undo 등)
# =============================
# ✅ 최초 1회만 로드: 새로고침/버튼 눌러도 불필요한 재로드를 줄인다.
if "transactions" not in st.session_state:
    st.session_state.transactions = load_transactions(DATA_PATH)

# ✅ Undo를 위해 "이전 스냅샷"을 저장할 공간
if "undo_stack" not in st.session_state:
    st.session_state.undo_stack = []  # 스냅샷을 여러 번 쌓아두면 여러 단계 Undo 가능

# ✅ 마지막 저장 시점 (편집 저장 버튼용)
if "last_saved_snapshot" not in st.session_state:
    st.session_state.last_saved_snapshot = copy.deepcopy(st.session_state.transactions)

# 현재 데이터 → DataFrame
df_all = ensure_dataframe(st.session_state.transactions)

# =============================
# 4) 제목/설명 + 새 거래 등록(메인, 탭 위)
# =============================
st.title("🧾 나만의 미니 가계부 (지출 관리 서비스)")
st.caption("입력 → 저장 → 즉시 반영되는 MVP 가계부")

# ✅ 보라 박스에 글자 넣기(비어 보이면 UX 망가짐)
st.markdown(
    '<div class="purple-banner">➕ 새 거래 등록 <span style="font-size:13px; font-weight:700; opacity:0.85; '
    'background:rgba(34,197,94,0.15); border:1px solid rgba(34,197,94,0.35); padding:4px 10px; border-radius:999px;">즉시 저장</span></div>',
    unsafe_allow_html=True
)

# ✅ 입력 폼(메인)
# - 구분/카테고리는 드롭다운(선택 실수 방지)
# - 내용/검색어는 타이핑(사용자 편의)
with st.form("add_tx_form", clear_on_submit=True):
    c1, c2, c3 = st.columns([2, 2, 2])

    with c1:
        tx_date = st.date_input("날짜", value=pd.Timestamp.today().date())
    with c2:
        tx_type = st.selectbox("구분", TYPES, index=1)
    with c3:
        tx_category = st.selectbox("카테고리", CATEGORIES, index=0)

    c4, c5 = st.columns([4, 2])
    with c4:
        tx_content = st.text_input("내용", placeholder="예) 지하철 / 점심 / 통신요금 ...")  # ✅ 바로 타이핑
    with c5:
        tx_amount = st.number_input("금액(원)", min_value=0, step=1000, value=0)

    submitted = st.form_submit_button("등록")

# ✅ 등록 버튼 처리 (제일 중요: 저장 로직은 모듈 함수 호출로 처리)
if submitted:
    new_tx = {
        "date": str(tx_date),
        "type": tx_type,
        "category": tx_category,
        "content": tx_content.strip(),
        "amount": int(tx_amount),
    }

    # Undo를 위해 저장 전 스냅샷 push
    st.session_state.undo_stack.append(copy.deepcopy(st.session_state.transactions))

    st.session_state.transactions.append(new_tx)
    save_transactions(DATA_PATH, st.session_state.transactions)
    st.session_state.last_saved_snapshot = copy.deepcopy(st.session_state.transactions)

    st.success("✅ 저장 완료! (즉시 반영)")
    st.rerun()


# =============================
# 5) 사이드바: 필터만 남김
# =============================
st.sidebar.header("🔎 필터")

# 기간 선택
# ✅ df가 비어도 date_input은 기본값이 필요하므로 "오늘~오늘"로 둔다.
default_start = pd.Timestamp.today().date()
default_end = pd.Timestamp.today().date()

if not df_all.empty and df_all["date"].notna().any():
    min_date = df_all["date"].min().date()
    max_date = df_all["date"].max().date()
    default_start, default_end = min_date, max_date

date_range = st.sidebar.date_input("기간 선택", value=(default_start, default_end))
if isinstance(date_range, tuple) and len(date_range) == 2:
    start_date, end_date = date_range
else:
    start_date, end_date = default_start, default_end

# 검색어(내용 포함) - ✅ 타이핑 입력
keyword = st.sidebar.text_input("검색어(내용 포함)", value="")

# 구분
type_filter = st.sidebar.selectbox("구분", ["전체"] + TYPES, index=0)

# 카테고리
category_filter = st.sidebar.selectbox("카테고리", ["전체"] + CATEGORIES, index=0)

# 필터 적용된 DF
df = apply_filters(df_all, start_date, end_date, keyword, type_filter, category_filter)


# =============================
# 6) 탭 (데이터 / 차트 / 관제(예산))
# =============================
tab_data, tab_chart, tab_budget = st.tabs(["📄 데이터", "📊 차트", "🚨 관제(예산)"])


# ---------------------------------
# (A) 데이터 탭
# ---------------------------------
with tab_data:
    st.subheader("📌 필터 결과 데이터")

    # ✅ 버튼 4개는 한 줄(가로 1열)로 쭉
    b1, b2, b3, b4 = st.columns([1, 1, 1.4, 1.4])

    # 1) Undo
    with b1:
        if st.button("🧯 실행 취소(Undo)"):
            if st.session_state.undo_stack:
                st.session_state.transactions = st.session_state.undo_stack.pop()
                save_transactions(DATA_PATH, st.session_state.transactions)
                st.session_state.last_saved_snapshot = copy.deepcopy(st.session_state.transactions)
                st.success("✅ Undo 완료")
                st.rerun()
            else:
                st.info("되돌릴 기록이 없어요.")

    # 2) 마지막 1건 삭제
    with b2:
        if st.button("↩️ 마지막 1건 삭제"):
            if st.session_state.transactions:
                st.session_state.undo_stack.append(copy.deepcopy(st.session_state.transactions))
                st.session_state.transactions.pop()
                save_transactions(DATA_PATH, st.session_state.transactions)
                st.session_state.last_saved_snapshot = copy.deepcopy(st.session_state.transactions)
                st.success("✅ 마지막 1건 삭제 완료")
                st.rerun()
            else:
                st.info("삭제할 데이터가 없어요.")

    # 3) 체크된 항목 선택 삭제 (체크박스는 아래 편집표에서 처리)
    with b3:
        delete_checked_clicked = st.button("🗑️ 체크된 항목 선택 삭제")

    # 4) 수정사항 저장(편집 저장)
    with b4:
        save_edited_clicked = st.button("💾 수정사항 저장(편집 저장)")

    # ✅ 데이터가 없으면 '표 자체'를 편집 모드로 띄울 필요가 없음 (여기서 방어하면 에러가 싹 사라짐)
    if df.empty:
        st.info("표시할 데이터가 없습니다. (필터 조건을 바꾸거나 새 거래를 등록해보세요.)")
        # 검색어 인사이트도 의미 없으니 여기서 종료
        st.stop()

    # 표에 보여줄 DF 만들기
    # ✅ 사용자 눈에는 _idx 같은 개발자용 컬럼이 거슬림 → "번호"로 바꿔서 보여줌
    df_view = df.copy()
    df_view = df_view.reset_index(drop=True)
    df_view.insert(0, "번호", range(len(df_view)))  # 화면에서만 쓰는 번호
    df_view["날짜"] = df_view["date"].dt.date
    df_view["구분"] = df_view["type"]
    df_view["카테고리"] = df_view["category"]
    df_view["내용"] = df_view["content"].fillna("")
    df_view["금액"] = df_view["amount"].astype(int)

    # 체크박스 삭제용 컬럼
    df_view.insert(0, "삭제", False)

    # ✅ 화면에 보여줄 컬럼만 남김
    show_cols = ["삭제", "번호", "날짜", "구분", "카테고리", "내용", "금액"]
    df_edit_base = df_view[show_cols].copy()

    # ✅ Streamlit 데이터 편집 표 (사용자가 표에서 바로 내용/금액 수정 가능)
    edited = st.data_editor(
        df_edit_base,
        use_container_width=True,
        hide_index=True,
        key="data_editor",
        column_config={
            "삭제": st.column_config.CheckboxColumn("삭제", help="체크 후 '체크된 항목 선택 삭제' 클릭"),
            "번호": st.column_config.NumberColumn("번호", disabled=True),
            "금액": st.column_config.NumberColumn("금액", min_value=0, step=1000),
        },
    )

    # --- (1) 체크된 항목 삭제 처리 ---
    if delete_checked_clicked:
        # 체크된 번호 목록
        checked_rows = edited[edited["삭제"] == True]
        if checked_rows.empty:
            st.info("체크된 항목이 없습니다.")
        else:
            # Undo 스택에 저장
            st.session_state.undo_stack.append(copy.deepcopy(st.session_state.transactions))

            # 실제 transactions에서 해당 레코드 삭제:
            # df는 필터된 데이터라 원본 인덱스와 다를 수 있음 → 안전하게 "날짜/구분/카테고리/내용/금액" 매칭 삭제
            to_delete = []
            for _, r in checked_rows.iterrows():
                to_delete.append({
                    "date": str(r["날짜"]),
                    "type": r["구분"],
                    "category": r["카테고리"],
                    "content": str(r["내용"]),
                    "amount": int(r["금액"]),
                })

            new_list = []
            for tx in st.session_state.transactions:
                # 하나씩 비교해서 "삭제 대상"이면 스킵
                matched = False
                for dtx in to_delete:
                    if (
                        str(tx.get("date"))[:10] == dtx["date"][:10]
                        and tx.get("type") == dtx["type"]
                        and tx.get("category") == dtx["category"]
                        and str(tx.get("content", "")) == dtx["content"]
                        and int(tx.get("amount", 0)) == dtx["amount"]
                    ):
                        matched = True
                        break
                if not matched:
                    new_list.append(tx)

            st.session_state.transactions = new_list
            save_transactions(DATA_PATH, st.session_state.transactions)
            st.session_state.last_saved_snapshot = copy.deepcopy(st.session_state.transactions)
            st.success("✅ 체크된 항목 삭제 완료")
            st.rerun()

    # --- (2) 편집 저장 처리 ---
    if save_edited_clicked:
        # Undo 스택에 저장
        st.session_state.undo_stack.append(copy.deepcopy(st.session_state.transactions))

        # edited 표를 기준으로 "필터 결과"에 있는 행들은 수정 반영
        # 실제 transactions 전체를 직접 재구성하기는 복잡하니,
        # 여기서는 '필터로 보이는 행들'만 매칭해서 업데이트한다.
        updated_list = copy.deepcopy(st.session_state.transactions)

        for _, r in edited.iterrows():
            # 삭제 체크는 여기서 반영하지 않음(삭제는 버튼으로만)
            new_date = str(r["날짜"])
            new_type = r["구분"]
            new_cat = r["카테고리"]
            new_content = str(r["내용"])
            new_amount = int(r["금액"])

            # 원본에서 동일 행 찾아 업데이트(첫 매칭만)
            for tx in updated_list:
                if (
                    str(tx.get("date"))[:10] == new_date[:10]
                    and tx.get("type") == new_type
                    and tx.get("category") == new_cat
                    and str(tx.get("content", "")) == new_content
                ):
                    # 이 경우는 "내용까지 같은 행"이라 업데이트 효과가 없음 → 아래에서 더 넓게 매칭
                    pass

        # 더 현실적인 업데이트: "번호"는 화면용이라서 원본 인덱스와 다를 수 있음.
        # 그래서 안전하게: 필터된 df의 각 row(기존값) ↔ edited row(새값)을 같은 순서로 대응시켜 반영
        df_filtered_original = df.copy().reset_index(drop=True)
        edited_only = edited.reset_index(drop=True)

        # 필터된 행 수가 같을 때만 순서 업데이트
        if len(df_filtered_original) == len(edited_only):
            for i in range(len(edited_only)):
                old = df_filtered_original.loc[i]
                new = edited_only.loc[i]

                old_key = (
                    str(old["date"])[:10],
                    old["type"],
                    old["category"],
                    str(old["content"] or ""),
                    int(old["amount"] or 0),
                )

                # 원본 리스트에서 old_key 찾고 new 값으로 바꿈
                for tx in updated_list:
                    tx_key = (
                        str(tx.get("date"))[:10],
                        tx.get("type"),
                        tx.get("category"),
                        str(tx.get("content") or ""),
                        int(tx.get("amount") or 0),
                    )
                    if tx_key == old_key:
                        tx["date"] = str(new["날짜"])
                        tx["type"] = new["구분"]
                        tx["category"] = new["카테고리"]
                        tx["content"] = str(new["내용"])
                        tx["amount"] = int(new["금액"])
                        break

        st.session_state.transactions = updated_list
        save_transactions(DATA_PATH, st.session_state.transactions)
        st.session_state.last_saved_snapshot = copy.deepcopy(st.session_state.transactions)
        st.success("✅ 편집 저장 완료")
        st.rerun()

    # ✅ 검색어 인사이트(표 아래)
    kw = (keyword or "").strip()
    if kw:
        # "지출" 중에서 검색어 포함된 건수/합계
        df_kw = df.copy()
        df_kw = df_kw[(df_kw["type"] == "지출") & (df_kw["content"].fillna("").str.contains(kw, case=False, na=False))]
        cnt = len(df_kw)
        total = int(df_kw["amount"].sum()) if cnt else 0
        st.markdown(f"🧠 **검색어 \"{kw}\" 포함 지출:** **{cnt}건 / {format_won(total)}원**")


# ---------------------------------
# (B) 차트 탭
# ---------------------------------
with tab_chart:
    st.subheader("📊 카테고리별 지출 통계")

    # ✅ 차트도 데이터 없을 때는 '안전하게 안내'하고 끝
    if df.empty:
        st.info("표시할 데이터가 없습니다. (필터 조건을 바꾸거나 새 거래를 등록해보세요.)")
        st.stop()

    # 차트는 "지출"만 보는게 자연스러움
    df_exp = df[df["type"] == "지출"].copy()

    if df_exp.empty:
        st.info("선택한 필터 범위에 '지출' 데이터가 없습니다.")
        st.stop()

    # 카테고리별 합계
    cat_sum = df_exp.groupby("category", as_index=False)["amount"].sum()

    # ✅ 모든 카테고리가 항상 나오게(0도 표시) → 그래프가 매번 흔들리지 않음
    cat_sum = cat_sum.set_index("category").reindex(CATEGORIES, fill_value=0).reset_index()

    # ✅ Plotly 다크 테마 + 축 글자 정상 표시
    # (이전 에러의 핵심: Plotly에 없는 속성(titlefont 등)을 써서 터짐 → 여기서는 공식 속성만 사용)
    fig = px.bar(
        cat_sum,
        x="category",
        y="amount",
        color="category",
        color_discrete_map=CATEGORY_COLORS,
        text="amount",
        template="plotly_dark",
        labels={"category": "카테고리", "amount": "금액(원)"},
        title="카테고리별 지출 통계",
    )

    # ✅ 숫자 '5k' 같은 축 표기 싫다 → 쉼표 표기(5000, 10000)로 강제
    fig.update_yaxes(tickformat=",")  # 10000 → 10,000 형태

    # ✅ 축/글자 크기(Plotly는 tickfont/title_font 같은 공식 속성만 써야 안전)
    fig.update_xaxes(
        title_text="카테고리",
        tickfont=dict(size=14),
        title_font=dict(size=16),
        automargin=True,
    )
    fig.update_yaxes(
        title_text="금액(원)",
        tickfont=dict(size=14),
        title_font=dict(size=16),
        automargin=True,
    )

    # ✅ 바 위 텍스트도 원 단위로 보기 좋게
    fig.update_traces(texttemplate="%{text:,}", textposition="outside", cliponaxis=False)

    # ✅ 그래프 여백(텍스트 잘리지 않게)
    fig.update_layout(
        height=520,
        margin=dict(l=60, r=30, t=70, b=60),
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True)

    # ---- 인사이트(간단) : "이번 달 지출 TOP: 카테고리(%)" ----
    st.markdown("🧠 **인사이트(간단)**")

    # "이번 달" 기준: 사용자가 고른 기간의 end_date가 속한 달
    m_start, m_end = month_window_from_end(end_date)

    df_month = apply_filters(df_all, m_start, m_end, "", "전체", "전체")
    df_month_exp = df_month[df_month["type"] == "지출"].copy()

    if df_month_exp.empty:
        st.write("이번 달 지출 데이터가 아직 없어요.")
    else:
        top = df_month_exp.groupby("category")["amount"].sum().sort_values(ascending=False)
        top_cat = top.index[0]
        top_amt = int(top.iloc[0])
        total_amt = int(df_month_exp["amount"].sum())
        pct = round((top_amt / total_amt) * 100) if total_amt > 0 else 0
        st.write(f"이번 달 지출 TOP: **{top_cat}({pct}%)**")


# ---------------------------------
# (C) 관제(예산) 탭
# ---------------------------------
with tab_budget:
    st.subheader("🚨 관제(예산)")

    # ✅ 예산 탭도 데이터 없으면 그냥 안내만 하고 끝 (에러 방지)
    if df.empty:
        st.info("표시할 데이터가 없습니다. (필터 조건을 바꾸거나 새 거래를 등록해보세요.)")
        st.stop()

    # 이번 달 기준 (차트 인사이트와 동일 기준)
    m_start, m_end = month_window_from_end(end_date)
    df_month = apply_filters(df_all, m_start, m_end, "", "전체", "전체")
    df_month_exp = df_month[df_month["type"] == "지출"].copy()

    st.caption(f"이번 달 기준: {m_start} ~ {m_end}")

    # ✅ 예산 입력(카테고리별)
    # - 예산은 '기록'이 아니라 '설정'이므로 세션에 저장하면 편함
    if "budget" not in st.session_state:
        st.session_state.budget = {c: 0 for c in CATEGORIES}

    st.markdown("#### 📌 카테고리별 예산 설정(원)")
    bc = st.columns(len(CATEGORIES))
    for i, c in enumerate(CATEGORIES):
        with bc[i]:
            st.session_state.budget[c] = st.number_input(
                f"{c}",
                min_value=0,
                step=10000,
                value=int(st.session_state.budget.get(c, 0)),
                key=f"budget_{c}",
            )

    st.markdown("---")

    # 지출 합계 계산
    spent_by_cat = df_month_exp.groupby("category")["amount"].sum().to_dict()
    total_budget = sum(int(st.session_state.budget.get(c, 0)) for c in CATEGORIES)
    total_spent = int(df_month_exp["amount"].sum()) if not df_month_exp.empty else 0

    # 전체 관제
    st.markdown("#### ✅ 이번 달 전체 관제")
    if total_budget <= 0:
        st.info("전체 예산이 0원입니다. 위에서 예산을 입력하면 관제가 시작돼요.")
    else:
        ratio = min(total_spent / total_budget, 1.0)
        st.progress(ratio)
        st.write(f"총 지출: **{format_won(total_spent)}원** / 총 예산: **{format_won(total_budget)}원**")

        if total_spent > total_budget:
            st.error("🚨 예산 초과! 지출을 줄이거나 예산을 재설정하세요.")
        elif total_spent > total_budget * 0.8:
            st.warning("⚠️ 예산 80% 이상 사용 중입니다.")
        else:
            st.success("👍 예산 범위 내에서 관리 중입니다.")

    # 카테고리별 관제
    st.markdown("#### 📊 카테고리별 관제")
    for c in CATEGORIES:
        budget_c = int(st.session_state.budget.get(c, 0))
        spent_c = int(spent_by_cat.get(c, 0))

        if budget_c <= 0:
            st.write(f"- **{c}**: 지출 {format_won(spent_c)}원 / 예산 미설정")
            continue

        ratio_c = min(spent_c / budget_c, 1.0)
        st.write(f"**{c}**  |  지출 {format_won(spent_c)}원 / 예산 {format_won(budget_c)}원")
        st.progress(ratio_c)

        if spent_c > budget_c:
            st.error(f"🚨 {c} 예산 초과!")
        elif spent_c > budget_c * 0.8:
            st.warning(f"⚠️ {c} 예산 80% 이상 사용")
        else:
            st.caption(f"✅ {c} 정상 범위")

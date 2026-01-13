# app.py  # Streamlit UI 담당 (입력/표/요약/그래프/필터)

import os
import pandas as pd
import streamlit as st

# 팀 로직 모듈
from ledger.repository import load_transactions, save_transactions
from ledger.services import calc_summary, calc_category_expense

# 차트(한글 깨짐/축라벨 문제를 코드로 해결하기 위해 Plotly 사용)
import plotly.express as px


# -----------------------------
# (0) 기본 설정
# -----------------------------
st.set_page_config(page_title="나만의 미니 가계부", layout="wide")
DATA_PATH = os.path.join("data", "ledger.csv")

# 기본 카테고리(요청 반영)
BASE_CATEGORIES = ["식비", "교통", "통신", "생활", "기타"]


# -----------------------------
# (0-1) 보라 테마 CSS (고급스럽게)
# -----------------------------
st.markdown(
    """
<style>
/* 전체 톤 */
:root{
  --p1:#8B5CF6;   /* purple */
  --p2:#A78BFA;   /* light purple */
  --p3:#22C55E;   /* green accent */
  --bg1:#0B0F19;
  --card:#111827;
  --card2:#0F172A;
  --line:rgba(255,255,255,.10);
  --text:rgba(255,255,255,.90);
  --muted:rgba(255,255,255,.65);
}

/* 상단 여백 */
.block-container{padding-top: 1.6rem;}

/* 보라 헤더(얇은 빈 박스 문제 해결: 텍스트 넣는 전용 컴포넌트) */
.tx-hero{
  width:100%;
  border-radius: 18px;
  padding: 14px 18px;
  background: linear-gradient(90deg, rgba(139,92,246,.18), rgba(167,139,250,.10));
  border: 1px solid rgba(139,92,246,.35);
  box-shadow: 0 10px 30px rgba(0,0,0,.25);
  display:flex;
  align-items:center;
  justify-content:space-between;
  gap:12px;
  margin: 10px 0 12px 0;
}
.tx-hero .left{
  display:flex; align-items:center; gap:10px;
  color: var(--text);
  font-weight: 800;
  font-size: 1.05rem;
}
.tx-hero .badge{
  font-size:.85rem;
  color: rgba(255,255,255,.88);
  background: rgba(34,197,94,.18);
  border: 1px solid rgba(34,197,94,.35);
  padding: 4px 10px;
  border-radius: 999px;
  white-space: nowrap;
}

/* 폼 카드 */
.tx-card{
  width:100%;
  border-radius: 18px;
  padding: 16px 16px 6px 16px;
  background: linear-gradient(180deg, rgba(255,255,255,.04), rgba(255,255,255,.02));
  border: 1px solid var(--line);
  box-shadow: 0 14px 35px rgba(0,0,0,.28);
}

/* 버튼 보라 */
.stButton>button{
  background: linear-gradient(90deg, rgba(139,92,246,.95), rgba(167,139,250,.95)) !important;
  color: white !important;
  border: 0 !important;
  border-radius: 12px !important;
  padding: .55rem 1.0rem !important;
  font-weight: 800 !important;
}
.stButton>button:hover{filter: brightness(1.05);}

/* 탭 포인트 컬러 */
button[data-baseweb="tab"] p {font-weight:800;}
button[data-baseweb="tab"][aria-selected="true"]{
  border-bottom: 3px solid rgba(139,92,246,.95) !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# -----------------------------
# (1) 유틸: 리스트(dict) -> DataFrame
# -----------------------------
def to_df(transactions: list) -> pd.DataFrame:
    if not transactions:
        return pd.DataFrame(columns=["date", "type", "category", "description", "amount"])

    df = pd.DataFrame(transactions)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0).astype(int)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


# -----------------------------
# (2) 앱 시작: 데이터 로드
# -----------------------------
transactions = load_transactions(DATA_PATH)
df_all = to_df(transactions)

# 카테고리 옵션(사이드바/메인 폼 둘 다 반영)
existing_cats = []
if not df_all.empty:
    existing_cats = [c for c in df_all["category"].dropna().unique().tolist() if str(c).strip() != ""]
category_master = list(dict.fromkeys(BASE_CATEGORIES + sorted(existing_cats)))  # 중복 제거 + 유지


# -----------------------------
# (3) 타이틀
# -----------------------------
st.title("🧾 나만의 미니 가계부 (지출 관리 서비스)")
st.caption("입력 → 저장 → 즉시 반영되는 MVP 가계부")


# -----------------------------
# (4) 사이드바: 필터만 남김
# -----------------------------
st.sidebar.header("🔎 필터")

# 기간 필터 (선택 기간 데이터만 표시)
if df_all.empty or df_all["date"].isna().all():
    min_date = pd.Timestamp.today().date()
    max_date = pd.Timestamp.today().date()
else:
    min_date = df_all["date"].min().date()
    max_date = df_all["date"].max().date()

start_date, end_date = st.sidebar.date_input("기간 선택", value=(min_date, max_date))

# 검색어(키보드 입력)
keyword = st.sidebar.text_input("검색어(내용 포함)", value="")

# 구분/카테고리
type_filter = st.sidebar.selectbox("구분", ["전체", "지출", "수입"])
category_filter = st.sidebar.selectbox("카테고리", ["전체"] + category_master)


# -----------------------------
# (5) 새 거래 등록: 메인(제목/캡션 아래, 탭 위)
# -----------------------------
st.markdown(
    """
<div class="tx-hero">
  <div class="left">➕ 새 거래 등록</div>
  <div class="badge">즉시 저장</div>
</div>
""",
    unsafe_allow_html=True,
)

with st.container():
    st.markdown('<div class="tx-card">', unsafe_allow_html=True)

    with st.form("add_tx_form_main", clear_on_submit=True):
        c1, c2, c3 = st.columns([1.2, 1.0, 1.0])
        with c1:
            in_date = st.date_input("날짜")
        with c2:
            in_type = st.selectbox("구분", ["지출", "수입"])
        with c3:
            # 카테고리: 기본 5개 + 기존데이터 카테고리까지
            in_category = st.selectbox("카테고리", category_master, index=(category_master.index("식비") if "식비" in category_master else 0))

        # 내용/금액: 키보드 바로 입력 가능(요청 반영)
        in_desc = st.text_input("내용", value="", placeholder="예) 지하철 / 점심 / 통신요금 ...")
        in_amount = st.number_input("금액(원)", min_value=0, step=1000)

        submitted = st.form_submit_button("등록")

    st.markdown("</div>", unsafe_allow_html=True)

# 등록 처리
if submitted:
    if in_category.strip() == "":
        st.error("카테고리를 입력/선택하세요.")
    elif in_desc.strip() == "":
        st.error("내용을 입력하세요.")
    else:
        new_tx = {
            "date": str(in_date),
            "type": in_type,
            "category": in_category.strip(),
            "description": in_desc.strip(),
            "amount": int(in_amount),
        }
        transactions.append(new_tx)
        save_transactions(DATA_PATH, transactions)
        st.success(f"등록 완료 ✅ {new_tx['date']} / {new_tx['type']} / {new_tx['category']} / {new_tx['amount']:,}원")
        st.rerun()


# -----------------------------
# (6) 필터 적용 (선택 기간 데이터만 표시)
# -----------------------------
df = df_all.copy()

# 기간 필터: df['date']가 datetime일 때만 안전하게 동작
if not df.empty:
    df = df[df["date"].notna()]  # NaT 제거
    df = df[(df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)]

if type_filter != "전체":
    df = df[df["type"] == type_filter]

if category_filter != "전체":
    df = df[df["category"] == category_filter]

if keyword.strip() != "":
    df = df[df["description"].fillna("").str.lower().str.contains(keyword.strip().lower())]


# -----------------------------
# (7) 탭 (데이터/차트/관제예산) 이하 로직은 원래 구조 유지
# -----------------------------
tab_data, tab_chart, tab_alert = st.tabs(["📄 데이터", "📊 차트", "🚨 관제(예산)"])


# -----------------------------
# (8) 데이터 탭
# -----------------------------
with tab_data:
    st.subheader("📌 필터 결과 데이터")

    if df.empty:
        st.info("등록된 거래가 없습니다. (또는 필터 조건에 맞는 데이터가 없습니다.)")
    else:
        view_df = df.copy()
        view_df["date"] = view_df["date"].dt.strftime("%Y-%m-%d")
        view_df = view_df.sort_values("date", ascending=False)

        view_df = view_df[["date", "type", "category", "description", "amount"]]
        view_df.columns = ["날짜", "구분", "카테고리", "내용", "금액"]

        st.dataframe(view_df, use_container_width=True)


# -----------------------------
# (9) 차트 탭
# -----------------------------
with tab_chart:
    st.subheader("📌 요약 지표 (Metric)")

    filtered_transactions = []
    if not df.empty:
        tmp = df.copy()
        tmp["date"] = tmp["date"].dt.strftime("%Y-%m-%d")
        filtered_transactions = tmp.to_dict(orient="records")

    income, expense, balance = calc_summary(filtered_transactions)

    c1, c2, c3 = st.columns(3)
    c1.metric("총 수입", f"{income:,} 원")
    c2.metric("총 지출", f"{expense:,} 원")
    c3.metric("잔액(수입-지출)", f"{balance:,} 원")

    st.divider()
    st.subheader("📈 카테고리별 지출 통계")

    cat_map = calc_category_expense(filtered_transactions)

    if not cat_map:
        st.info("지출 데이터가 없어서 그래프를 표시할 수 없습니다.")
    else:
        cat_df = pd.DataFrame([{"카테고리": k, "금액": v} for k, v in cat_map.items()]).sort_values("금액", ascending=False)

        # ✅ 해결 1) WSL에서도 한글/축/숫자 안 보이던 문제: Plotly로 렌더링(브라우저 폰트 사용)
        # ✅ 해결 2) 카테고리 글자 세로(90도) 문제: tickangle=0 고정
        fig = px.bar(
            cat_df,
            x="카테고리",
            y="금액",
            title="카테고리별 지출 통계",
        )
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=10, r=10, t=50, b=10),
            xaxis_title="카테고리",
            yaxis_title="금액(원)",
            font=dict(size=14),
        )
        fig.update_xaxes(tickangle=0)
        st.plotly_chart(fig, use_container_width=True)


# -----------------------------
# (10) 관제 탭: 예산 경고
# -----------------------------
with tab_alert:
    st.subheader("🚨 지출 한도(예산) 관제")

    budget = st.number_input("월 예산 입력(원)", min_value=0, step=10000)

    filtered_transactions = []
    if not df.empty:
        tmp = df.copy()
        tmp["date"] = tmp["date"].dt.strftime("%Y-%m-%d")
        filtered_transactions = tmp.to_dict(orient="records")

    _, expense, _ = calc_summary(filtered_transactions)

    st.write(f"현재 지출 합계: **{expense:,} 원**")

    if budget > 0:
        ratio = expense / budget
        st.progress(min(ratio, 1.0))

        if ratio >= 1.0:
            st.error("❌ 예산을 초과했습니다!")
        elif ratio >= 0.8:
            st.warning("⚠️ 예산의 80%를 사용했습니다!")
        else:
            st.success("✅ 예산 사용이 안정적입니다.")
    else:
        st.info("예산을 입력하면 경고/진행률이 표시됩니다.")


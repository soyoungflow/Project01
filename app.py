# app.py  # Streamlit UI 담당 (입력/표/요약/그래프/필터)

import os
import pandas as pd
import streamlit as st
import plotly.express as px

from ledger.repository import load_transactions, save_transactions
from ledger.services import calc_summary, calc_category_expense


# -----------------------------
# (0) 기본 설정
# -----------------------------
st.set_page_config(page_title="나만의 미니 가계부", layout="wide")
DATA_PATH = os.path.join("data", "ledger.csv")

DEFAULT_CATEGORIES = ["식비", "교통", "통신", "생활", "기타"]


# -----------------------------
# (0-1) 보라 테마 CSS
# -----------------------------
st.markdown(
    """
<style>
:root{
  --p1:#8b5cf6;
  --p2:#a78bfa;
  --p3:#22c55e;
  --card:rgba(255,255,255,0.06);
  --border:rgba(255,255,255,0.10);
  --text:rgba(255,255,255,0.92);
  --muted:rgba(255,255,255,0.70);
}
.block-container { padding-top: 1.4rem; }
h1, h2, h3 { color: var(--text) !important; }
p, .stCaption { color: var(--muted) !important; }

.purple-banner{
  border: 1px solid rgba(139,92,246,0.45);
  background: linear-gradient(90deg, rgba(139,92,246,0.18), rgba(167,139,250,0.10));
  border-radius: 18px;
  padding: 14px 18px;
  margin: 14px 0 10px 0;
  box-shadow: 0 10px 35px rgba(0,0,0,0.25);
}
.purple-title{
  display:flex;
  align-items:center;
  gap:10px;
  font-weight: 800;
  font-size: 20px;
  color: var(--text);
}
.pill{
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 999px;
  border: 1px solid rgba(34,197,94,0.45);
  background: rgba(34,197,94,0.18);
  color: rgba(220,255,235,0.95);
  font-weight: 700;
}
.card{
  border: 1px solid var(--border);
  background: var(--card);
  border-radius: 16px;
  padding: 16px 16px 8px 16px;
  margin-bottom: 10px;
}

/* 버튼 보라 */
.stButton > button, .stFormSubmitButton > button{
  background: linear-gradient(90deg, var(--p1), var(--p2)) !important;
  border: 0 !important;
  color: white !important;
  border-radius: 12px !important;
  padding: 0.55rem 1.1rem !important;
  font-weight: 800 !important;
  box-shadow: 0 10px 25px rgba(139,92,246,0.22) !important;
}
.stButton > button:hover, .stFormSubmitButton > button:hover{
  filter: brightness(1.03);
  transform: translateY(-1px);
}

/* 사이드바 타이틀 색 */
section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
  color: rgba(167,139,250,0.95) !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# -----------------------------
# (0-2) session_state: Undo(복구)용
# -----------------------------
if "last_snapshot" not in st.session_state:
    st.session_state.last_snapshot = None  # 삭제/수정 직전 백업(list[dict])
if "last_action" not in st.session_state:
    st.session_state.last_action = None  # "delete" / "edit" 등


def snapshot_now(current_transactions: list, action: str) -> None:
    """삭제/수정 직전에 전체 백업을 세션에 저장(Undo 1회)."""
    st.session_state.last_snapshot = [dict(x) for x in current_transactions]
    st.session_state.last_action = action


def undo_if_possible() -> bool:
    """가능하면 마지막 백업으로 복구하고 True 반환."""
    snap = st.session_state.get("last_snapshot")
    if not snap:
        return False
    save_transactions(DATA_PATH, snap)
    st.session_state.last_snapshot = None
    st.session_state.last_action = None
    return True


# -----------------------------
# (1) 유틸: 리스트(dict) -> DataFrame
# -----------------------------
def to_df(transactions: list) -> pd.DataFrame:
    if not transactions:
        return pd.DataFrame(columns=["__idx", "date", "type", "category", "description", "amount"])

    safe_rows = []
    for i, t in enumerate(transactions):
        safe_rows.append(
            {
                "__idx": i,
                "date": t.get("date", ""),
                "type": t.get("type", ""),
                "category": t.get("category", ""),
                "description": t.get("description", ""),
                "amount": t.get("amount", 0),
            }
        )

    df = pd.DataFrame(safe_rows)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0).astype(int)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


# -----------------------------
# (2) 데이터 로드
# -----------------------------
transactions = load_transactions(DATA_PATH)
df_all = to_df(transactions)


# -----------------------------
# (3) 타이틀
# -----------------------------
st.title("🧾 나만의 미니 가계부 (지출 관리 서비스)")
st.caption("입력 → 저장 → 즉시 반영되는 MVP 가계부")


# -----------------------------
# (4) 사이드바: 필터
# -----------------------------
st.sidebar.header("🔎 필터")

if df_all.empty or df_all["date"].isna().all():
    min_date = pd.Timestamp.today().date()
    max_date = pd.Timestamp.today().date()
else:
    min_date = df_all["date"].min().date()
    max_date = df_all["date"].max().date()

start_date, end_date = st.sidebar.date_input("기간 선택", value=(min_date, max_date))
keyword = st.sidebar.text_input("검색어(내용 포함)", value="", placeholder="예) 지하철 / 점심 / 통신요금...")

type_filter = st.sidebar.selectbox("구분", ["전체", "지출", "수입"])

category_set = set(DEFAULT_CATEGORIES)
if not df_all.empty:
    category_set |= set(df_all["category"].dropna().astype(str).tolist())
category_options = ["전체"] + sorted(category_set)
category_filter = st.sidebar.selectbox("카테고리", category_options)

st.sidebar.divider()


# -----------------------------
# (5) 메인: 새 거래 등록(탭 위)
# -----------------------------
st.markdown(
    """
<div class="purple-banner">
  <div class="purple-title">
    <span style="font-size:22px;">➕</span>
    <span>새 거래 등록</span>
    <span class="pill">즉시 저장</span>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

with st.container():
    st.markdown('<div class="card">', unsafe_allow_html=True)

    with st.form("add_tx_form_main", clear_on_submit=True):
        c1, c2, c3 = st.columns([1.2, 1.0, 1.2])
        with c1:
            in_date = st.date_input("날짜")
        with c2:
            in_type = st.selectbox("구분", ["지출", "수입"])
        with c3:
            main_cat_set = set(DEFAULT_CATEGORIES)
            if not df_all.empty:
                main_cat_set |= set(df_all["category"].dropna().astype(str).tolist())
            main_cat_options = sorted(main_cat_set)
            in_category = st.selectbox("카테고리", main_cat_options, index=0)

        in_desc = st.text_input("내용", value="", placeholder="예) 지하철 / 점심 / 통신요금 ...")
        in_amount = st.number_input("금액(원)", min_value=0, step=1000, value=0)

        submitted = st.form_submit_button("등록")

    st.markdown("</div>", unsafe_allow_html=True)

if submitted:
    if str(in_desc).strip() == "":
        st.error("내용을 입력하세요.")
    else:
        new_tx = {
            "date": str(in_date),
            "type": in_type,
            "category": str(in_category).strip(),
            "description": str(in_desc).strip(),
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
df = df[df["date"].notna()]
df = df[(df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)]

if type_filter != "전체":
    df = df[df["type"] == type_filter]
if category_filter != "전체":
    df = df[df["category"] == category_filter]
if keyword.strip() != "":
    df = df[df["description"].fillna("").str.lower().str.contains(keyword.strip().lower())]


# -----------------------------
# (7) 탭
# -----------------------------
tab_data, tab_chart, tab_alert = st.tabs(["📄 데이터", "📊 차트", "🚨 관제(예산)"])


# -----------------------------
# (8) 데이터 탭: 표 + 삭제 + Undo + 수정(Edit)
# -----------------------------
with tab_data:
    st.subheader("📌 필터 결과 데이터")

    # 상단 툴바: Undo / 마지막1건삭제
    t1, t2, t3 = st.columns([1.2, 1.6, 3.2])
    with t1:
        if st.button("🧯 실행 취소(Undo)"):
            if undo_if_possible():
                st.success("복구 완료 ✅")
                st.rerun()
            else:
                st.info("복구할 작업이 없습니다.")
    with t2:
        if st.button("↩️ 마지막 1건 삭제"):
            if len(transactions) == 0:
                st.info("삭제할 데이터가 없습니다.")
            else:
                snapshot_now(transactions, action="delete_last")  # ✅ Undo 백업
                transactions.pop()
                save_transactions(DATA_PATH, transactions)
                st.success("마지막 1건 삭제 완료 ✅")
                st.rerun()

    if df.empty:
        st.info("등록된 거래가 없습니다. (또는 필터 조건에 맞는 데이터가 없습니다.)")
    else:
        view_df = df.copy()
        view_df["date"] = view_df["date"].dt.strftime("%Y-%m-%d")
        view_df["삭제"] = False  # 선택 삭제 체크
        # ✅ 편집 가능 컬럼: 날짜/구분/카테고리/내용/금액
        show_df = view_df[["삭제", "__idx", "date", "type", "category", "description", "amount"]].copy()
        show_df.columns = ["삭제", "__idx", "날짜", "구분", "카테고리", "내용", "금액"]

        # 편집용 옵션
        edit_cat_set = set(DEFAULT_CATEGORIES)
        edit_cat_set |= set(df_all["category"].dropna().astype(str).tolist()) if not df_all.empty else set()
        edit_cat_options = sorted(edit_cat_set)

        edited = st.data_editor(
            show_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "삭제": st.column_config.CheckboxColumn(help="체크한 항목을 삭제합니다."),
                "__idx": st.column_config.NumberColumn(help="삭제/수정 매핑용(건드리지 마세요)"),
                "날짜": st.column_config.TextColumn(help="YYYY-MM-DD"),
                "구분": st.column_config.SelectboxColumn(options=["지출", "수입"]),
                "카테고리": st.column_config.SelectboxColumn(options=edit_cat_options),
                "금액": st.column_config.NumberColumn(format="%d"),
            },
            # ✅ 이제 편집 가능: 날짜/구분/카테고리/내용/금액
            disabled=["__idx"],
        )

        b1, b2 = st.columns([1.2, 3.8])
        with b1:
            if st.button("🗑️ 체크된 항목 선택 삭제"):
                idxs = edited.loc[edited["삭제"] == True, "__idx"].tolist()
                if not idxs:
                    st.info("삭제할 항목을 먼저 체크하세요.")
                else:
                    snapshot_now(transactions, action="delete_selected")  # ✅ Undo 백업
                    for i in sorted(map(int, idxs), reverse=True):
                        if 0 <= i < len(transactions):
                            transactions.pop(i)
                    save_transactions(DATA_PATH, transactions)
                    st.success(f"선택 삭제 완료 ✅ ({len(idxs)}건)")
                    st.rerun()

        with b2:
            if st.button("💾 수정사항 저장(편집 저장)"):
                # 변경사항을 transactions에 반영
                snapshot_now(transactions, action="edit")  # ✅ Undo 백업

                # 원본을 복사해서 idx 기준으로 덮어쓰기
                new_list = [dict(x) for x in transactions]

                for _, row in edited.iterrows():
                    idx = int(row["__idx"])
                    if 0 <= idx < len(new_list):
                        # 날짜 파싱(실패하면 기존 유지)
                        d = pd.to_datetime(row["날짜"], errors="coerce")
                        date_str = (
                            d.strftime("%Y-%m-%d")
                            if pd.notna(d)
                            else str(new_list[idx].get("date", ""))
                        )

                        new_list[idx] = {
                            "date": date_str,
                            "type": str(row["구분"]),
                            "category": str(row["카테고리"]),
                            "description": str(row["내용"]),
                            "amount": int(pd.to_numeric(row["금액"], errors="coerce") or 0),
                        }

                save_transactions(DATA_PATH, new_list)
                st.success("수정 저장 완료 ✅ (Undo로 되돌릴 수 있음)")
                st.rerun()


# -----------------------------
# (9) 차트 탭
# -----------------------------
with tab_chart:
    st.subheader("📌 요약 지표 (Metric)")

    filtered_transactions = []
    if not df.empty:
        tmp = df.copy()
        tmp["date"] = tmp["date"].dt.strftime("%Y-%m-%d")
        filtered_transactions = tmp.drop(columns=["__idx"], errors="ignore").to_dict(orient="records")

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
        for c in DEFAULT_CATEGORIES:
            cat_map.setdefault(c, 0)

        cat_df = pd.DataFrame([{"카테고리": k, "금액(원)": v} for k, v in cat_map.items()])
        cat_df = cat_df.sort_values("금액(원)", ascending=False)

        fig = px.bar(cat_df, x="카테고리", y="금액(원)", title="카테고리별 지출 통계")
        fig.update_yaxes(tickformat=",")  # ✅ 5k → 5000 (콤마 포함)
        fig.update_layout(
            height=520,
            margin=dict(l=10, r=10, t=60, b=10),
            xaxis_title="카테고리",
            yaxis_title="금액(원)",
        )
        st.plotly_chart(fig, use_container_width=True)


# -----------------------------
# (10) 관제 탭
# -----------------------------
with tab_alert:
    st.subheader("🚨 지출 한도(예산) 관제")

    budget = st.number_input("월 예산 입력(원)", min_value=0, step=10000, value=0)

    filtered_transactions = []
    if not df.empty:
        tmp = df.copy()
        tmp["date"] = tmp["date"].dt.strftime("%Y-%m-%d")
        filtered_transactions = tmp.drop(columns=["__idx"], errors="ignore").to_dict(orient="records")

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

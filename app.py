# app.py  # Streamlit UI 담당 (입력/표/요약/그래프/필터)

import os
import pandas as pd
import streamlit as st

# (차트용) matplotlib
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

# 팀원이 만든 로직 모듈 import  # ← "UI는 호출만 한다" 원칙
from ledger.repository import load_transactions, save_transactions  # CSV I/O
from ledger.services import calc_summary, calc_category_expense  # 통계 계산


# -----------------------------
# (0) 기본 설정
# -----------------------------
st.set_page_config(page_title="나만의 미니 가계부", layout="wide")

DATA_PATH = os.path.join("data", "ledger.csv")

# -----------------------------
# (0-1) 고급 보라 테마 CSS
# -----------------------------
st.markdown(
    """
<style>
:root{
  --p1:#7C3AED; /* violet */
  --p2:#A855F7; /* purple */
  --p3:#22C55E; /* green */
  --bg1:#0B0C10;
  --bg2:#0F111A;
  --card:#141724;
  --card2:#101321;
  --line:rgba(255,255,255,0.08);
  --txt:rgba(255,255,255,0.92);
  --muted:rgba(255,255,255,0.65);
}

section.main > div { padding-top: 1.2rem; }

.purple-bar{
  width:100%;
  border-radius: 999px;
  padding: 12px 18px;
  border: 1px solid rgba(168,85,247,0.35);
  background: linear-gradient(90deg, rgba(124,58,237,0.22), rgba(168,85,247,0.10));
  box-shadow: 0 8px 28px rgba(124,58,237,0.10);
  display:flex;
  align-items:center;
  gap:10px;
  color: var(--txt);
  font-weight: 800;
  letter-spacing: -0.2px;
}
.purple-pill{
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(34,197,94,0.18);
  border: 1px solid rgba(34,197,94,0.30);
  color: rgba(210,255,225,0.95);
  font-weight: 700;
  font-size: 0.85rem;
}
.purple-icon{ color: rgba(168,85,247,0.95); font-weight:900; }

.stButton > button{
  border-radius: 14px !important;
  border: 1px solid rgba(168,85,247,0.35) !important;
  background: linear-gradient(180deg, rgba(124,58,237,0.95), rgba(168,85,247,0.88)) !important;
  color: white !important;
  font-weight: 800 !important;
  padding: 0.55rem 0.95rem !important;
  box-shadow: 0 10px 30px rgba(124,58,237,0.16) !important;
}
.stButton > button:hover{
  transform: translateY(-1px);
  filter: brightness(1.04);
}

div[data-testid="stForm"]{
  border: 1px solid var(--line);
  background: linear-gradient(180deg, rgba(20,23,36,0.92), rgba(16,19,33,0.92));
  border-radius: 18px;
  padding: 16px 16px 6px 16px;
  box-shadow: 0 12px 40px rgba(0,0,0,0.22);
}

div[data-testid="stDataFrame"]{
  border-radius: 16px;
  overflow:hidden;
  border: 1px solid var(--line);
}

hr{
  border-top: 1px solid var(--line) !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# (0-2) matplotlib 한글/축 표시 안정화 (조용히 처리)
# -----------------------------
def _set_matplotlib_font_safely():
    # 환경에 따라 설치된 폰트가 다르니, 있으면 그걸 쓰고 없으면 기본값
    candidates = ["NanumGothic", "Noto Sans CJK KR", "AppleGothic", "Malgun Gothic", "DejaVu Sans"]
    for name in candidates:
        try:
            plt.rcParams["font.family"] = name
            break
        except Exception:
            pass
    plt.rcParams["axes.unicode_minus"] = False

_set_matplotlib_font_safely()


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

# Undo를 위한 스냅샷(최초 1회)
if "undo_stack" not in st.session_state:
    st.session_state.undo_stack = []
if "last_action" not in st.session_state:
    st.session_state.last_action = ""

df_all = to_df(transactions)

# 카테고리 기본 세트 + 데이터에 있는 것 합치기
BASE_CATEGORIES = ["식비", "교통", "통신", "생활", "기타"]
data_categories = []
if not df_all.empty:
    data_categories = sorted(df_all["category"].dropna().astype(str).unique().tolist())

CATEGORY_POOL = []
for c in BASE_CATEGORIES + data_categories:
    c = str(c).strip()
    if c and c not in CATEGORY_POOL:
        CATEGORY_POOL.append(c)


# -----------------------------
# (3) 타이틀
# -----------------------------
st.title("🧾 나만의 미니 가계부 (지출 관리 서비스)")
st.caption("입력 → 저장 → 즉시 반영되는 MVP 가계부")

# -----------------------------
# (4) 메인: 새 거래 등록 (제목/캡션 아래, 탭 위)
# -----------------------------
st.markdown(
    """
<div class="purple-bar">
  <span class="purple-icon">＋</span>
  <span style="font-size:1.05rem;">새 거래 등록</span>
  <span class="purple-pill">즉시 저장</span>
</div>
""",
    unsafe_allow_html=True,
)

with st.form("add_tx_form_main", clear_on_submit=True):
    c1, c2, c3, c4 = st.columns([1.2, 1.2, 1.4, 1.2])

    with c1:
        in_date = st.date_input("날짜")
    with c2:
        in_type = st.selectbox("구분", ["지출", "수입"])
    with c3:
        # 원하는 고정 카테고리 + 데이터 카테고리까지 같이 노출
        in_category = st.selectbox("카테고리", CATEGORY_POOL, index=0 if CATEGORY_POOL else 0)
    with c4:
        in_amount = st.number_input("금액(원)", min_value=0, step=1000)

    in_desc = st.text_input("내용", value="", placeholder="예) 지하철 / 점심 / 통신요금 ...")

    submitted = st.form_submit_button("등록")

if submitted:
    if str(in_category).strip() == "":
        st.error("카테고리를 선택하세요.")
    elif str(in_desc).strip() == "":
        st.error("내용을 입력하세요.")
    else:
        # Undo 스냅샷 저장
        st.session_state.undo_stack.append([dict(x) for x in transactions])

        new_tx = {
            "date": str(in_date),  # YYYY-MM-DD
            "type": in_type,
            "category": str(in_category).strip(),
            "description": str(in_desc).strip(),
            "amount": int(in_amount),
        }

        transactions.append(new_tx)
        save_transactions(DATA_PATH, transactions)
        st.session_state.last_action = "add"
        st.success(f"등록 완료 ✅ {new_tx['date']} / {new_tx['type']} / {new_tx['category']} / {new_tx['amount']:,}원")
        st.rerun()

st.divider()


# -----------------------------
# (5) 사이드바: 필터만 남김
# -----------------------------
st.sidebar.header("🔎 필터")

# 기간 필터
if df_all.empty or df_all["date"].isna().all():
    min_date = pd.Timestamp.today().date()
    max_date = pd.Timestamp.today().date()
else:
    min_date = df_all["date"].min().date()
    max_date = df_all["date"].max().date()

start_date, end_date = st.sidebar.date_input("기간 선택", value=(min_date, max_date))

keyword = st.sidebar.text_input("검색어(내용 포함)", value="")  # 타이핑 OK
type_filter = st.sidebar.selectbox("구분", ["전체", "지출", "수입"])

category_options = ["전체"] + CATEGORY_POOL
category_filter = st.sidebar.selectbox("카테고리", category_options)

# -----------------------------
# (6) 필터 적용 (선택 기간 데이터만 표시)
# -----------------------------
df = df_all.copy()

# date가 NaT인 행은 필터에서 제외(안전)
df = df[df["date"].notna()]

# 기간 필터
df = df[(df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)]

# 구분 필터
if type_filter != "전체":
    df = df[df["type"] == type_filter]

# 카테고리 필터
if category_filter != "전체":
    df = df[df["category"] == category_filter]

# 검색 필터
if keyword.strip() != "":
    df = df[df["description"].fillna("").str.lower().str.contains(keyword.strip().lower())]


# -----------------------------
# (7) 탭
# -----------------------------
tab_data, tab_chart, tab_alert = st.tabs(["📄 데이터", "📊 차트", "🚨 관제(예산)"])


# -----------------------------
# (8) 데이터 탭: 표 + 편집/삭제/Undo
# -----------------------------
with tab_data:
    st.subheader("📌 필터 결과 데이터")

    if df.empty:
        st.info("등록된 거래가 없습니다. (또는 필터 조건에 맞는 데이터가 없습니다.)")
    else:
        # 표시용 DF: 원본 transactions의 인덱스를 추적해야 삭제/편집이 안전함
        # 1) 전체 df_all에서 현재 필터 df의 행을 찾기 위해, 원본 인덱스(_idx)를 부여
        df_all_with_idx = df_all.copy()
        df_all_with_idx["_idx"] = df_all_with_idx.index  # df_all이 transactions 순서 그대로 만들어졌다는 전제

        # date 문자열 비교를 위해 동일 포맷으로 맞춤
        _df = df.copy()
        _df["_key_date"] = _df["date"].dt.strftime("%Y-%m-%d")
        _df["_key_type"] = _df["type"].astype(str)
        _df["_key_cat"] = _df["category"].astype(str)
        _df["_key_desc"] = _df["description"].astype(str)
        _df["_key_amt"] = _df["amount"].astype(int)

        _all = df_all_with_idx.copy()
        _all["_key_date"] = _all["date"].dt.strftime("%Y-%m-%d")
        _all["_key_type"] = _all["type"].astype(str)
        _all["_key_cat"] = _all["category"].astype(str)
        _all["_key_desc"] = _all["description"].astype(str)
        _all["_key_amt"] = _all["amount"].astype(int)

        # 단순 merge로 idx 매핑 (동일 레코드가 중복이면 100% 완벽하진 않지만, MVP에선 충분)
        merged = pd.merge(
            _df,
            _all[["_idx", "_key_date", "_key_type", "_key_cat", "_key_desc", "_key_amt"]],
            on=["_key_date", "_key_type", "_key_cat", "_key_desc", "_key_amt"],
            how="left",
        )

        view_df = merged.copy()
        view_df["date"] = view_df["_key_date"]
        view_df = view_df.drop(columns=["_key_date", "_key_type", "_key_cat", "_key_desc", "_key_amt"])

        # 삭제 체크박스 + 편집 가능한 표 구성
        editor_df = pd.DataFrame(
            {
                "삭제": [False] * len(view_df),
                "_idx": view_df["_idx"].fillna(-1).astype(int),
                "날짜": view_df["date"],
                "구분": view_df["type"],
                "카테고리": view_df["category"],
                "내용": view_df["description"],
                "금액": view_df["amount"].astype(int),
            }
        )

        # 4개 버튼을 "1열(가로 한 줄)"로 배치
        b1, b2, b3, b4 = st.columns(4)
        undo_clicked = b1.button("🧯 실행 취소(Undo)", use_container_width=True)
        last_del_clicked = b2.button("↩️ 마지막 1건 삭제", use_container_width=True)
        checked_del_clicked = b3.button("🗑️ 체크된 항목 선택 삭제", use_container_width=True)
        save_edit_clicked = b4.button("💾 수정사항 저장(편집 저장)", use_container_width=True)

        edited = st.data_editor(
            editor_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "삭제": st.column_config.CheckboxColumn("삭제", help="삭제할 행 체크"),
                "_idx": st.column_config.NumberColumn("_idx", help="원본 인덱스(삭제/수정용)", disabled=True),
                "날짜": st.column_config.TextColumn("날짜", help="YYYY-MM-DD"),
                "구분": st.column_config.SelectboxColumn("구분", options=["지출", "수입"]),
                "카테고리": st.column_config.SelectboxColumn("카테고리", options=CATEGORY_POOL),
                "내용": st.column_config.TextColumn("내용"),
                "금액": st.column_config.NumberColumn("금액", step=1000, min_value=0),
            },
        )

        # (A) Undo
        if undo_clicked:
            if st.session_state.undo_stack:
                prev = st.session_state.undo_stack.pop()
                save_transactions(DATA_PATH, prev)
                st.success("되돌렸습니다 ✅")
                st.rerun()
            else:
                st.info("되돌릴 기록이 없습니다.")

        # (B) 마지막 1건 삭제
        if last_del_clicked:
            if transactions:
                st.session_state.undo_stack.append([dict(x) for x in transactions])
                transactions.pop()
                save_transactions(DATA_PATH, transactions)
                st.success("마지막 1건 삭제 완료 ✅")
                st.rerun()
            else:
                st.info("삭제할 데이터가 없습니다.")

        # (C) 체크된 항목 삭제
        if checked_del_clicked:
            targets = edited[(edited["삭제"] == True) & (edited["_idx"] >= 0)]["_idx"].astype(int).tolist()
            targets = sorted(set(targets), reverse=True)  # 뒤에서부터 삭제
            if not targets:
                st.info("체크된 항목이 없습니다.")
            else:
                st.session_state.undo_stack.append([dict(x) for x in transactions])
                for idx in targets:
                    if 0 <= idx < len(transactions):
                        transactions.pop(idx)
                save_transactions(DATA_PATH, transactions)
                st.success(f"선택 삭제 완료 ✅ ({len(targets)}건)")
                st.rerun()

        # (D) 편집 저장
        if save_edit_clicked:
            # 편집된 내용을 원본 transactions에 반영
            rows = edited[edited["_idx"] >= 0].copy()
            if rows.empty:
                st.info("수정할 데이터가 없습니다.")
            else:
                st.session_state.undo_stack.append([dict(x) for x in transactions])

                # idx별로 업데이트
                for _, r in rows.iterrows():
                    idx = int(r["_idx"])
                    if not (0 <= idx < len(transactions)):
                        continue

                    # 날짜 파싱 → YYYY-MM-DD 문자열로 저장
                    dt = pd.to_datetime(r["날짜"], errors="coerce")
                    date_str = str(dt.date()) if pd.notna(dt) else transactions[idx].get("date", "")

                    transactions[idx] = {
                        "date": date_str,
                        "type": str(r["구분"]).strip(),
                        "category": str(r["카테고리"]).strip(),
                        "description": str(r["내용"]).strip(),
                        "amount": int(pd.to_numeric(r["금액"], errors="coerce") or 0),
                    }

                save_transactions(DATA_PATH, transactions)
                st.success("수정사항 저장 완료 ✅")
                st.rerun()


# -----------------------------
# (9) 차트 탭: 요약 + 그래프
# -----------------------------
with tab_chart:
    st.subheader("📌 요약 지표 (Metric)")

    # 필터 DF -> list[dict]
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
        cat_df = (
            pd.DataFrame([{"category": k, "amount": v} for k, v in cat_map.items()])
            .sort_values("amount", ascending=False)
        )

        # matplotlib로 직접 그려서
        # - x축 라벨 가로
        # - y축 5k 같은 축약 없이 5000/10000/15000
        fig, ax = plt.subplots(figsize=(9.5, 4.8))
        ax.bar(cat_df["category"], cat_df["amount"])

        ax.set_title("카테고리별 지출 통계", pad=12)
        ax.set_xlabel("카테고리")
        ax.set_ylabel("금액(원)")

        ax.tick_params(axis="x", labelrotation=0)
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: f"{int(x):,}"))

        ax.grid(axis="y", alpha=0.25)
        fig.tight_layout()

        st.pyplot(fig, use_container_width=True)


# -----------------------------
# (10) 관제 탭: 예산 경고
# -----------------------------
with tab_alert:
    st.subheader("🚨 지출 한도(예산) 관제")

    budget = st.number_input("월 예산 입력(원)", min_value=0, step=10000)

    # 현재 필터 기준 지출 합계
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

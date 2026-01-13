# app.py  # Streamlit UI 담당 (입력/표/요약/그래프/필터)

import os
import re
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

# -----------------------------
# (0-1) 보라 테마 CSS
# -----------------------------
st.markdown(
    """
<style>
:root{
  --bg:#0b0f17;
  --card:#121826;
  --card2:#0f1522;
  --stroke:rgba(255,255,255,0.08);
  --text:rgba(255,255,255,0.92);
  --muted:rgba(255,255,255,0.68);
  --purple:#8b5cf6;
  --purple2:#a78bfa;
  --purple3:#6d28d9;
  --good:#22c55e;
}

.block-container { padding-top: 2.0rem; }

.purple-bar{
  width:100%;
  padding:16px 18px;
  border-radius:16px;
  background: linear-gradient(90deg, rgba(139,92,246,0.22), rgba(167,139,250,0.10));
  border: 1px solid rgba(139,92,246,0.35);
  color: var(--text);
  font-weight: 800;
  font-size: 18px;
  letter-spacing: -0.2px;
  display:flex;
  align-items:center;
  gap:10px;
  box-shadow: 0 8px 22px rgba(0,0,0,0.35);
  margin: 8px 0 12px 0;
}
.purple-pill{
  margin-left:10px;
  font-size:12px;
  font-weight:700;
  color: rgba(255,255,255,0.92);
  background: rgba(34,197,94,0.16);
  border: 1px solid rgba(34,197,94,0.35);
  padding: 4px 10px;
  border-radius: 999px;
}

.purple-card{
  background: linear-gradient(180deg, rgba(18,24,38,0.90), rgba(10,14,22,0.90));
  border: 1px solid var(--stroke);
  border-radius: 18px;
  padding: 18px 18px;
  box-shadow: 0 10px 28px rgba(0,0,0,0.35);
}

.stButton>button{
  background: linear-gradient(90deg, rgba(139,92,246,0.95), rgba(167,139,250,0.90));
  border: 1px solid rgba(255,255,255,0.10);
  color: white;
  border-radius: 14px;
  padding: 0.6rem 1.0rem;
  font-weight: 800;
  box-shadow: 0 10px 20px rgba(139,92,246,0.18);
}
.stButton>button:hover{
  filter: brightness(1.05);
  border-color: rgba(255,255,255,0.18);
}

div[data-testid="stDataFrame"]{
  border: 1px solid var(--stroke) !important;
  border-radius: 16px !important;
  overflow: hidden !important;
}
div[data-testid="stDataEditor"]{
  border: 1px solid var(--stroke) !important;
  border-radius: 16px !important;
  overflow: hidden !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------
# (1) 유틸
# -----------------------------
BASE_CATEGORIES = ["식비", "교통", "통신", "생활", "기타"]


def parse_amount(text: str) -> int:
    """'10,000' / '10000원' 같은 입력을 정수로 파싱"""
    s = re.sub(r"[^\d]", "", str(text))
    if s == "":
        return 0
    return int(s)


def normalize_transactions(transactions: list) -> list:
    """저장 직전 안전하게 정리(키/타입 보정)"""
    out = []
    for t in transactions:
        out.append(
            {
                "date": str(t.get("date", ""))[:10],
                "type": t.get("type", "지출"),
                "category": t.get("category", "기타"),
                "description": t.get("description", ""),
                "amount": int(pd.to_numeric(t.get("amount", 0), errors="coerce") or 0),
            }
        )
    return out


def to_df(transactions: list) -> pd.DataFrame:
    # 비어 있어도 dtype까지 세팅해서 .dt 에러 원천 차단
    df = pd.DataFrame(transactions, columns=["date", "type", "category", "description", "amount"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0).astype(int)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")  # <- 핵심: empty여도 datetime64 dtype
    return df


def df_to_transactions(df: pd.DataFrame) -> list:
    tmp = df.copy()
    tmp["date"] = pd.to_datetime(tmp["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    tmp["amount"] = pd.to_numeric(tmp["amount"], errors="coerce").fillna(0).astype(int)
    tmp["type"] = tmp["type"].fillna("지출")
    tmp["category"] = tmp["category"].fillna("기타")
    tmp["description"] = tmp["description"].fillna("")
    return tmp[["date", "type", "category", "description", "amount"]].to_dict(orient="records")


# -----------------------------
# (2) 데이터 로드
# -----------------------------
transactions = load_transactions(DATA_PATH)
transactions = normalize_transactions(transactions)
df_all = to_df(transactions)

# Undo용 스냅샷
if "undo_stack" not in st.session_state:
    st.session_state.undo_stack = []  # list[list[dict]]


def push_undo(snapshot: list):
    # 너무 커지는 거 방지(최근 5개만)
    st.session_state.undo_stack.append(snapshot)
    st.session_state.undo_stack = st.session_state.undo_stack[-5:]


def do_save(new_transactions: list):
    new_transactions = normalize_transactions(new_transactions)
    save_transactions(DATA_PATH, new_transactions)
    st.rerun()


# -----------------------------
# (3) 타이틀
# -----------------------------
st.title("🧾 나만의 미니 가계부 (지출 관리 서비스)")
st.caption("입력 → 저장 → 즉시 반영되는 MVP 가계부")

# -----------------------------
# (4) 사이드바: 필터만 남김
# -----------------------------
st.sidebar.header("🔎 필터")

# 안전한 min/max (데이터 없어도 OK)
if df_all.empty or df_all["date"].isna().all():
    min_date = pd.Timestamp.today().date()
    max_date = pd.Timestamp.today().date()
else:
    min_date = df_all["date"].min().date()
    max_date = df_all["date"].max().date()

start_date, end_date = st.sidebar.date_input("기간 선택", value=(min_date, max_date))
keyword = st.sidebar.text_input("검색어(내용 포함)", value="")  # 타이핑 입력 OK
type_filter = st.sidebar.selectbox("구분", ["전체", "지출", "수입"])

# 카테고리 옵션: 기본 5개 + 데이터에 있는 커스텀까지 합치기
cats_in_data = []
if not df_all.empty:
    cats_in_data = sorted([c for c in df_all["category"].dropna().unique().tolist() if str(c).strip() != ""])
category_pool = list(dict.fromkeys(BASE_CATEGORIES + cats_in_data))  # 중복 제거 + 순서 유지
category_options = ["전체"] + category_pool
category_filter = st.sidebar.selectbox("카테고리", category_options)

# -----------------------------
# (5) 메인: 새 거래 등록(제목/캡션 아래, 탭 위)
# -----------------------------
st.markdown(
    '<div class="purple-bar">➕ 새 거래 등록 <span class="purple-pill">즉시 저장</span></div>',
    unsafe_allow_html=True,
)

st.markdown('<div class="purple-card">', unsafe_allow_html=True)

with st.form("add_tx_form_main", clear_on_submit=True):
    c1, c2, c3 = st.columns(3)
    in_date = c1.date_input("날짜")
    in_type = c2.selectbox("구분", ["지출", "수입"])
    in_cat_mode = c3.selectbox("카테고리 선택", BASE_CATEGORIES + ["직접입력"])

    if in_cat_mode == "직접입력":
        in_category = st.text_input("카테고리(직접 입력)", value="", placeholder="예) 병원, 교육 등")
    else:
        in_category = in_cat_mode

    c4, c5 = st.columns([3, 1])
    in_desc = c4.text_input("내용", value="", placeholder="예) 점심 / 지하철 / 통신요금 ...")  # 타이핑 OK
    in_amount_text = c5.text_input("금액(원)", value="", placeholder="예) 10000")  # 타이핑 OK

    submitted = st.form_submit_button("등록")

st.markdown("</div>", unsafe_allow_html=True)

if submitted:
    if str(in_category).strip() == "":
        st.error("카테고리를 입력하세요.")
    elif str(in_desc).strip() == "":
        st.error("내용을 입력하세요.")
    else:
        amount = parse_amount(in_amount_text)
        new_tx = {
            "date": str(in_date),
            "type": in_type,
            "category": str(in_category).strip(),
            "description": str(in_desc).strip(),
            "amount": int(amount),
        }
        push_undo(transactions.copy())
        transactions.append(new_tx)
        do_save(transactions)

# -----------------------------
# (6) 필터 적용 (★ 빈 데이터/NaT면 dt 접근 안 하게 안전처리)
# -----------------------------
df = df_all.copy()

if not df.empty:
    # date가 datetime64로 보장되어 있어 .dt 안전
    start_ts = pd.to_datetime(start_date)
    end_ts = pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)
    df = df[(df["date"] >= start_ts) & (df["date"] <= end_ts)]

    if type_filter != "전체":
        df = df[df["type"] == type_filter]

    if category_filter != "전체":
        df = df[df["category"] == category_filter]

    if keyword.strip() != "":
        df = df[df["description"].fillna("").str.contains(keyword.strip(), case=False, na=False)]
else:
    # 완전 빈 데이터면 그대로 빈 df 유지(여기서 dt 쓰면 터짐)
    df = df_all.copy()

# -----------------------------
# (7) 탭
# -----------------------------
tab_data, tab_chart, tab_alert = st.tabs(["📄 데이터", "📊 차트", "🚨 관제(예산)"])

# -----------------------------
# (8) 데이터 탭: 조회 + 편집 + 삭제 + Undo
# -----------------------------
with tab_data:
    st.subheader("📌 필터 결과 데이터")

    # 버튼 4개 한 줄
    b1, b2, b3, b4 = st.columns(4)

    # 데이터 없으면 안내만 (★ 여기서도 안전)
    if df.empty:
        st.info("등록된 거래가 없습니다. (또는 필터 조건에 맞는 데이터가 없습니다.)")
    else:
        # 편집용 DF 구성
        edit_df = df.copy().reset_index(drop=True)
        edit_df.insert(0, "삭제", False)              # 체크박스 삭제용
        edit_df.insert(1, "_idx", edit_df.index)       # 내부 식별자(표시되지만 의미만)
        edit_df["date"] = edit_df["date"].dt.strftime("%Y-%m-%d")

        # 컬럼명 표시용
        show_df = edit_df.rename(
            columns={
                "date": "날짜",
                "type": "구분",
                "category": "카테고리",
                "description": "내용",
                "amount": "금액",
            }
        )

        # 편집 UI
        edited = st.data_editor(
            show_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "삭제": st.column_config.CheckboxColumn("삭제", help="체크 후 '체크된 항목 선택 삭제'"),
                "_idx": st.column_config.NumberColumn("_idx", disabled=True),
                "날짜": st.column_config.TextColumn("날짜"),
                "구분": st.column_config.SelectboxColumn("구분", options=["지출", "수입"]),
                "카테고리": st.column_config.SelectboxColumn("카테고리", options=category_pool),
                "내용": st.column_config.TextColumn("내용"),
                "금액": st.column_config.NumberColumn("금액", min_value=0, step=1000),
            },
            key="editor",
        )

        # 원본 전체 transactions(필터 전)에서 해당 row들을 찾아 편집/삭제 반영하려면
        # 여기선 단순화: 현재 "필터 결과"를 수정/삭제한 뒤, 필터 결과가 아닌 전체 데이터에 반영한다.
        # 매칭 기준: (날짜, 구분, 카테고리, 내용, 금액) 완전 일치로 찾고, 같은 값이 여러 개면 앞에서부터 처리.

        def apply_changes_to_all(all_tx: list, before_rows: pd.DataFrame, after_rows: pd.DataFrame) -> list:
            all_df = to_df(all_tx)
            # before/after는 "필터 결과" 기준이므로 date가 문자열 → datetime 변환
            before = before_rows.copy()
            after = after_rows.copy()

            # 표 컬럼명 -> 내부 컬럼명 역매핑
            rename_back = {"날짜": "date", "구분": "type", "카테고리": "category", "내용": "description", "금액": "amount"}
            before = before.rename(columns=rename_back)
            after = after.rename(columns=rename_back)

            # 삭제 체크
            to_delete = after[after["삭제"] == True].copy()

            # 편집 저장용(삭제 제외)
            to_update = after[after["삭제"] == False].copy()

            # all_df도 비교용 문자열 date 컬럼 만들기
            all_df_cmp = all_df.copy()
            all_df_cmp["date_str"] = all_df_cmp["date"].dt.strftime("%Y-%m-%d")

            def find_first_match_index(row):
                mask = (
                    (all_df_cmp["date_str"] == str(row["date"])[:10])
                    & (all_df_cmp["type"] == row["type"])
                    & (all_df_cmp["category"] == row["category"])
                    & (all_df_cmp["description"] == row["description"])
                    & (all_df_cmp["amount"] == int(row["amount"]))
                )
                idxs = all_df_cmp[mask].index.tolist()
                return idxs[0] if idxs else None

            # 1) 삭제 먼저: before 기준으로 찾는다(사용자가 편집도 했을 수 있으니 after 대신 before를 활용)
            if not to_delete.empty:
                # 삭제 대상은 "after에서 삭제 체크된 행"의 현재값으로도 잡히지만,
                # 안정적으로 before에서 같은 _idx 가진 행을 가져와 삭제
                before_map = before_rows.copy()
                before_map = before_map.rename(columns=rename_back)
                before_map["_idx"] = before_rows["_idx"].values
                del_keys = set(to_delete["_idx"].tolist())

                del_rows = before_map[before_map["_idx"].isin(del_keys)]
                for _, r in del_rows.iterrows():
                    idx = find_first_match_index(r)
                    if idx is not None:
                        all_df_cmp = all_df_cmp.drop(index=idx).reset_index(drop=True)
                        all_df = all_df.drop(index=idx).reset_index(drop=True)
                        all_df_cmp = all_df.copy()
                        all_df_cmp["date_str"] = all_df_cmp["date"].dt.strftime("%Y-%m-%d")

            # 2) 편집: before와 after를 _idx로 조인해서 바뀐 행만 찾아 업데이트
            before_base = before_rows.copy().rename(columns=rename_back)
            after_base = after_rows.copy().rename(columns=rename_back)

            before_base["_idx"] = before_rows["_idx"].values
            after_base["_idx"] = after_rows["_idx"].values

            merged = before_base.merge(after_base, on="_idx", suffixes=("_b", "_a"))
            # 변경 감지(삭제 체크된 것은 제외)
            merged = merged[merged["삭제_a"] == False]

            for _, r in merged.iterrows():
                changed = (
                    str(r["date_b"])[:10] != str(r["date_a"])[:10]
                    or r["type_b"] != r["type_a"]
                    or r["category_b"] != r["category_a"]
                    or str(r["description_b"]) != str(r["description_a"])
                    or int(r["amount_b"]) != int(r["amount_a"])
                )
                if not changed:
                    continue

                # before 값으로 원본 찾아서, after 값으로 덮어쓰기
                idx = find_first_match_index(
                    {
                        "date": r["date_b"],
                        "type": r["type_b"],
                        "category": r["category_b"],
                        "description": r["description_b"],
                        "amount": int(r["amount_b"]),
                    }
                )
                if idx is not None:
                    all_df.loc[idx, "date"] = pd.to_datetime(r["date_a"], errors="coerce")
                    all_df.loc[idx, "type"] = r["type_a"]
                    all_df.loc[idx, "category"] = r["category_a"]
                    all_df.loc[idx, "description"] = r["description_a"]
                    all_df.loc[idx, "amount"] = int(r["amount_a"])

            return df_to_transactions(all_df)

        # 버튼 동작들
        if b1.button("🧯 실행 취소(Undo)"):
            if st.session_state.undo_stack:
                restored = st.session_state.undo_stack.pop()
                do_save(restored)
            else:
                st.warning("되돌릴 기록이 없습니다.")

        if b2.button("↩️ 마지막 1건 삭제"):
            if transactions:
                push_undo(transactions.copy())
                transactions.pop()
                do_save(transactions)
            else:
                st.warning("삭제할 데이터가 없습니다.")

        if b3.button("🗑️ 체크된 항목 선택 삭제"):
            # 편집표에서 체크된 것 삭제
            before_rows = show_df.copy()
            after_rows = edited.copy()
            if "삭제" in after_rows.columns and after_rows["삭제"].any():
                push_undo(transactions.copy())
                new_all = apply_changes_to_all(transactions, before_rows, after_rows)
                do_save(new_all)
            else:
                st.warning("삭제할 항목을 체크하세요.")

        if b4.button("💾 수정사항 저장(편집 저장)"):
            before_rows = show_df.copy()
            after_rows = edited.copy()
            push_undo(transactions.copy())
            new_all = apply_changes_to_all(transactions, before_rows, after_rows)
            do_save(new_all)

# -----------------------------
# (9) 차트 탭: 요약 + 카테고리별 지출(Plotly)
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
    st.subheader("📊 카테고리별 지출 통계")

    cat_map = calc_category_expense(filtered_transactions)

    if not cat_map:
        st.info("지출 데이터가 없어서 그래프를 표시할 수 없습니다.")
    else:
        cat_df = pd.DataFrame([{"카테고리": k, "금액(원)": v} for k, v in cat_map.items()])
        cat_df = cat_df.sort_values("금액(원)", ascending=False)

        fig = px.bar(cat_df, x="카테고리", y="금액(원)", title="카테고리별 지출 통계")
        # y축 5k 같은 축약 대신 5000/10000 형태로 보이게: tickformat="," + SI 비활성
        fig.update_yaxes(title="금액(원)", tickformat=",", separatethousands=True)
        fig.update_xaxes(title="카테고리", tickangle=0)
        fig.update_layout(
            template="plotly_dark",
            title_x=0.5,
            font=dict(size=14),
            margin=dict(l=40, r=20, t=60, b=40),
        )
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

    _, exp_sum, _ = calc_summary(filtered_transactions)
    st.write(f"현재 지출 합계: **{exp_sum:,} 원**")

    if budget > 0:
        ratio = exp_sum / budget
        st.progress(min(ratio, 1.0))
        if ratio >= 1.0:
            st.error("❌ 예산을 초과했습니다!")
        elif ratio >= 0.8:
            st.warning("⚠️ 예산의 80%를 사용했습니다!")
        else:
            st.success("✅ 예산 사용이 안정적입니다.")
    else:
        st.info("예산을 입력하면 경고/진행률이 표시됩니다.")

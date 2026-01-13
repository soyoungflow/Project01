# app.py  # ✅ 최종본 W (U 기반 + desc→description 전면 교체 + 단일 컬러 디자인 통일)

import os  # 폴더/파일 경로 처리
import json  # 예산 저장/불러오기
from datetime import date  # 날짜 기본값

import pandas as pd  # CSV 읽기/쓰기 + 집계
import streamlit as st  # UI


# =============================================================================
# (0) 기본 설정
# =============================================================================
st.set_page_config(
    page_title="나만의 미니 가계부 (지출 관리 서비스)",
    layout="wide",
)

DATA_DIR = "data"
LEDGER_PATH = os.path.join(DATA_DIR, "ledger.csv")
BUDGET_PATH = os.path.join(DATA_DIR, "budgets.json")

CATEGORIES = ["식비", "교통", "통신", "생활", "기타"]
TX_TYPES = ["지출", "수입"]

# ✅ (1) desc → description 전면 교체 (컬럼/변수/세션키/위젯키 모두)
COLUMNS = ["_idx", "date", "type", "category", "description", "amount"]


# =============================================================================
# (1) 다크 테마 + 입력 박스 단일 컬러 디자인 통일 (구분/카테고리 기준)
# =============================================================================
st.markdown(
    """
<style>
/* 전체 배경: 다크 + 보라 톤 */
.stApp {
  background: radial-gradient(1200px 600px at 50% 0%, rgba(120,80,255,0.25), rgba(0,0,0,0) 55%),
              radial-gradient(900px 450px at 50% 15%, rgba(120,80,255,0.18), rgba(0,0,0,0) 60%),
              linear-gradient(180deg, #070A12 0%, #070A12 100%);
  color: #EAEAF0;
}

/* 기본 텍스트 */
h1,h2,h3,h4,h5,h6,p,span,label,div { color: #EAEAF0; }

/* 섹션 헤더(보라 박스) */
.section-header {
  width: 100%;
  padding: 18px 22px;
  border-radius: 999px;
  background: linear-gradient(90deg, rgba(130,90,255,0.40), rgba(130,90,255,0.18));
  border: 1px solid rgba(130,90,255,0.35);
  box-shadow: 0 12px 40px rgba(0,0,0,0.35);
  display: flex;
  align-items: center;
  gap: 12px;
}
.section-header .title {
  font-size: 40px;
  font-weight: 800;
  letter-spacing: -0.5px;
}
.section-header .subtitle {
  opacity: 0.85;
  font-size: 14px;
  margin-top: 2px;
}

/* ✅ 모든 입력 박스 공통 스타일: 구분/카테고리 박스 톤과 완전 동일 */
div[data-baseweb="input"],
div[data-baseweb="select"],
div[data-baseweb="textarea"],
div[data-baseweb="datepicker"],
div[data-baseweb="spinbutton"] {
    background-color: #3a3d46 !important;
    border-radius: 999px !important;
    border: 1px solid #5a5f6a !important;
    box-shadow: inset 0 0 0 1px rgba(255,255,255,0.02) !important;
}

/* 내부 텍스트 */
div[data-baseweb="input"] input,
div[data-baseweb="textarea"] textarea {
    color: #ffffff !important;
    background-color: transparent !important;
}

/* placeholder */
div[data-baseweb="input"] input::placeholder,
div[data-baseweb="textarea"] textarea::placeholder {
    color: rgba(255,255,255,0.45) !important;
}

/* select 내부 글자 */
div[data-baseweb="select"] * {
    color: #ffffff !important;
}

/* 포커스 시 */
div[data-baseweb]:focus-within {
    box-shadow: 0 0 0 2px rgba(130,90,255,0.35) !important;
    border-color: #825AFF !important;
}

/* 버튼 */
.stButton > button {
  background: linear-gradient(90deg, rgba(130,90,255,0.85), rgba(130,90,255,0.55));
  border: 1px solid rgba(130,90,255,0.40);
  color: #FFFFFF;
  border-radius: 999px;
  padding: 10px 18px;
  font-weight: 700;
}
.stButton > button:hover { filter: brightness(1.05); }

/* 데이터프레임 */
div[data-testid="stDataFrame"] {
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 18px;
  overflow: hidden;
}

/* 사이드바도 너무 어둡지 않게 */
section[data-testid="stSidebar"] {
  background: rgba(255,255,255,0.04);
  border-right: 1px solid rgba(255,255,255,0.06);
}
</style>
""",
    unsafe_allow_html=True,
)


# =============================================================================
# (2) 파일/데이터 유틸
# =============================================================================
def ensure_dir() -> None:
    """data 폴더 없으면 생성"""
    os.makedirs(DATA_DIR, exist_ok=True)


def load_ledger() -> pd.DataFrame:
    """
    거래내역 CSV 로드.
    - 과거 데이터에 desc 컬럼이 있으면 description으로 자동 변환(호환성)
    - description은 항상 저장/로딩되므로 재실행해도 '내용'이 안 사라짐
    """
    ensure_dir()

    if not os.path.exists(LEDGER_PATH):
        return pd.DataFrame(columns=COLUMNS)

    df = pd.read_csv(LEDGER_PATH)

    # ✅ 과거 호환: desc → description
    if "desc" in df.columns and "description" not in df.columns:
        df = df.rename(columns={"desc": "description"})

    # 필수 컬럼 보정
    for col in COLUMNS:
        if col not in df.columns:
            df[col] = "" if col in ["date", "type", "category", "description"] else 0

    df["_idx"] = pd.to_numeric(df["_idx"], errors="coerce").fillna(0).astype(int)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0).astype(int)
    df["description"] = df["description"].fillna("").astype(str)

    return df[COLUMNS].copy()


def save_ledger(df: pd.DataFrame) -> None:
    """거래내역 저장 (description 포함)"""
    ensure_dir()

    df = df.copy()
    if "desc" in df.columns:
        df = df.rename(columns={"desc": "description"})

    for col in COLUMNS:
        if col not in df.columns:
            df[col] = "" if col in ["date", "type", "category", "description"] else 0

    df["_idx"] = pd.to_numeric(df["_idx"], errors="coerce").fillna(0).astype(int)
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0).astype(int)
    df["description"] = df["description"].fillna("").astype(str)

    df = df[COLUMNS].copy()
    df.to_csv(LEDGER_PATH, index=False)


def load_budgets() -> dict:
    """
    예산 로드:
    - {"전체": 0, "식비":0, ...}
    """
    ensure_dir()
    default_b = {"전체": 0, **{c: 0 for c in CATEGORIES}}

    if not os.path.exists(BUDGET_PATH):
        return default_b

    try:
        with open(BUDGET_PATH, "r", encoding="utf-8") as f:
            b = json.load(f)
    except Exception:
        b = default_b

    for k in default_b:
        if k not in b:
            b[k] = 0

    for k in b:
        try:
            b[k] = int(b[k])
        except Exception:
            b[k] = 0

    return b


def save_budgets(b: dict) -> None:
    """예산 저장"""
    ensure_dir()
    with open(BUDGET_PATH, "w", encoding="utf-8") as f:
        json.dump(b, f, ensure_ascii=False, indent=2)


def to_dt(s: pd.Series) -> pd.Series:
    """문자열 date 컬럼을 datetime으로 변환 (필터/월관제용)"""
    return pd.to_datetime(s, errors="coerce")


def this_month_range(today_: date) -> tuple[date, date]:
    """이번 달 1일~말일"""
    first = today_.replace(day=1)
    if first.month == 12:
        next_first = first.replace(year=first.year + 1, month=1, day=1)
    else:
        next_first = first.replace(month=first.month + 1, day=1)
    last = (pd.to_datetime(next_first) - pd.Timedelta(days=1)).date()
    return first, last


# =============================================================================
# (3) 세션 상태 초기화
# =============================================================================
if "df" not in st.session_state:
    st.session_state.df = load_ledger()

if "history" not in st.session_state:
    st.session_state.history = []

if "budgets" not in st.session_state:
    st.session_state.budgets = load_budgets()


def push_history() -> None:
    """Undo용: 현재 df 복사본을 history에 저장"""
    st.session_state.history.append(st.session_state.df.copy())


def undo_last() -> None:
    """Undo: 마지막 상태로 되돌림"""
    if st.session_state.history:
        st.session_state.df = st.session_state.history.pop()
        save_ledger(st.session_state.df)


# =============================================================================
# (4) 상단 타이틀
# =============================================================================
st.markdown(
    """
<div class="section-header">
  <div style="font-size:46px;">🧾</div>
  <div>
    <div class="title">나만의 미니 가계부 (지출 관리 서비스)</div>
    <div class="subtitle">입력 → 저장 → 즉시 반영되는 MVP 가계부</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)
st.write("")


# =============================================================================
# (5) 사이드바 필터
# =============================================================================
with st.sidebar:
    st.markdown("### 🔎 필터")

    today = date.today()
    date_range = st.date_input(
        "기간 선택",
        value=(today, today),
        key="filter_date_range",
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date, end_date = today, today

    keyword = st.text_input("검색어(내용 포함)", value="", key="filter_keyword")

    type_filter = st.selectbox("구분", ["전체"] + TX_TYPES, index=0, key="filter_type")
    category_filter = st.selectbox("카테고리", ["전체"] + CATEGORIES, index=0, key="filter_category")


def get_filtered_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    사이드바 필터를 df에 적용한 결과 반환
    - 날짜/구분/카테고리/검색어(내용 포함)
    """
    tmp = df.copy()

    tmp["_dt"] = to_dt(tmp["date"])
    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)

    tmp = tmp[(tmp["_dt"].notna()) & (tmp["_dt"] >= start_dt) & (tmp["_dt"] <= end_dt)]

    if type_filter != "전체":
        tmp = tmp[tmp["type"] == type_filter]

    if category_filter != "전체":
        tmp = tmp[tmp["category"] == category_filter]

    if keyword.strip():
        k = keyword.strip()
        # ✅ desc 금지, description만
        tmp = tmp[tmp["description"].fillna("").astype(str).str.contains(k, case=False, na=False)]

    return tmp.drop(columns=["_dt"], errors="ignore")


# =============================================================================
# (6) 새 거래 등록 (보라 박스 안에 타이틀이 들어가게)
# =============================================================================
st.markdown(
    """
<div class="section-header" style="margin-top:14px;">
  <div style="font-size:34px;">➕</div>
  <div class="title" style="font-size:36px;">새 거래 등록</div>
  <div style="margin-left:10px; opacity:0.85; font-weight:700;">(즉시 저장)</div>
</div>
""",
    unsafe_allow_html=True,
)
st.write("")

c1, c2, c3 = st.columns([2.2, 1.6, 1.6])
with c1:
    tx_date = st.date_input("날짜", value=today, key="input_date")
with c2:
    tx_type = st.selectbox("구분", TX_TYPES, index=0, key="input_type")
with c3:
    tx_category = st.selectbox("카테고리", CATEGORIES, index=0, key="input_category")

# ✅ (1) desc → description: 변수명/위젯키/세션키 모두 description으로 통일
description = st.text_input(
    "내용",
    value="",
    key="input_description",  # 입력 위젯 키도 desc 금지
    placeholder="예) 지하철 / 점심 / 통신요금 ...",
)
amount = st.number_input("금액(원)", min_value=0, step=1000, value=0, key="input_amount")

if st.button("등록", key="btn_add"):
    push_history()

    df = st.session_state.df.copy()
    next_idx = (df["_idx"].max() + 1) if len(df) else 0

    # ✅ new_row도 desc 금지: description만 사용
    new_row = {
        "_idx": int(next_idx),
        "date": tx_date.strftime("%Y-%m-%d"),
        "type": tx_type,
        "category": tx_category,
        "description": str(description).strip(),
        "amount": int(amount),
    }

    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    st.session_state.df = df
    save_ledger(df)

    # 입력값 리셋 (다음 입력 편하게)
    st.session_state.input_description = ""
    st.session_state.input_amount = 0

    st.success("저장 완료! (CSV에 바로 반영됨)")


# =============================================================================
# (7) 탭: 데이터 / 차트 / 관제(예산)
# =============================================================================
tab_data, tab_chart, tab_budget = st.tabs(["📄 데이터", "📊 차트", "🚨 관제(예산)"])


# =============================================================================
# (8) 데이터 탭
# =============================================================================
with tab_data:
    st.markdown("## 📌 필터 결과 데이터")

    b1, b2, b3, b4 = st.columns(4)

    with b1:
        if st.button("🧯 실행 취소(Undo)", use_container_width=True):
            undo_last()

    with b2:
        if st.button("↩️ 마지막 1건 삭제", use_container_width=True):
            if len(st.session_state.df) == 0:
                st.info("삭제할 데이터가 없습니다.")
            else:
                push_history()
                st.session_state.df = st.session_state.df.iloc[:-1].copy()
                save_ledger(st.session_state.df)
                st.success("마지막 1건 삭제 완료")

    with b3:
        if st.button("🗑️ 체크된 항목 선택 삭제", use_container_width=True):
            st.session_state._do_delete_checked = True

    with b4:
        if st.button("💾 수정사항 저장(편집 저장)", use_container_width=True):
            st.session_state._do_save_edits = True

    df_all = st.session_state.df.copy()
    df_filtered = get_filtered_df(df_all)

    if df_filtered.empty:
        st.info("필터 조건에 해당하는 데이터가 없습니다.")
    else:
        show = df_filtered.copy()
        show = show.rename(columns={"_idx": "번호"})
        show.insert(0, "삭제", False)

        show = show[["삭제", "번호", "date", "type", "category", "description", "amount"]].copy()
        show = show.rename(
            columns={
                "date": "날짜",
                "type": "구분",
                "category": "카테고리",
                "description": "내용",
                "amount": "금액",
            }
        )

        edited = st.data_editor(show, use_container_width=True, hide_index=True, key="data_editor")

        # 체크 삭제
        if st.session_state.get("_do_delete_checked"):
            st.session_state._do_delete_checked = False

            checked = edited[edited["삭제"] == True]
            if checked.empty:
                st.info("체크된 항목이 없습니다.")
            else:
                push_history()
                ids = checked["번호"].tolist()
                new_all = df_all[~df_all["_idx"].isin(ids)].copy()
                st.session_state.df = new_all
                save_ledger(new_all)
                st.success(f"{len(ids)}건 삭제 완료")

        # 편집 저장
        if st.session_state.get("_do_save_edits"):
            st.session_state._do_save_edits = False

            push_history()

            core = edited.copy()
            core = core.rename(
                columns={
                    "번호": "_idx",
                    "날짜": "date",
                    "구분": "type",
                    "카테고리": "category",
                    "내용": "description",  # ✅ 저장 시도 desc 금지
                    "금액": "amount",
                }
            )
            core = core.drop(columns=["삭제"], errors="ignore")

            core["_idx"] = pd.to_numeric(core["_idx"], errors="coerce").fillna(-1).astype(int)
            core["amount"] = pd.to_numeric(core["amount"], errors="coerce").fillna(0).astype(int)
            core["description"] = core["description"].fillna("").astype(str)

            new_all = df_all.copy()
            for _, r in core.iterrows():
                rid = int(r["_idx"])
                mask = new_all["_idx"] == rid
                if mask.any():
                    new_all.loc[mask, ["date", "type", "category", "description", "amount"]] = [
                        str(r["date"]),
                        str(r["type"]),
                        str(r["category"]),
                        str(r["description"]),
                        int(r["amount"]),
                    ]

            st.session_state.df = new_all
            save_ledger(new_all)
            st.success("편집 내용 저장 완료")

        # 검색어 인사이트 (표 밑)
        if keyword.strip():
            k = keyword.strip()
            # 현재 필터 기준(기간/구분/카테고리/검색어 포함) 거래 수 + 합산금액
            base = df_filtered.copy()
            count = len(base)
            total_amt = int(base["amount"].sum()) if count else 0
            st.markdown("🧠 **검색어 인사이트(간단)**")
            st.write(f'검색어 "{k}" 포함 거래: **{count}건 / {total_amt:,}원**')


# =============================================================================
# (9) 차트 탭
# =============================================================================
with tab_chart:
    st.markdown("## 📊 카테고리별 지출 통계")

    df_all = st.session_state.df.copy()
    df_filtered = get_filtered_df(df_all)

    exp = df_filtered[df_filtered["type"] == "지출"].copy()

    if exp.empty:
        st.info("지출 데이터가 없어서 차트를 그릴 수 없습니다.")
    else:
        agg = exp.groupby("category", as_index=False)["amount"].sum()
        agg["category"] = pd.Categorical(agg["category"], categories=CATEGORIES, ordered=True)
        agg = agg.sort_values("category")

        import plotly.express as px

        fig = px.bar(
            agg,
            x="category",
            y="amount",
            text="amount",
            color="category",
            title="카테고리별 지출 통계",
        )

        # 축/숫자/글자 안 보이는 문제 방지(다크)
        fig.update_layout(
            template="plotly_dark",
            margin=dict(l=40, r=20, t=60, b=50),
            font=dict(color="#FFFFFF", size=14),
            xaxis_title="카테고리",
            yaxis_title="금액(원)",
            legend_title_text="카테고리",
        )
        fig.update_xaxes(showgrid=False, tickfont=dict(color="#FFFFFF"))
        fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.08)", tickfont=dict(color="#FFFFFF"))
        fig.update_traces(texttemplate="%{text:,}", textposition="outside", cliponaxis=False)

        st.plotly_chart(fig, use_container_width=True)

        # 인사이트(간단): TOP1 + 퍼센티지
        total = agg["amount"].sum()
        top = agg.sort_values("amount", ascending=False).iloc[0]
        top_cat = str(top["category"])
        top_amt = int(top["amount"])
        pct = (top_amt / total * 100) if total else 0

        st.markdown("🧠 **인사이트(간단)**")
        st.write(f"이번 기간 지출 TOP: **{top_cat}({pct:.0f}%)**")


# =============================================================================
# (10) 관제(예산) 탭
# =============================================================================
with tab_budget:
    st.markdown("## 🚨 관제(예산)")

    first_day, last_day = this_month_range(date.today())
    st.caption(f"이번 달 기준: {first_day.strftime('%Y-%m-%d')} ~ {last_day.strftime('%Y-%m-%d')}")

    df_all = st.session_state.df.copy()
    df_all["_dt"] = to_dt(df_all["date"])

    month_exp = df_all[
        (df_all["_dt"].notna())
        & (df_all["_dt"] >= pd.to_datetime(first_day))
        & (df_all["_dt"] <= pd.to_datetime(last_day))
        & (df_all["type"] == "지출")
    ].copy()

    spend_by_cat = month_exp.groupby("category")["amount"].sum().to_dict()
    total_spend = int(month_exp["amount"].sum()) if not month_exp.empty else 0

    st.markdown("### 📌 카테고리별 예산 설정(원)")

    # ✅ 전체 + 카테고리 예산 입력 (박스 디자인은 위 CSS로 단일 컬러 통일됨)
    budget_keys = ["전체"] + CATEGORIES
    cols = st.columns(len(budget_keys))

    # 예산 상태 복사본(화면에서 수정 후 저장 버튼으로 반영)
    new_b = dict(st.session_state.budgets)

    for i, k in enumerate(budget_keys):
        with cols[i]:
            new_b[k] = st.number_input(
                k,
                min_value=0,
                step=10000,
                value=int(st.session_state.budgets.get(k, 0)),
                key=f"budget_{k}",
            )

    if st.button("💾 예산 저장", key="btn_save_budget"):
        st.session_state.budgets = new_b
        save_budgets(new_b)
        st.success("예산 저장 완료")

    budgets = new_b

    st.write("---")
    st.markdown("### ✅ 이번 달 전체 관제")

    # 전체 예산 계산:
    # - 사용자가 "전체"에 입력한 값이 있으면 그걸 우선 사용
    # - 없으면(0이면) 카테고리 예산 합계를 전체 예산으로 사용
    overall_budget = int(budgets.get("전체", 0))
    if overall_budget <= 0:
        overall_budget = sum(int(budgets.get(c, 0)) for c in CATEGORIES)

    overall_ratio = (total_spend / overall_budget) if overall_budget > 0 else 0.0

    st.progress(min(overall_ratio, 1.0))
    st.write(f"총 지출: **{total_spend:,}원** / 총 예산: **{overall_budget:,}원**")

    # ✅ 요구사항: "⚠️ 예산의 80%를 사용했습니다!" 다시 뜨게
    if overall_budget > 0 and 0.8 <= overall_ratio < 1.0:
        st.warning("⚠️ 예산의 80%를 사용했습니다!")
    elif overall_budget > 0 and overall_ratio >= 1.0:
        st.error("🚨 예산을 초과했습니다!")
    else:
        st.success("👍 예산 범위 내에서 관리 중입니다.")

    st.write("")
    st.markdown("### 📊 카테고리별 관제")

    for c in CATEGORIES:
        c_budget = int(budgets.get(c, 0))
        c_spend = int(spend_by_cat.get(c, 0))
        ratio = (c_spend / c_budget) if c_budget > 0 else 0.0

        st.write(f"**{c}** | 지출 {c_spend:,}원 / 예산 {c_budget:,}원")
        st.progress(min(ratio, 1.0))

        if c_budget > 0 and 0.8 <= ratio < 1.0:
            st.warning(f"⚠️ {c} 예산의 80%를 사용했습니다!")
        elif c_budget > 0 and ratio >= 1.0:
            st.error(f"🚨 {c} 예산을 초과했습니다!")

        st.write("")


# =============================================================================
# ✅ 최종본 W 상태 체크 (코드로 보장되는 것들)
# - desc 완전 제거: 컬럼/변수/키 전부 description
# - CSV 저장/로드에도 description만 사용 => 재실행해도 '내용' 안 사라짐
# - 날짜/내용/금액/예산 박스 포함 모든 입력 UI가 "구분/카테고리"와 동일한 단일 컬러 디자인
# =============================================================================

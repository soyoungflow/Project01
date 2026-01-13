# app.py  # Streamlit UI 담당 (입력/표/요약/그래프/필터)  # ← UI 파일(로직은 services/repository가 담당)

import os  # 파일 경로 처리(저장 경로 만들 때 사용)
import pandas as pd  # 표/필터/가공용
import streamlit as st  # UI 프레임워크
import plotly.express as px  # ✅ 차트(웹 폰트로 한글/축 라벨 안정적으로 표시)

# 팀원이 만든 로직 모듈 import  # ← "UI는 호출만 한다" 원칙
from ledger.repository import load_transactions, save_transactions  # CSV I/O
from ledger.services import calc_summary, calc_category_expense  # 통계 계산


# -----------------------------
# (0) 기본 설정
# -----------------------------
st.set_page_config(page_title="나만의 미니 가계부", layout="wide")  # 앱 기본 레이아웃(가로 넓게)

DATA_PATH = os.path.join("data", "ledger.csv")  # 저장 파일 위치(팀 폴더 구조 기준)


# -----------------------------
# (0-1) ✅ 고급 보라 테마 CSS (UI만 꾸미는 부분 / 기능엔 영향 없음)
# -----------------------------
st.markdown(
    """
<style>
/* 전체 톤 */
:root{
  --p1:#8b5cf6;   /* violet */
  --p2:#a78bfa;   /* light violet */
  --p3:#6d28d9;   /* deep violet */
  --g1:#22c55e;   /* green accent */
  --bg1: rgba(139,92,246,0.12);
  --bd1: rgba(139,92,246,0.35);
}

/* 보라 그라데이션 배너 */
.purple-banner{
  border: 1px solid var(--bd1);
  background: linear-gradient(90deg, rgba(109,40,217,0.25), rgba(139,92,246,0.10));
  border-radius: 18px;
  padding: 14px 18px;
  margin: 10px 0 14px 0;
  box-shadow: 0 10px 30px rgba(0,0,0,0.25);
  display:flex;
  align-items:center;
  justify-content:space-between;
}
.purple-banner .left{
  display:flex;
  gap:10px;
  align-items:center;
}
.purple-badge{
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(34,197,94,0.18);
  border: 1px solid rgba(34,197,94,0.35);
  color: rgba(195,255,215,0.95);
  font-size: 12px;
  font-weight: 700;
}
.purple-title{
  font-size: 18px;
  font-weight: 800;
}

/* 버튼 통일 */
.stButton > button{
  border-radius: 14px !important;
  border: 1px solid rgba(167,139,250,0.45) !important;
  background: linear-gradient(180deg, rgba(139,92,246,0.95), rgba(109,40,217,0.95)) !important;
  color: white !important;
  font-weight: 800 !important;
  padding: 10px 14px !important;
}
.stButton > button:hover{
  filter: brightness(1.08);
  transform: translateY(-1px);
}

/* 탭 밑줄 포인트 */
button[role="tab"][aria-selected="true"]{
  border-bottom: 3px solid var(--p1) !important;
}

/* 섹션 카드 느낌 */
.section-card{
  border: 1px solid rgba(255,255,255,0.10);
  background: rgba(255,255,255,0.03);
  border-radius: 18px;
  padding: 18px;
  margin: 8px 0 18px 0;
}
</style>
""",
    unsafe_allow_html=True,
)


# -----------------------------
# (1) 유틸: 리스트(dict) -> DataFrame
# -----------------------------
def to_df(transactions: list) -> pd.DataFrame:
    """transactions(list[dict])를 DataFrame으로 안전 변환 (빈 데이터/타입 꼬임 방어)"""
    if not transactions:
        # ✅ 컬럼 고정: 빈 상태에서도 화면/필터/차트가 안 터지게 한다
        return pd.DataFrame(columns=["date", "type", "category", "description", "amount"])

    df = pd.DataFrame(transactions)

    # ✅ amount는 숫자여야 함(문자열 섞이면 계산/차트 깨짐)
    df["amount"] = pd.to_numeric(df.get("amount", 0), errors="coerce").fillna(0).astype(int)

    # ✅ date는 반드시 datetime (안 그러면 .dt에서 AttributeError 터짐)
    df["date"] = pd.to_datetime(df.get("date", None), errors="coerce")

    # ✅ 누락 컬럼 방어(혹시 저장된 CSV가 예전 포맷이어도 앱이 죽지 않게)
    for col in ["type", "category", "description"]:
        if col not in df.columns:
            df[col] = ""

    return df


def push_history(before_transactions: list):
    """Undo를 위해 이전 상태를 스택에 저장"""
    if "history" not in st.session_state:
        st.session_state["history"] = []
    # ✅ 깊은 복사(리스트 안 dict까지 복사) - 안 하면 Undo가 같이 바뀜
    snapshot = [dict(x) for x in before_transactions]
    st.session_state["history"].append(snapshot)


def safe_date_range(df_all: pd.DataFrame):
    """date_input 기본값을 안전하게 만든다(빈 DF/전부 NaT면 오늘)"""
    if df_all.empty or df_all["date"].isna().all():
        today = pd.Timestamp.today().date()
        return today, today
    return df_all["date"].min().date(), df_all["date"].max().date()


# -----------------------------
# (2) 앱 시작: 데이터 로드 (재실행해도 데이터 유지)
# -----------------------------
transactions = load_transactions(DATA_PATH)  # CSV 있으면 읽고, 없으면 빈 리스트
df_all = to_df(transactions)  # 전체 DF (필터/차트/표의 기반)

# ✅ 내부 식별자(_idx) 부여: 편집/삭제/선택삭제할 때 "원본 리스트의 몇 번째인지" 추적용
# (유저에게는 '번호'로 보여주고, 내부는 _idx로 사용)
if not df_all.empty:
    df_all = df_all.reset_index(drop=True)
    df_all["_idx"] = df_all.index.astype(int)
else:
    df_all["_idx"] = pd.Series(dtype=int)


# -----------------------------
# (3) 타이틀 영역
# -----------------------------
st.title("🧾 나만의 미니 가계부 (지출 관리 서비스)")  # 큰 제목
st.caption("입력 → 저장 → 즉시 반영되는 MVP 가계부")  # 작은 설명


# -----------------------------
# (4) 사이드바: 필터(필터만 남김)
# -----------------------------
st.sidebar.header("🔎 필터")

min_date, max_date = safe_date_range(df_all)

# ✅ 기간 선택: 선택 기간 데이터만 표시(아래 필터 적용에서 그대로 사용)
start_date, end_date = st.sidebar.date_input("기간 선택", value=(min_date, max_date))

# ✅ 검색어(바로 타이핑)
keyword = st.sidebar.text_input("검색어(내용 포함)", value="")

# ✅ 구분/카테고리 (드롭다운)
type_filter = st.sidebar.selectbox("구분", ["전체", "지출", "수입"])

# ✅ 카테고리 기본 리스트(요구: 식비/교통/통신/생활/기타) + 기존 데이터에 새 카테고리 있으면 자동 합류
BASE_CATEGORIES = ["식비", "교통", "통신", "생활", "기타"]
category_pool = set(BASE_CATEGORIES)
if not df_all.empty:
    category_pool |= set(df_all["category"].dropna().astype(str).tolist())

category_options = ["전체"] + sorted([c for c in category_pool if c.strip() != ""])
category_filter = st.sidebar.selectbox("카테고리", category_options)


# -----------------------------
# (5) ✅ 메인: 새 거래 등록 (제목/캡션 아래, 탭 위)
# -----------------------------
st.markdown(
    """
<div class="purple-banner">
  <div class="left">
    <div class="purple-title">➕ 새 거래 등록</div>
    <div class="purple-badge">즉시 저장</div>
  </div>
</div>
""",
    unsafe_allow_html=True,
)

with st.container():
    st.markdown('<div class="section-card">', unsafe_allow_html=True)

    # ✅ 메인 폼: 구분/카테고리 드롭다운 + 내용/금액은 타이핑
    with st.form("add_tx_form_main", clear_on_submit=True):
        c1, c2, c3 = st.columns([1.2, 1.2, 1.6])

        with c1:
            in_date = st.date_input("날짜", value=pd.Timestamp.today().date())  # 날짜 선택
        with c2:
            in_type = st.selectbox("구분", ["지출", "수입"])  # 드롭다운
        with c3:
            # ✅ 카테고리 드롭다운(요구 카테고리 기본 제공)
            in_category = st.selectbox("카테고리", BASE_CATEGORIES, index=0)

        c4, c5 = st.columns([3, 1])
        with c4:
            # ✅ 내용은 바로 타이핑
            in_desc = st.text_input("내용", value="", placeholder="예) 지하철 / 점심 / 통신요금 ...")
        with c5:
            # ✅ 금액도 바로 타이핑 가능(text_input) + 숫자만 추출해서 저장
            in_amount_text = st.text_input("금액(원)", value="0", placeholder="예) 12000")

        submitted = st.form_submit_button("등록")

    st.markdown("</div>", unsafe_allow_html=True)

# ✅ 등록 처리(저장 + 즉시 반영)
if submitted:
    # (1) 내용/카테고리 기본 검증
    if str(in_desc).strip() == "":
        st.error("내용을 입력하세요.")
    else:
        # (2) 금액 파싱: "12,000" 같은 입력도 허용
        cleaned = "".join([ch for ch in str(in_amount_text) if ch.isdigit()])
        in_amount = int(cleaned) if cleaned != "" else 0

        new_tx = {
            "date": str(in_date),  # CSV 저장용(YYYY-MM-DD)
            "type": in_type,
            "category": str(in_category).strip(),
            "description": str(in_desc).strip(),
            "amount": int(in_amount),
        }

        # ✅ Undo 대비: 저장 전 상태를 history에 쌓음
        push_history(transactions)

        transactions.append(new_tx)
        save_transactions(DATA_PATH, transactions)

        st.success(
            f"등록 완료 ✅ {new_tx['date']} / {new_tx['type']} / {new_tx['category']} / {new_tx['amount']:,}원"
        )
        st.rerun()


# -----------------------------
# (6) 필터 적용 (선택 기간 데이터만 표시)
# -----------------------------
df = df_all.copy()

# ✅ 빈 데이터면 여기서 더 진행하지 않아도 앱이 안 터지게 방어
if not df.empty:
    # date가 datetime일 때만 .dt 사용 (혹시라도 꼬이면 to_datetime 다시 시도)
    if not pd.api.types.is_datetime64_any_dtype(df["date"]):
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # ✅ 기간 필터(핵심)
    df = df[df["date"].notna()]  # NaT 제거(비교 에러 방지)
    df = df[(df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)]

    # ✅ 구분 필터
    if type_filter != "전체":
        df = df[df["type"] == type_filter]

    # ✅ 카테고리 필터
    if category_filter != "전체":
        df = df[df["category"] == category_filter]

    # ✅ 검색 필터(내용 포함)
    if keyword.strip() != "":
        df = df[df["description"].fillna("").str.lower().str.contains(keyword.strip().lower())]


# -----------------------------
# (7) 메인: 탭 구성
# -----------------------------
tab_data, tab_chart, tab_alert = st.tabs(["📄 데이터", "📊 차트", "🚨 관제(예산)"])


# -----------------------------
# (8) 데이터 탭: 표 + 편집/삭제/Undo
# -----------------------------
with tab_data:
    st.subheader("📌 필터 결과 데이터")

    # ✅ 버튼 4개를 "가로 1줄"로 배치
    b1, b2, b3, b4 = st.columns(4)

    # (A) 실행 취소(Undo)
    with b1:
        if st.button("🧯 실행 취소(Undo)"):
            hist = st.session_state.get("history", [])
            if hist:
                prev = hist.pop()  # 마지막 상태로 복귀
                save_transactions(DATA_PATH, prev)
                st.success("Undo 완료 ✅ (이전 상태로 되돌림)")
                st.rerun()
            else:
                st.info("되돌릴 기록이 없습니다.")

    # (B) 마지막 1건 삭제
    with b2:
        if st.button("↩️ 마지막 1건 삭제"):
            if len(transactions) > 0:
                push_history(transactions)
                transactions.pop()
                save_transactions(DATA_PATH, transactions)
                st.success("마지막 1건 삭제 완료 ✅")
                st.rerun()
            else:
                st.info("삭제할 데이터가 없습니다.")

    # (C) 체크된 항목 선택 삭제
    delete_selected_clicked = False
    with b3:
        delete_selected_clicked = st.button("🗑️ 체크된 항목 선택 삭제")

    # (D) 수정사항 저장(편집 저장)
    save_edits_clicked = False
    with b4:
        save_edits_clicked = st.button("💾 수정사항 저장(편집 저장)")

    if df.empty:
        st.info("등록된 거래가 없습니다. (또는 필터 조건에 맞는 데이터가 없습니다.)")
    else:
        # ✅ 보여줄 DF 구성
        view_df = df.copy()
        view_df["date"] = view_df["date"].dt.strftime("%Y-%m-%d")  # 보기용 문자열

        # ✅ 유저가 체크하는 삭제 컬럼 추가
        view_df.insert(0, "delete", False)

        # ✅ 컬럼 순서/이름(유저 친화적으로)
        # - _idx는 내부 식별자지만 유저에겐 "번호"로 보여준다 (요구: _idx 말고 한국어)
        view_df = view_df[["delete", "_idx", "date", "type", "category", "description", "amount"]]
        view_df.columns = ["삭제", "번호", "날짜", "구분", "카테고리", "내용", "금액"]

        # ✅ 편집 가능한 표(내용/금액/카테고리/구분 수정 가능)
        edited = st.data_editor(
            view_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "삭제": st.column_config.CheckboxColumn("삭제", help="체크 후 '체크된 항목 선택 삭제' 버튼을 누르세요."),
                "번호": st.column_config.NumberColumn("번호", disabled=True),
                "날짜": st.column_config.TextColumn("날짜", help="YYYY-MM-DD 형태"),
                "구분": st.column_config.SelectboxColumn("구분", options=["지출", "수입"]),
                "카테고리": st.column_config.SelectboxColumn("카테고리", options=BASE_CATEGORIES),
                "내용": st.column_config.TextColumn("내용"),
                "금액": st.column_config.NumberColumn("금액", min_value=0, step=1000),
            },
            key="data_editor",
        )

        # ✅ 체크 삭제 실행
        if delete_selected_clicked:
            to_delete = edited[edited["삭제"] == True]["번호"].tolist()
            if len(to_delete) == 0:
                st.info("체크된 항목이 없습니다.")
            else:
                push_history(transactions)
                # 번호(=원본 인덱스)를 기준으로 삭제
                keep = []
                for i, tx in enumerate(transactions):
                    if i not in set(map(int, to_delete)):
                        keep.append(tx)
                save_transactions(DATA_PATH, keep)
                st.success(f"선택 삭제 완료 ✅ ({len(to_delete)}건)")
                st.rerun()

        # ✅ 편집 저장 실행
        if save_edits_clicked:
            push_history(transactions)

            # edited는 표시용 컬럼명(한글) 상태
            # 번호를 기반으로 원본 transactions를 업데이트한다
            updated = [dict(x) for x in transactions]  # 복사 후 수정

            for _, row in edited.iterrows():
                idx = int(row["번호"])

                # 안전 방어(혹시 꼬인 경우)
                if idx < 0 or idx >= len(updated):
                    continue

                # 날짜는 문자열로 저장(기존 규칙 유지)
                date_str = str(row["날짜"]).strip()

                updated[idx] = {
                    "date": date_str,
                    "type": str(row["구분"]).strip(),
                    "category": str(row["카테고리"]).strip(),
                    "description": str(row["내용"]).strip(),
                    "amount": int(row["금액"]) if pd.notna(row["금액"]) else 0,
                }

            save_transactions(DATA_PATH, updated)
            st.success("편집 저장 완료 ✅")
            st.rerun()


# -----------------------------
# (9) 차트 탭: 요약 + 카테고리별 지출 차트 (✅ 축/한글/숫자 안정)
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
        # ✅ DataFrame 생성
        cat_df = pd.DataFrame([{"카테고리": k, "금액": v} for k, v in cat_map.items()])
        cat_df = cat_df.sort_values("금액", ascending=False)

        # ✅ 카테고리별 색상(각각 다른 색)
        # (원하는 톤이면 여기 hex만 바꾸면 됨)
        color_map = {
            "식비": "#a78bfa",   # violet
            "교통": "#60a5fa",   # blue
            "통신": "#34d399",   # green
            "생활": "#f59e0b",   # amber
            "기타": "#fb7185",   # rose
        }
        # 데이터에 예상 외 카테고리 있어도 자동으로 색 배정(Plotly 기본 팔레트)
        cat_df["색상키"] = cat_df["카테고리"].astype(str)

        fig = px.bar(
            cat_df,
            x="카테고리",
            y="금액",
            color="색상키",
            color_discrete_map=color_map,
            title="카테고리별 지출 통계",
        )

        # ✅ 축 라벨/숫자 포맷 고정
        fig.update_layout(
            showlegend=False,
            xaxis_title="카테고리",
            yaxis_title="금액(원)",
            margin=dict(l=40, r=20, t=60, b=40),
        )
        # ✅ y축: 5k/10k 같은 축약 금지 → 5000/10000/15000 형태로
        fig.update_yaxes(tickformat=",d")  # 콤마 포함 정수
        # ✅ x축 글자 가로로
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

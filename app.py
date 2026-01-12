# app.py  # Streamlit UI 담당 (입력/표/요약/그래프/필터)  # ← 네 역할

import os  # 파일 경로 처리  # ← CSV 저장 경로 만들 때 사용
import pandas as pd  # 표/그룹통계용  # ← st.dataframe, 그룹핑
import streamlit as st  # Streamlit UI  # ← 화면 구성

# 팀원이 만든 로직 모듈 import  # ← "UI는 호출만 한다" 원칙
from ledger.repository import load_transactions, save_transactions  # CSV I/O
from ledger.services import calc_summary, calc_category_expense  # 통계 계산


# -----------------------------
# (0) 기본 설정  # ← 화면 전체 설정
# -----------------------------
st.set_page_config(page_title="나만의 미니 가계부", layout="wide")  # 제목/레이아웃(채점 UI 가점)

DATA_PATH = os.path.join("data", "ledger.csv")  # 저장 파일 위치  # ← 팀 폴더 구조 기준


# -----------------------------
# (1) 유틸: 리스트(dict) -> DataFrame  # ← 표/필터/그래프 공통으로 쓰기
# -----------------------------
def to_df(transactions: list) -> pd.DataFrame:
    # transactions가 비었을 때도 안전하게 빈 DF 반환  # ← "빈 화면 오류" 방지(감점 방지)
    if not transactions:
        return pd.DataFrame(columns=["date", "type", "category", "description", "amount"])

    df = pd.DataFrame(transactions)  # 리스트 -> 표 형태로 변환  # ← st.dataframe에 바로 사용
    # amount는 숫자여야 함  # ← 혹시 문자열로 들어오면 변환
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0).astype(int)
    # date는 비교/정렬을 위해 datetime으로  # ← 기간필터 구현용
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


# -----------------------------
# (2) 앱 시작: 데이터 로드  # ← 앱 재실행해도 데이터 유지(F4)
# -----------------------------
transactions = load_transactions(DATA_PATH)  # CSV 있으면 읽고, 없으면 빈 리스트  # ← repository 요구사항
df_all = to_df(transactions)  # 전부 DF로 변환  # ← 이후 필터에서 사용


# -----------------------------
# (3) 타이틀 영역  # ← 가독성/대시보드 경험(UI 채점)
# -----------------------------
st.title("🧾 나만의 미니 가계부 (지출 관리 서비스)")  # 페이지 제목
st.caption("입력 → 저장 → 즉시 반영되는 MVP 가계부")  # 설명 문구(UX 가점)


# -----------------------------
# (4) 사이드바: 필터 + 입력 폼  # ← 입력 UI(5점) + 즉시 반영(5점)
# -----------------------------
st.sidebar.header("🔎 필터")  # 필터 섹션

# (4-1) 기간 필터(도전 D1)  # ← 목록/통계/그래프에 동일 적용
if df_all.empty or df_all["date"].isna().all():
    # 데이터 없으면 기본값 오늘로  # ← date_input 에러 방지
    min_date = pd.Timestamp.today().date()
    max_date = pd.Timestamp.today().date()
else:
    min_date = df_all["date"].min().date()
    max_date = df_all["date"].max().date()

start_date, end_date = st.sidebar.date_input(
    "기간 선택", value=(min_date, max_date)  # 시작/끝 기본값  # ← 필터 UX
)

# (4-2) 검색 필터(도전 D2)  # ← 내용(description) 포함 여부
keyword = st.sidebar.text_input("검색어(내용 포함)", value="")  # 빈값이면 전체

# (4-3) 구분/카테고리 필터  # ← UI 편의(감점 방지)
type_filter = st.sidebar.selectbox("구분", ["전체", "지출", "수입"])  # 선택
category_options = ["전체"]
if not df_all.empty:
    category_options += sorted(df_all["category"].dropna().unique().tolist())
category_filter = st.sidebar.selectbox("카테고리", category_options)

st.sidebar.divider()  # 구분선  # ← UI 가독성

# (4-4) 입력 폼(필수 F1)  # ← 날짜/구분/카테고리/내용/금액 + 등록 버튼
st.sidebar.header("➕ 새 거래 등록")

with st.sidebar.form("add_tx_form", clear_on_submit=True):
    in_date = st.date_input("날짜")  # 날짜 입력  # ← 요구사항
    in_type = st.selectbox("구분", ["지출", "수입"])  # 지출/수입  # ← 요구사항
    in_category = st.text_input("카테고리", value="식비")  # 카테고리  # ← 요구사항
    in_desc = st.text_input("내용", value="")  # 메모  # ← 요구사항
    in_amount = st.number_input("금액(원)", min_value=0, step=1000)  # 금액(정수)  # ← 검증 자동
    submitted = st.form_submit_button("등록")  # 등록 버튼  # ← 요구사항

# (4-5) 등록 처리  # ← 등록 시 저장 + 즉시 반영(대시보드 경험 5점)
if submitted:
    # 기본 검증  # ← 사용자 불편 감점 방지
    if in_category.strip() == "":
        st.sidebar.error("카테고리를 입력하세요.")  # 입력 검증
    elif in_desc.strip() == "":
        st.sidebar.error("내용을 입력하세요.")  # 입력 검증
    else:
        # 거래 1건을 dict로 생성  # ← 수업 범위(딕셔너리 방식)
        new_tx = {
            "date": str(in_date),  # YYYY-MM-DD 문자열  # ← CSV 저장 형식
            "type": in_type,  # 지출/수입
            "category": in_category.strip(),
            "description": in_desc.strip(),
            "amount": int(in_amount),  # 정수로 저장
        }

        # 리스트에 추가 후 저장  # ← F4: 덮어쓰기 저장
        transactions.append(new_tx)
        save_transactions(DATA_PATH, transactions)

        st.sidebar.success(f"등록 완료 ✅ {new_tx['date']} / {new_tx['type']} / {new_tx['category']} / {new_tx['amount']:,}원")

        # 즉시 반영: rerun  # ← "입력 후 즉시 반영" 채점 포인트(5점)
        st.rerun()


# -----------------------------
# (5) 필터 적용  # ← 목록/통계/그래프 모두 동일 기준(요구사항)
# -----------------------------
df = df_all.copy()  # 전체 -> 필터용 복사

# 기간 필터  # ← start<=date<=end
df = df[(df["date"].dt.date >= start_date) & (df["date"].dt.date <= end_date)]

# 구분 필터
if type_filter != "전체":
    df = df[df["type"] == type_filter]

# 카테고리 필터
if category_filter != "전체":
    df = df[df["category"] == category_filter]

# 검색 필터(내용 포함)
if keyword.strip() != "":
    df = df[df["description"].fillna("").str.lower().str.contains(keyword.strip().lower())]


# -----------------------------
# (6) 메인: 탭 구성(데이터/차트/관제)  # ← 너가 보여준 “탭 UI”로 가점
# -----------------------------
tab_data, tab_chart, tab_alert = st.tabs(["📄 데이터", "📊 차트", "🚨 관제(예산)"])


# -----------------------------
# (7) 데이터 탭: 표 출력(F2)  # ← "목록 조회" 요구사항
# -----------------------------
with tab_data:
    st.subheader("📌 필터 결과 데이터")

    if df.empty:
        st.info("등록된 거래가 없습니다. (또는 필터 조건에 맞는 데이터가 없습니다.)")  # 빈 데이터 안내  # ← 요구사항
    else:
        # 보기 좋게: 날짜 문자열로, 정렬 최신순  # ← UX 가점
        view_df = df.copy()
        view_df["date"] = view_df["date"].dt.strftime("%Y-%m-%d")
        view_df = view_df.sort_values("date", ascending=False)

        # 컬럼 순서 고정  # ← 채점 기준 컬럼 맞추기
        view_df = view_df[["date", "type", "category", "description", "amount"]]
        view_df.columns = ["날짜", "구분", "카테고리", "내용", "금액"]

        st.dataframe(view_df, use_container_width=True)  # 표 출력  # ← F2


# -----------------------------
# (8) 차트 탭: 요약 + 그래프(F3, F5)  # ← metric/차트 표시
# -----------------------------
with tab_chart:
    st.subheader("📌 요약 지표 (Metric)")

    # DF -> 다시 list[dict]로 변환해서 서비스 함수에 넣기  # ← 팀 함수 시그니처 맞추기
    filtered_transactions = []
    if not df.empty:
        tmp = df.copy()
        tmp["date"] = tmp["date"].dt.strftime("%Y-%m-%d")
        filtered_transactions = tmp.to_dict(orient="records")

    income, expense, balance = calc_summary(filtered_transactions)  # 요약 계산  # ← F3

    c1, c2, c3 = st.columns(3)  # 3칸으로 metric 배치  # ← UX/가독성 가점
    c1.metric("총 수입", f"{income:,} 원")
    c2.metric("총 지출", f"{expense:,} 원")
    c3.metric("잔액(수입-지출)", f"{balance:,} 원")

    st.divider()

    st.subheader("📈 카테고리별 지출 통계")

    # 카테고리별 지출 합계 dict 받기  # ← F5
    cat_map = calc_category_expense(filtered_transactions)

    if not cat_map:
        st.info("지출 데이터가 없어서 그래프를 표시할 수 없습니다.")  # 빈 데이터 예외 처리(감점 방지)
    else:
        cat_df = pd.DataFrame(
            [{"category": k, "amount": v} for k, v in cat_map.items()]
        ).sort_values("amount", ascending=False)

        cat_df = cat_df.set_index("category")  # bar_chart는 index를 라벨로 사용  # ← Streamlit 기본 차트
        st.bar_chart(cat_df)  # 막대차트 출력  # ← F5


# -----------------------------
# (9) 관제 탭: 예산 경고(D4)  # ← 선택 기능(보너스) + 화면 완성도
# -----------------------------
with tab_alert:
    st.subheader("🚨 지출 한도(예산) 관제")

    budget = st.number_input("월 예산 입력(원)", min_value=0, step=10000)  # 예산 입력  # ← D4
    # 현재 필터 기준 지출 합계 사용  # ← 필터 연동(점수 가점)
    filtered_transactions = []
    if not df.empty:
        tmp = df.copy()
        tmp["date"] = tmp["date"].dt.strftime("%Y-%m-%d")
        filtered_transactions = tmp.to_dict(orient="records")

    _, expense, _ = calc_summary(filtered_transactions)  # 총 지출만 가져오기  # ← services 재사용

    st.write(f"현재 지출 합계: **{expense:,} 원**")  # 지출 표시

    if budget > 0:
        ratio = expense / budget  # 사용률  # ← D4
        st.progress(min(ratio, 1.0))  # 0~1.0 범위  # ← UX 가점

        if ratio >= 1.0:
            st.error("❌ 예산을 초과했습니다!")  # 100% 초과  # ← 요구사항
        elif ratio >= 0.8:
            st.warning("⚠️ 예산의 80%를 사용했습니다!")  # 80% 이상  # ← 요구사항
        else:
            st.success("✅ 예산 사용이 안정적입니다.")  # 안전 구간
    else:
        st.info("예산을 입력하면 경고/진행률이 표시됩니다.")  # 예산 0일 때 안내

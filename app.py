import streamlit as st

st.title("나만의 미니 가계부")
# streamlit_app.py
import streamlit as st
from datetime import datetime

st.title("가계부 입력 (Dictionary 기반)")

# ----------------------
# 카테고리 정의
# ----------------------
categories = {
    "수입": ["급여", "이자", "할인적립", "투자수익", "기타"],
    "지출": [
        "주거", "통신", "보험", "상환", "식비", "교통비",
        "생활용품", "의류", "미용", "건강", "여행",
        "교육", "경조사", "기타"
    ]
}

# ----------------------
# 거래 목록 (세션 상태)
# ----------------------
if "transactions" not in st.session_state:
    st.session_state["transactions"] = []   # ← 딕셔너리들을 담는 리스트

# ----------------------
# 입력 UI
# ----------------------
date = st.date_input("날짜")
trade_type = st.selectbox("거래종류", list(categories.keys()))
category = st.selectbox("분류", categories[trade_type])
description = st.text_input("설명 (선택사항)")
amount = st.number_input("금액", min_value=0, step=1000)

# ----------------------
# 저장 처리
# ----------------------
if st.button("저장"):
    # 거래 한 건 딕셔너리 생성
    transaction = {
        "날짜": date.strftime("%Y-%m-%d"),
        "거래종류": trade_type,
        "분류": category,
        "설명": description,
        "금액": amount,
        "기록시각": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    # 거래 목록 리스트에 추가
    st.session_state["transactions"].append(transaction)

    st.success("거래 1건이 저장되었습니다.")

# ----------------------
# 거래 목록 출력
# ----------------------
st.subheader("거래 목록")
st.write(st.session_state["transactions"])

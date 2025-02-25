import streamlit as st

def sidebar_menu():
    st.sidebar.title("📊 데이터 시각화")
    
    # 카테고리 선택
    category = st.sidebar.selectbox("카테고리 선택", [
        "부서별 통계", "연령대별 통계", "지역별 통계"
    ])
    
    # 하위 항목 선택
    if category == "부서별 통계":
        subcategory = st.sidebar.selectbox("세부 항목", ["과기본", "연기단", "경영본부"])
    elif category == "연령대별 통계":
        subcategory = st.sidebar.selectbox("세부 항목", ["20대", "30대", "40대", "50대"])
    else:
        subcategory = st.sidebar.selectbox("세부 항목", ["서울", "경기", "부산", "대전"])
    
    return category, subcategory

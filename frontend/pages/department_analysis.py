import streamlit as st
import pandas as pd
import plotly.express as px
from frontend.database import (
    get_db_connection, 
    save_to_powerbi_table,
    save_analysis,
    load_existing_analysis,
    save_analysis_state
)
from frontend.services.ai_analysis import generate_department_analysis

def show_department_analysis_page(file_id, subcategory):
    if subcategory == "1. 기본 현황":
        show_basic_status(file_id)
    elif subcategory == "2. 학력/전공":
        show_education_analysis(file_id)
    # ... 기타 카테고리

def show_basic_status(file_id):
    # 상단 탭으로 세부 항목 구분
    tab1, tab2, tab3 = st.tabs([
        "부서별 분포",
        "성별 분포",
        "연령대 분포"
    ])
    
    with tab1:
        show_department_distribution(file_id)
    with tab2:
        show_gender_distribution(file_id)
    with tab3:
        show_age_distribution(file_id)

def show_education_analysis(file_id):
    # 상단 탭으로 세부 항목 구분
    tab1, tab2 = st.tabs([
        "학력 분포",
        "전공 분포"
    ])
    
    with tab1:
        show_education_distribution(file_id)
    with tab2:
        show_major_distribution(file_id)

def show_department_distribution(file_id):
    # 2단 레이아웃
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("데이터 테이블")
        conn = get_db_connection()
        df = pd.read_sql("""
            SELECT department, COUNT(*) as count,
                   ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
            FROM respondents 
            WHERE file_id = %s
            GROUP BY department
            ORDER BY count DESC
        """, conn, params=[file_id])
        
        # 데이터 테이블 표시
        st.dataframe(
            df.style.format({
                'count': '{:,.0f}',
                'percentage': '{:.1f}%'
            }),
            use_container_width=True
        )
        
        # PowerBI용 데이터 저장
        save_to_powerbi_table(file_id, "department_distribution", df)
        
    with col2:
        st.subheader("시각화")
        # 도넛 차트로 변경
        fig = px.pie(df, 
                    values='count', 
                    names='department',
                    title='부서별 분포',
                    hole=0.5)  # 도넛 차트를 위한 hole 설정
        
        # 차트 스타일 수정
        fig.update_traces(
            textposition='outside',
            textinfo='percent+label',
            texttemplate='%{label}<br>%{percent:.1%}'
        )
        
        # 레이아웃 수정
        fig.update_layout(
            showlegend=True,
            legend=dict(
                orientation="vertical",
                yanchor="middle",
                y=0.5,
                xanchor="right",
                x=1.1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    # 구분선
    st.markdown("---")
    
    # AI 분석 섹션
    col_button1, col_button2 = st.columns([1, 1])
    with col_button1:
        if st.button("AI 분석 실행", use_container_width=True):
            with st.spinner("AI가 분석 중입니다..."):
                analysis_text = generate_department_analysis(df)
                save_analysis(file_id, "department", "distribution", analysis_text)
                st.success("AI 분석이 완료되었습니다!")
                # AI 분석 결과를 텍스트 영역에 자동으로 표시하기 위해 페이지 새로고침
                st.experimental_rerun()
    
    with col_button2:
        if st.button("분석 내용 저장", use_container_width=True):
            save_analysis_state(file_id, "department_distribution", df, fig, edited_analysis)
            st.success("현재 분석 상태가 저장되었습니다!")
    
    # 분석 내용 편집 영역
    st.subheader("분석 내용")
    existing_analysis = load_existing_analysis(file_id, "department", "distribution")
    edited_analysis = st.text_area(
        "분석 내용을 입력하거나 수정하세요",
        value=existing_analysis,  # 저장된 분석 내용이나 AI 분석 결과가 여기에 표시됨
        height=200
    )

def show_gender_distribution(file_id):
    # 2단 레이아웃
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("데이터 테이블")
        conn = get_db_connection()
        df = pd.read_sql("""
            SELECT gender, COUNT(*) as count,
                   ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
            FROM respondents 
            WHERE file_id = %s
            GROUP BY gender
            ORDER BY count DESC
        """, conn, params=[file_id])
        
        st.dataframe(
            df.style.format({
                'count': '{:,.0f}',
                'percentage': '{:.1f}%'
            }),
            use_container_width=True
        )
        
        save_to_powerbi_table(file_id, "gender_distribution", df)
        
    with col2:
        st.subheader("시각화")
        fig = px.pie(df, values='count', names='gender', 
                    title='성별 분포',
                    hole=0.4)
        fig.update_traces(textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    # 구분선
    st.markdown("---")
    
    # AI 분석 섹션
    col_button1, col_button2 = st.columns([1, 1])
    with col_button1:
        if st.button("AI 분석 실행", key="gender_ai", use_container_width=True):
            with st.spinner("AI가 분석 중입니다..."):
                analysis_text = generate_department_analysis(df)
                save_analysis(file_id, "gender", "distribution", analysis_text)
                st.success("AI 분석이 완료되었습니다!")
    
    with col_button2:
        if st.button("분석 내용 저장", key="gender_save", use_container_width=True):
            save_analysis_state(file_id, "gender_distribution", df, fig, edited_analysis)
            st.success("현재 분석 상태가 저장되었습니다!")
    
    # 분석 내용 편집 영역
    st.subheader("분석 내용")
    existing_analysis = load_existing_analysis(file_id, "gender", "distribution")
    edited_analysis = st.text_area(
        "분석 내용을 입력하거나 수정하세요",
        value=existing_analysis,
        height=200,
        key="gender_analysis"
    )
    
    if st.button("분석 내용 업데이트", key="gender_update", use_container_width=True):
        save_analysis(file_id, "gender", "distribution", edited_analysis)
        st.success("분석 내용이 업데이트되었습니다!")

def show_age_distribution(file_id):
    # 2단 레이아웃
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("데이터 테이블")
        conn = get_db_connection()
        df = pd.read_sql("""
            SELECT age_group, COUNT(*) as count,
                   ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
            FROM respondents 
            WHERE file_id = %s
            GROUP BY age_group
            ORDER BY age_group
        """, conn, params=[file_id])
        
        st.dataframe(
            df.style.format({
                'count': '{:,.0f}',
                'percentage': '{:.1f}%'
            }),
            use_container_width=True
        )
        
        save_to_powerbi_table(file_id, "age_distribution", df)
        
    with col2:
        st.subheader("시각화")
        fig = px.bar(df, x='age_group', y='count',
                    text='percentage',
                    title='연령대 분포')
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
    
    # 구분선
    st.markdown("---")
    
    # AI 분석 섹션
    col_button1, col_button2 = st.columns([1, 1])
    with col_button1:
        if st.button("AI 분석 실행", key="age_ai", use_container_width=True):
            with st.spinner("AI가 분석 중입니다..."):
                analysis_text = generate_department_analysis(df)
                save_analysis(file_id, "age", "distribution", analysis_text)
                st.success("AI 분석이 완료되었습니다!")
    
    with col_button2:
        if st.button("분석 내용 저장", key="age_save", use_container_width=True):
            save_analysis_state(file_id, "age_distribution", df, fig, edited_analysis)
            st.success("현재 분석 상태가 저장되었습니다!")
    
    # 분석 내용 편집 영역
    st.subheader("분석 내용")
    existing_analysis = load_existing_analysis(file_id, "age", "distribution")
    edited_analysis = st.text_area(
        "분석 내용을 입력하거나 수정하세요",
        value=existing_analysis,
        height=200,
        key="age_analysis"
    )
    
    if st.button("분석 내용 업데이트", key="age_update", use_container_width=True):
        save_analysis(file_id, "age", "distribution", edited_analysis)
        st.success("분석 내용이 업데이트되었습니다!")

def show_education_distribution(file_id):
    # 2단 레이아웃
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("데이터 테이블")
        conn = get_db_connection()
        df = pd.read_sql("""
            SELECT education, COUNT(*) as count,
                   ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
            FROM respondents 
            WHERE file_id = %s
            GROUP BY education
            ORDER BY count DESC
        """, conn, params=[file_id])
        
        st.dataframe(
            df.style.format({
                'count': '{:,.0f}',
                'percentage': '{:.1f}%'
            }),
            use_container_width=True
        )
        
        save_to_powerbi_table(file_id, "education_distribution", df)
        
    with col2:
        st.subheader("시각화")
        fig = px.bar(df, x='education', y='count',
                    text='percentage',
                    title='학력 분포')
        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
        st.plotly_chart(fig, use_container_width=True)
    
    # 구분선
    st.markdown("---")
    
    # AI 분석 섹션
    col_button1, col_button2 = st.columns([1, 1])
    with col_button1:
        if st.button("AI 분석 실행", key="edu_ai", use_container_width=True):
            with st.spinner("AI가 분석 중입니다..."):
                analysis_text = generate_department_analysis(df)
                save_analysis(file_id, "education", "distribution", analysis_text)
                st.success("AI 분석이 완료되었습니다!")
    
    with col_button2:
        if st.button("분석 내용 저장", key="edu_save", use_container_width=True):
            save_analysis_state(file_id, "education_distribution", df, fig, edited_analysis)
            st.success("현재 분석 상태가 저장되었습니다!")
    
    # 분석 내용 편집 영역
    st.subheader("분석 내용")
    existing_analysis = load_existing_analysis(file_id, "education", "distribution")
    edited_analysis = st.text_area(
        "분석 내용을 입력하거나 수정하세요",
        value=existing_analysis,
        height=200,
        key="edu_analysis"
    )
    
    if st.button("분석 내용 업데이트", key="edu_update", use_container_width=True):
        save_analysis(file_id, "education", "distribution", edited_analysis)
        st.success("분석 내용이 업데이트되었습니다!")

def show_major_distribution(file_id):
    # 2단 레이아웃
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("데이터 테이블")
        conn = get_db_connection()
        df = pd.read_sql("""
            SELECT major, COUNT(*) as count,
                   ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
            FROM respondents 
            WHERE file_id = %s
            GROUP BY major
            ORDER BY count DESC
        """, conn, params=[file_id])
        
        st.dataframe(
            df.style.format({
                'count': '{:,.0f}',
                'percentage': '{:.1f}%'
            }),
            use_container_width=True
        )
        
        save_to_powerbi_table(file_id, "major_distribution", df)
        
    with col2:
        st.subheader("시각화")
        fig = px.pie(df, values='count', names='major',
                    title='전공 분포',
                    hole=0.4)
        fig.update_traces(textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
    
    # 구분선
    st.markdown("---")
    
    # AI 분석 섹션
    col_button1, col_button2 = st.columns([1, 1])
    with col_button1:
        if st.button("AI 분석 실행", key="major_ai", use_container_width=True):
            with st.spinner("AI가 분석 중입니다..."):
                analysis_text = generate_department_analysis(df)
                save_analysis(file_id, "major", "distribution", analysis_text)
                st.success("AI 분석이 완료되었습니다!")
    
    with col_button2:
        if st.button("분석 내용 저장", key="major_save", use_container_width=True):
            save_analysis_state(file_id, "major_distribution", df, fig, edited_analysis)
            st.success("현재 분석 상태가 저장되었습니다!")
    
    # 분석 내용 편집 영역
    st.subheader("분석 내용")
    existing_analysis = load_existing_analysis(file_id, "major", "distribution")
    edited_analysis = st.text_area(
        "분석 내용을 입력하거나 수정하세요",
        value=existing_analysis,
        height=200,
        key="major_analysis"
    )
    
    if st.button("분석 내용 업데이트", key="major_update", use_container_width=True):
        save_analysis(file_id, "major", "distribution", edited_analysis)
        st.success("분석 내용이 업데이트되었습니다!") 
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from frontend.database import (
    get_db_connection,
    save_to_powerbi_table,
    save_analysis,
    load_existing_analysis,
    save_analysis_state
)
from frontend.services.ai_analysis import generate_department_analysis
from frontend.components.ai_analysis import show_ai_analysis

def show_cgs_analysis(file_id):
    st.title("CGS(기업지배구조) 분석")
    
    # 전체 통계 탭과 부서별 상세 분석 탭으로 구분
    tab1, tab2 = st.tabs(["전체 통계", "부서별 상세 분석"])
    
    with tab1:
        show_overall_statistics(file_id)
    
    with tab2:
        show_detailed_analysis(file_id)

def show_overall_statistics(file_id):
    # 데이터 가져오기
    conn = get_db_connection()
    df = pd.read_sql("""
        SELECT 
            q.question_category,
            q.survey_id,
            r.response,
            COUNT(*) as response_count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY q.survey_id), 1) as percentage
        FROM cgs_responses r
        JOIN cgs_questions q ON r.survey_id = q.survey_id
        WHERE r.file_id = %s
        GROUP BY q.question_category, q.survey_id, r.response
        ORDER BY q.question_category, q.survey_id, r.response
    """, conn, params=[file_id])
    
    # 응답 의미 매핑 (7점 척도)
    response_meanings = {
        1: '전혀 아니다',
        2: '아니다',
        3: '약간 아니다',
        4: '보통이다',
        5: '약간 그렇다',
        6: '그렇다',
        7: '매우 그렇다'
    }
    
    # 색상 매핑 (7단계)
    colors = {
        1: '#FF0000',  # 빨강
        2: '#FF6666',  # 연한 빨강
        3: '#FFCC66',  # 주황
        4: '#FFFF99',  # 노랑
        5: '#99FF99',  # 연한 초록
        6: '#66CC66',  # 초록
        7: '#009900'   # 진한 초록
    }
    
    # 각 카테고리별 분석
    for category in df['question_category'].unique():
        st.subheader(f"📊 {category}")
        
        # 해당 카테고리 데이터
        cat_data = df[df['question_category'] == category]
        
        # 1. 응답 분포 차트
        fig = go.Figure()
        
        for response in sorted(cat_data['response'].unique()):
            response_data = cat_data[cat_data['response'] == response]
            
            fig.add_trace(go.Bar(
                name=f"{response}점 - {response_meanings[response]}",
                x=response_data['survey_id'],
                y=response_data['percentage'],
                text=response_data['percentage'].apply(lambda x: f'{x:.1f}%'),
                textposition='auto',
                marker_color=colors[response]
            ))
        
        fig.update_layout(
            title=f'{category} - 문항별 응답 분포',
            barmode='stack',
            xaxis_title='문항',
            yaxis_title='응답 비율(%)',
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # 2. 상세 데이터
        col1, col2 = st.columns(2)
        
        with col1:
            # 평균 점수 계산
            avg_scores = cat_data.groupby('survey_id').apply(
                lambda x: (x['response'] * x['response_count']).sum() / x['response_count'].sum()
            ).round(2)
            
            st.metric(
                "카테고리 평균 점수",
                f"{avg_scores.mean():.2f}",
                f"최고 {avg_scores.max():.2f} / 최저 {avg_scores.min():.2f}"
            )
        
        with col2:
            # 긍정 응답 비율 (5~7점)
            positive_pct = cat_data[cat_data['response'] >= 5]['response_count'].sum() / \
                         cat_data['response_count'].sum() * 100
            
            st.metric(
                "긍정 응답 비율",
                f"{positive_pct:.1f}%",
                f"부정 응답 {100-positive_pct:.1f}%"
            )
        
        # 3. 응답 분포 테이블
        st.write("### 상세 응답 분포 (%)")
        pivot_df = pd.pivot_table(
            cat_data,
            values='percentage',
            index='survey_id',
            columns='response',
            fill_value=0
        ).round(1)
        
        pivot_df.columns = [f"{col}점 - {response_meanings[col]}" for col in pivot_df.columns]
        
        st.dataframe(
            pivot_df.style.format("{:.1f}%"),
            use_container_width=True
        )

def show_cgs_by_department(file_id):
    st.info("CGS 부서별 분석 - 개발 중")
    # TODO: 구현 예정

def show_cgs_by_question(file_id):
    st.info("CGS 문항별 분석 - 개발 중")
    # TODO: 구현 예정 

def show_detailed_analysis(file_id):
    st.info("부서별 상세 분석 - 개발 중")
    # TODO: 부서별 분석 기능 구현 예정

def show_category_analysis(file_id, category):
    """카테고리별 분석 표시"""
    conn = get_db_connection()
    df = pd.read_sql("""
        WITH avg_scores AS (
            SELECT 
                r.respondent_id,
                d.department,
                AVG(CAST(r.response AS FLOAT))::numeric as avg_score
            FROM cgs_responses r
            JOIN respondents d ON r.respondent_id = d.respondent_id 
            JOIN cgs_questions q ON r.survey_id = q.survey_id
            WHERE r.file_id = %s AND q.question_category = %s
            GROUP BY r.respondent_id, d.department
        )
        SELECT 
            department,
            COUNT(*) as count,
            AVG(avg_score)::numeric(10,2) as avg_score,
            MIN(avg_score)::numeric(10,2) as min_score,
            MAX(avg_score)::numeric(10,2) as max_score,
            STDDEV(avg_score)::numeric(10,2) as std_score
        FROM avg_scores
        GROUP BY department
        ORDER BY avg_score DESC
    """, conn, params=[int(file_id), category])

    st.subheader(f"📊 {category} 분석")
    
    # 1. 막대 차트 (고유 key 추가)
    fig1 = px.bar(df, x='department', y='avg_score',
                  title=f'{category} - 부서별 평균 점수')
    st.plotly_chart(fig1, use_container_width=True,
                    key=f"cgs_bar_{category}_{file_id}")

    # 2. 박스 플롯 (고유 key 추가)
    fig2 = px.box(df, x='department', y='avg_score',
                  title=f'{category} - 부서별 분포')
    st.plotly_chart(fig2, use_container_width=True,
                    key=f"cgs_box_{category}_{file_id}")

    # AI 분석 섹션
    show_ai_analysis(file_id, df, ("cgs", category), f"cgs_{category}") 
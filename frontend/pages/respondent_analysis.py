import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from frontend.database import (
    get_db_connection,
    save_to_powerbi_table,
    save_analysis,
    load_existing_analysis
)
from frontend.services.ai_analysis import generate_department_analysis

def show_basic_status(file_id):
    st.markdown("""
        <style>
        .stExpander {
            border: 1px solid #ddd;
            border-radius: 8px;
            margin-top: 20px;
        }
        .stTextArea textarea {
            font-size: 16px;
            font-family: 'Noto Sans KR', sans-serif;
        }
        .stButton button {
            font-weight: bold;
            height: 45px;
        }
        </style>
    """, unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "부서별 분포",
        "성별 분포",
        "연령대 분포",
        "학력/전공 분포",
        "자격증 현황"
    ])
    
    with tab1:
        show_department_distribution(file_id)
    with tab2:
        show_gender_distribution(file_id)
    with tab3:
        show_age_distribution(file_id)
    with tab4:
        show_education_distribution(file_id)
    with tab5:
        show_certification_distribution(file_id)

def show_department_distribution(file_id):
    st.subheader("부서별 분포")
    
    # file_id를 int로 변환하여 쿼리 실행
    conn = get_db_connection()
    df = pd.read_sql("""
        SELECT 
            department,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
        FROM respondents 
        WHERE file_id = %s
        GROUP BY department 
        ORDER BY count DESC
    """, conn, params=[int(file_id)])  # int로 명시적 변환
    
    # 1. 상단: 주요 지표
    total = df['count'].sum()
    max_dept = df.iloc[0]['department']
    max_pct = df.iloc[0]['percentage']
    
    col1, col2, col3 = st.columns(3)
    col1.metric("총 응답자", f"{total:,}명")
    col2.metric("최다 부서", max_dept)
    col3.metric("최다 부서 비율", f"{max_pct:.1f}%")
    
    # 2. 4분할 레이아웃
    col1, col2 = st.columns(2)
    
    # 왼쪽 상단: 데이터 테이블
    with col1:
        st.write("📋 상세 데이터")
        st.dataframe(
            df.style.format({
                'count': '{:,}명',
                'percentage': '{:.1f}%'
            }),
            use_container_width=True
        )
    
    # 오른쪽 상단: 도넛 차트
    with col2:
        st.write("📊 부서별 분포")
        fig1 = px.pie(df, 
                     values='count',
                     names='department',
                     hole=0.4,
                     title='부서별 인원 분포')
        fig1.update_traces(textinfo='percent+label')
        st.plotly_chart(fig1, use_container_width=True)
    
    # 왼쪽 하단: 막대 그래프
    with col1:
        fig2 = px.bar(df,
                     x='department',
                     y='count',
                     text='count',
                     title='부서별 인원수')
        fig2.update_traces(texttemplate='%{text:,}명')
        st.plotly_chart(fig2, use_container_width=True)
    
    # 오른쪽 하단: 누적 비율 라인 차트
    with col2:
        df['cumulative_pct'] = df['percentage'].cumsum()
        fig3 = px.line(df,
                      x='department',
                      y='cumulative_pct',
                      markers=True,
                      title='부서별 누적 비율')
        fig3.update_traces(texttemplate='%{y:.1f}%')
        st.plotly_chart(fig3, use_container_width=True)

    # AI 분석
    show_ai_analysis(file_id, df, ("respondent", "department"), "dept")

def show_gender_distribution(file_id):
    # 1. 데이터 테이블과 차트
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
        fig = px.pie(df, 
                    values='count', 
                    names='gender',
                    title='성별 분포',
                    hole=0.5)
        
        fig.update_traces(
            textposition='outside',
            textinfo='percent+label'
        )
        st.plotly_chart(fig, use_container_width=True)

    # AI 분석
    show_ai_analysis(file_id, df, ("respondent", "gender"), "gender")

def show_age_distribution(file_id):
    st.subheader("연령대 분포")
    
    # 데이터 가져오기
    conn = get_db_connection()
    df = pd.read_sql("""
        SELECT 
            age_group,
            gender,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY age_group), 1) as gender_percentage,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as total_percentage
        FROM respondents 
        WHERE file_id = %s
        GROUP BY age_group, gender
        ORDER BY age_group, gender
    """, conn, params=[file_id])
    
    # 전체 요약 데이터
    summary_df = df.groupby('age_group').agg({
        'count': 'sum',
        'total_percentage': 'sum'
    }).reset_index()
    
    # 1. 상단: 주요 지표
    total = df['count'].sum()
    max_age = summary_df.iloc[summary_df['count'].idxmax()]['age_group']
    max_pct = summary_df.iloc[summary_df['count'].idxmax()]['total_percentage']
    
    col1, col2, col3 = st.columns(3)
    col1.metric("총 인원", f"{total:,}명")
    col2.metric("최다 연령대", max_age)
    col3.metric("최다 연령대 비율", f"{max_pct:.1f}%")
    
    # 2. 4분할 레이아웃
    col1, col2 = st.columns(2)
    
    # 왼쪽 상단: 데이터 테이블
    with col1:
        st.write("📋 상세 데이터")
        st.dataframe(
            summary_df.style.format({
                'count': '{:,}명',
                'total_percentage': '{:.1f}%'
            }),
            use_container_width=True
        )
    
    # 오른쪽 상단: 복합 차트 (막대 + 선)
    with col2:
        st.write("📊 연령대별 분포")
        
        # 복합 차트 생성
        fig = go.Figure()
        
        # 남성 막대 추가
        male_data = df[df['gender'] == '남성']
        fig.add_trace(go.Bar(
            name='남성',
            x=male_data['age_group'],
            y=male_data['count'],
            text=male_data['count'],
            marker_color='rgb(0, 87, 138)'
        ))
        
        # 여성 막대 추가
        female_data = df[df['gender'] == '여성']
        fig.add_trace(go.Bar(
            name='여성',
            x=female_data['age_group'],
            y=female_data['count'],
            text=female_data['count'],
            marker_color='rgb(255, 127, 80)'
        ))
        
        # 비율 선 추가
        fig.add_trace(go.Scatter(
            name='비율',
            x=summary_df['age_group'],
            y=summary_df['total_percentage'],
            yaxis='y2',
            line=dict(color='black', width=2, dash='dot'),
            mode='lines+markers+text',
            text=summary_df['total_percentage'].apply(lambda x: f'{x:.1f}%'),
            textposition='top center'
        ))
        
        # 레이아웃 설정
        fig.update_layout(
            title='연령대별 성별 분포 및 비율',
            barmode='stack',
            yaxis=dict(title='인원수'),
            yaxis2=dict(
                title='비율(%)',
                overlaying='y',
                side='right',
                range=[0, max(summary_df['total_percentage']) * 1.2]
            ),
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
    
    # 왼쪽 하단: 파이 차트
    with col1:
        fig2 = px.pie(df,
                     values='count',
                     names='age_group',
                     title='연령대별 비율')
        fig2.update_traces(textinfo='percent+label')
        st.plotly_chart(fig2, use_container_width=True)
    
    # 오른쪽 하단: 누적 비율
    with col2:
        df['cumulative_pct'] = df['total_percentage'].cumsum()
        fig3 = px.line(df,
                      x='age_group',
                      y='cumulative_pct',
                      markers=True,
                      title='연령대별 누적 비율')
        fig3.update_traces(texttemplate='%{y:.1f}%')
        st.plotly_chart(fig3, use_container_width=True)
    
    # AI 분석
    show_ai_analysis(file_id, df, ("respondent", "age"), "age")

def show_education_distribution(file_id):
    st.subheader("학력/전공 분포")
    
    tab1, tab2 = st.tabs(["학력 분포", "전공 분포"])
    
    with tab1:
        show_education_level_distribution(file_id)
    with tab2:
        show_major_distribution(file_id)

def show_certification_distribution(file_id):
    st.subheader("자격증 현황")
    
    conn = get_db_connection()
    df = pd.read_sql("""
        SELECT 
            certifications,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
        FROM respondents 
        WHERE file_id = %s AND certifications IS NOT NULL
        GROUP BY certifications
        ORDER BY count DESC
    """, conn, params=[file_id])
    
    # 1. 상단: 주요 지표
    total = df['count'].sum()
    max_cert = df.iloc[0]['certifications']
    max_pct = df.iloc[0]['percentage']
    
    col1, col2, col3 = st.columns(3)
    col1.metric("총 자격증 수", f"{total:,}개")
    col2.metric("최다 자격증", max_cert)
    col3.metric("최다 비율", f"{max_pct:.1f}%")
    
    # 2. 4분할 레이아웃
    col1, col2 = st.columns(2)
    
    # 왼쪽 상단: 데이터 테이블
    with col1:
        st.write("📋 상세 데이터")
        st.dataframe(
            df.style.format({
                'count': '{:,}명',
                'percentage': '{:.1f}%'
            }),
            use_container_width=True
        )
    
    # 오른쪽 상단: 도넛 차트
    with col2:
        st.write("📊 자격증 분포")
        fig1 = px.pie(df, 
                     values='count',
                     names='certifications',
                     hole=0.4,
                     title='자격증별 분포')
        fig1.update_traces(textinfo='percent+label')
        st.plotly_chart(fig1, use_container_width=True)
    
    # 왼쪽 하단: 막대 그래프
    with col1:
        fig2 = px.bar(df,
                     x='certifications',
                     y='count',
                     text='count',
                     title='자격증별 인원수')
        fig2.update_traces(texttemplate='%{text:,}명')
        st.plotly_chart(fig2, use_container_width=True)
    
    # 오른쪽 하단: 누적 비율
    with col2:
        df['cumulative_pct'] = df['percentage'].cumsum()
        fig3 = px.line(df,
                      x='certifications',
                      y='cumulative_pct',
                      markers=True,
                      title='자격증 누적 비율')
        fig3.update_traces(texttemplate='%{y:.1f}%')
        st.plotly_chart(fig3, use_container_width=True)
    
    # AI 분석
    show_ai_analysis(file_id, df, ("respondent", "certification"), "cert")

def show_education_level_distribution(file_id):
    st.subheader("학력 분포")
    
    # 데이터 가져오기
    conn = get_db_connection()
    df = pd.read_sql("""
        SELECT 
            education_level,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
        FROM respondents 
        WHERE file_id = %s
        GROUP BY education_level
        ORDER BY 
            CASE education_level
                WHEN '고졸' THEN 1
                WHEN '전문대졸' THEN 2
                WHEN '대졸' THEN 3
                WHEN '석사' THEN 4
                WHEN '박사' THEN 5
                ELSE 6
            END
    """, conn, params=[file_id])
    
    # 1. 상단: 주요 지표
    total = df['count'].sum()
    max_edu = df.iloc[0]['education_level']
    max_pct = df.iloc[0]['percentage']
    
    col1, col2, col3 = st.columns(3)
    col1.metric("총 인원", f"{total:,}명")
    col2.metric("최다 학력", max_edu)
    col3.metric("최다 학력 비율", f"{max_pct:.1f}%")
    
    # 2. 4분할 레이아웃
    col1, col2 = st.columns(2)
    
    # 왼쪽 상단: 데이터 테이블
    with col1:
        st.write("📋 상세 데이터")
        st.dataframe(
            df.style.format({
                'count': '{:,}명',
                'percentage': '{:.1f}%'
            }),
            use_container_width=True
        )
    
    # 오른쪽 상단: 도넛 차트
    with col2:
        st.write("📊 학력 분포")
        fig1 = px.pie(df, 
                     values='count',
                     names='education_level',
                     hole=0.4,
                     title='학력별 인원 분포')
        fig1.update_traces(textinfo='percent+label')
        st.plotly_chart(fig1, use_container_width=True)
    
    # 왼쪽 하단: 막대 그래프
    with col1:
        fig2 = px.bar(df,
                     x='education_level',
                     y='count',
                     text='count',
                     title='학력별 인원수')
        fig2.update_traces(texttemplate='%{text:,}명')
        st.plotly_chart(fig2, use_container_width=True)
    
    # 오른쪽 하단: 누적 비율 라인 차트
    with col2:
        df['cumulative_pct'] = df['percentage'].cumsum()
        fig3 = px.line(df,
                      x='education_level',
                      y='cumulative_pct',
                      markers=True,
                      title='학력별 누적 비율')
        fig3.update_traces(texttemplate='%{y:.1f}%')
        st.plotly_chart(fig3, use_container_width=True)

    # AI 분석
    show_ai_analysis(file_id, df, ("education", "level"), "edu")

def show_major_distribution(file_id):
    st.subheader("전공 분포")
    
    # 데이터 가져오기
    conn = get_db_connection()
    df = pd.read_sql("""
        SELECT 
            major,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage,
            education_level
        FROM respondents 
        WHERE file_id = %s
        GROUP BY major, education_level
        ORDER BY count DESC
    """, conn, params=[file_id])
    
    # 1. 상단: 주요 지표
    total = df.groupby('major')['count'].sum().reset_index()
    max_major = total.iloc[0]['major']
    max_count = total.iloc[0]['count']
    max_pct = (max_count / total['count'].sum()) * 100
    
    col1, col2, col3 = st.columns(3)
    col1.metric("총 인원", f"{total['count'].sum():,}명")
    col2.metric("최다 전공", max_major)
    col3.metric("최다 전공 비율", f"{max_pct:.1f}%")
    
    # 2. 4분할 레이아웃
    col1, col2 = st.columns(2)
    
    # 왼쪽 상단: 데이터 테이블
    with col1:
        st.write("📋 상세 데이터")
        summary_df = df.groupby('major').agg({
            'count': 'sum',
            'percentage': 'sum'
        }).reset_index()
        
        st.dataframe(
            summary_df.style.format({
                'count': '{:,}명',
                'percentage': '{:.1f}%'
            }),
            use_container_width=True
        )
    
    # 오른쪽 상단: 복합 차트 (막대 + 선)
    with col2:
        st.write("📊 전공별 분포")
        
        # 복합 차트 생성
        fig1 = go.Figure()
        
        # 학력별로 스택 막대 추가
        for level in df['education_level'].unique():
            level_data = df[df['education_level'] == level]
            fig1.add_trace(go.Bar(
                name=level,
                x=level_data['major'],
                y=level_data['count'],
                text=level_data['count']
            ))
        
        # 비율 선 추가
        fig1.add_trace(go.Scatter(
            name='비율',
            x=summary_df['major'],
            y=summary_df['percentage'],
            yaxis='y2',
            line=dict(color='black', width=2, dash='dot'),
            mode='lines+markers+text',
            text=summary_df['percentage'].apply(lambda x: f'{x:.1f}%'),
            textposition='top center'
        ))
        
        # 레이아웃 설정
        fig1.update_layout(
            title='전공별 학력 분포 및 비율',
            barmode='stack',
            yaxis=dict(title='인원수'),
            yaxis2=dict(
                title='비율(%)',
                overlaying='y',
                side='right',
                range=[0, max(summary_df['percentage']) * 1.2]
            ),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            )
        )
        
        st.plotly_chart(fig1, use_container_width=True)
    
    # 왼쪽 하단: 선버스트 차트
    with col1:
        fig2 = px.sunburst(
            df,
            path=['major', 'education_level'],
            values='count',
            title='전공-학력 계층 구조'
        )
        st.plotly_chart(fig2, use_container_width=True)
    
    # 오른쪽 하단: 트리맵
    with col2:
        fig3 = px.treemap(
            df,
            path=[px.Constant("전체"), 'major', 'education_level'],
            values='count',
            title='전공-학력 트리맵'
        )
        st.plotly_chart(fig3, use_container_width=True)
    
    # 3. 추가 차트들
    st.write("### 추가 시각화")
    col1, col2 = st.columns(2)
    
    # 왼쪽: 도넛 차트
    with col1:
        fig4 = px.pie(
            summary_df,
            values='count',
            names='major',
            hole=0.4,
            title='전공별 비율 (도넛 차트)'
        )
        fig4.update_traces(textinfo='percent+label')
        st.plotly_chart(fig4, use_container_width=True)
    
    # 오른쪽: 누적 영역 차트
    with col2:
        fig5 = px.area(
            df,
            x='major',
            y='count',
            color='education_level',
            title='전공별 학력 분포 (누적 영역)'
        )
        st.plotly_chart(fig5, use_container_width=True)

    # AI 분석
    show_ai_analysis(file_id, df, ("education", "major"), "major")

def show_ai_analysis(file_id, df, analysis_type, key_prefix):
    """AI 분석 공통 컴포넌트"""
    with st.expander("📊 AI 분석"):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # 기존 분석 불러오기
            existing = load_existing_analysis(file_id, analysis_type[0], analysis_type[1])
            
            # 고유한 키 생성 - file_id를 포함하여 완전히 고유하게 만듦
            text_key = f"analysis_{key_prefix}_{file_id}"
            
            # 텍스트 영역
            edited_text = st.text_area(
                "분석 내용",
                value=existing if existing else "",
                height=300,
                key=text_key  # 고유한 키 사용
            )
        
        with col2:
            # 분석 버튼
            if st.button("🤖 AI 분석", 
                        key=f"btn_analyze_{key_prefix}_{file_id}",  # 버튼도 고유 키
                        use_container_width=True):
                with st.spinner("분석 중..."):
                    # 부서별 상세 데이터 가져오기
                    conn = get_db_connection()
                    dept_data = pd.read_sql("""
                        SELECT 
                            department,
                            COUNT(*) as count,
                            STRING_AGG(DISTINCT gender, ', ') as genders,
                            STRING_AGG(DISTINCT age_group, ', ') as age_groups,
                            STRING_AGG(DISTINCT education_level, ', ') as education_levels
                        FROM respondents 
                        WHERE file_id = %s
                        GROUP BY department
                    """, conn, params=[file_id])
                    
                    analysis = generate_department_analysis(dept_data, analysis_type[1])
                    if analysis:
                        save_analysis(file_id, analysis_type[0], analysis_type[1], analysis)
                        st.success("분석 완료!")
                        st.rerun()  # 페이지 새로고침
            
            # 저장 버튼
            if st.button("💾 저장",
                        key=f"btn_save_{key_prefix}_{file_id}",  # 저장 버튼도 고유 키
                        use_container_width=True):
                save_analysis(file_id, analysis_type[0], analysis_type[1], edited_text)
                st.success("저장 완료!") 
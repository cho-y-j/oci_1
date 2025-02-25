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

def get_category_from_survey_id(survey_id):
    # survey_id에서 카테고리 매핑
    category_mapping = {
        '인간적': '인간적-도움 (Humanistic-Helpful)',
        '친화적': '친화적 (Affiliative)',
        '승인': '승인 (Approval)',
        '전통적': '전통적 (Conventional)',
        '의존적': '의존적 (Dependent)',
        '회피적': '회피적 (Avoidance)',
        '반대적': '반대적 (Oppositional)',
        '권력': '권력 (Power)',
        '경쟁': '경쟁적 (Competitive)',
        '능력': '유능/완벽주의적 (Competence/Perfectionistic)',
        '성취': '성취 (Achievement)',
        '자아': '자기 실현적 (Self-Actualizing)'
    }
    
    for key in category_mapping:
        if key in survey_id:
            return category_mapping[key]
    return survey_id

def show_oci_analysis(file_id):
    st.title("OCI(조직문화) 분석")
    
    # 전체 통계 탭과 부서별 상세 분석 탭으로 구분
    tab1, tab2 = st.tabs(["전체 통계", "부서별 상세 분석"])
    
    with tab1:
        show_overall_statistics(file_id)
    
    with tab2:
        show_detailed_analysis(file_id)

def show_overall_statistics(file_id):
    st.subheader("OCI 문항 카테고리별 전체 통계")
    
    # 카테고리 목록 가져오기
    conn = get_db_connection()
    categories = pd.read_sql("""
        SELECT DISTINCT question_category 
        FROM oci_questions 
        ORDER BY question_category
    """, conn)
    
    # 탭으로 10가지 카테고리 표시
    tabs = st.tabs(categories['question_category'].tolist())
    
    for idx, tab in enumerate(tabs):
        with tab:
            show_category_response_distribution(file_id, categories['question_category'].iloc[idx])

def show_category_response_distribution(file_id, category):
    # 해당 카테고리의 응답 분포 데이터 가져오기
    conn = get_db_connection()
    df = pd.read_sql("""
        SELECT 
            q.question_category,
            q.survey_id,
            r.response,
            COUNT(*) as response_count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY q.survey_id), 1) as percentage
        FROM oci_responses r
        JOIN oci_questions q ON r.survey_id = q.survey_id
        WHERE r.file_id = %s AND q.question_category = %s
        GROUP BY q.question_category, q.survey_id, r.response
        ORDER BY q.survey_id, r.response
    """, conn, params=[file_id, category])
    
    # 응답 의미 매핑
    response_meanings = {
        1: '전혀 그렇지 않다',
        2: '그렇지 않다',
        3: '보통이다',
        4: '그렇다',
        5: '매우 그렇다'
    }
    
    # 1. 상단: 주요 통계
    avg_score = df.groupby('survey_id').apply(
        lambda x: (x['response'] * x['response_count']).sum() / x['response_count'].sum()
    ).mean()
    
    st.metric("카테고리 평균 점수", f"{avg_score:.2f}")
    
    # 2. 응답 분포 차트
    fig = go.Figure()
    
    # 각 응답 값별로 막대 추가 (색상 지정)
    colors = {
        1: '#FF9999',  # 빨간색 계열
        2: '#FFB366',  # 주황색 계열
        3: '#FFFF99',  # 노란색 계열
        4: '#99FF99',  # 초록색 계열
        5: '#99CCFF'   # 파란색 계열
    }
    
    for response in sorted(df['response'].unique()):
        response_data = df[df['response'] == response]
        meaning = response_meanings[response]
        
        fig.add_trace(go.Bar(
            name=f"{response}점 - {meaning}",
            x=response_data['survey_id'],
            y=response_data['percentage'],
            text=response_data['percentage'].apply(lambda x: f'{x:.1f}%'),
            textposition='auto',
            marker_color=colors[response]
        ))
    
    # 차트 레이아웃 설정
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
    
    # 3. 상세 데이터 테이블
    pivot_df = df.pivot_table(
        values='percentage',
        index='survey_id',
        columns='response',
        fill_value=0
    ).round(1)
    
    # 컬럼명에 응답 의미 추가
    pivot_df.columns = [f"{col}점 - {response_meanings[col]}" for col in pivot_df.columns]
    
    st.write("### 상세 응답 분포 (%)")
    st.dataframe(
        pivot_df.style.format("{:.1f}%"),
        use_container_width=True
    )

def show_detailed_analysis(file_id):
    # 기존의 부서별 상세 분석 코드...
    st.title("OCI(조직문화) 분석")
    
    # 카테고리 목록 가져오기
    conn = get_db_connection()
    categories = pd.read_sql("""
        SELECT DISTINCT question_category 
        FROM oci_questions 
        ORDER BY question_category  -- survey_id 대신 question_category로 변경
    """, conn)
    
    # 만약 특정 순서로 정렬하고 싶다면:
    category_order = [
        '인간적-도움 (Humanistic-Helpful)',
        '친화적 (Affiliative)',
        '승인 (Approval)',
        '전통적 (Conventional)',
        '의존적 (Dependent)',
        '회피적 (Avoidance)',
        '반대적 (Oppositional)',
        '권력 (Power)',
        '경쟁적 (Competitive)',
        '유능/완벽주의적 (Competence/Perfectionistic)',
        '성취 (Achievement)',
        '자기 실현적 (Self-Actualizing)'
    ]
    
    # 카테고리를 원하는 순서로 정렬
    categories['sort_order'] = categories['question_category'].map(
        {cat: i for i, cat in enumerate(category_order)}
    )
    categories = categories.sort_values('sort_order')
    
    # 탭 생성
    tabs = st.tabs(categories['question_category'].tolist())
    
    # 각 카테고리별 분석
    for idx, tab in enumerate(tabs):
        with tab:
            show_category_analysis(file_id, categories['question_category'].iloc[idx])

def show_category_analysis(file_id, category):
    """카테고리별 분석 표시"""
    conn = get_db_connection()
    df = pd.read_sql("""
        WITH avg_scores AS (
            SELECT 
                r.respondent_id,
                d.department,
                AVG(CAST(r.response AS FLOAT))::numeric as avg_score
            FROM oci_responses r
            JOIN respondents d ON r.respondent_id = d.respondent_id 
            JOIN oci_questions q ON r.survey_id = q.survey_id
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

    # 각 차트에 고유한 key 부여
    st.subheader(f"📊 {category} 분석")
    
    # 1. 막대 차트
    fig1 = px.bar(df, x='department', y='avg_score', 
                  title=f'{category} - 부서별 평균 점수')
    st.plotly_chart(fig1, use_container_width=True, 
                    key=f"oci_bar_{category}_{file_id}")

    # 2. 박스 플롯
    fig2 = px.box(df, x='department', y='avg_score',
                  title=f'{category} - 부서별 분포')
    st.plotly_chart(fig2, use_container_width=True, 
                    key=f"oci_box_{category}_{file_id}")

    # AI 분석 섹션
    show_ai_analysis(file_id, df, ("oci", category), f"oci_{category}")

def show_ai_analysis(file_id, df, analysis_type, key_prefix):
    """AI 분석 공통 컴포넌트"""
    with st.expander("📊 AI 분석"):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            analysis_text = load_existing_analysis(file_id, analysis_type[0], analysis_type[1])
            edited_text = st.text_area(
                "분석 내용",
                value=analysis_text if analysis_text else "",
                height=300,
                key=f"{key_prefix}_analysis"
            )
        
        with col2:
            st.write("")
            st.write("")
            if st.button("🤖 AI 분석 요청", key=f"request_{key_prefix}", use_container_width=True):
                try:
                    new_analysis = generate_oci_analysis(df, analysis_type[1])
                    st.session_state[f"{key_prefix}_analysis"] = new_analysis
                    save_analysis(file_id, analysis_type[0], analysis_type[1], new_analysis)
                    st.success("AI 분석이 완료되었습니다!")
                except Exception as e:
                    st.error(f"AI 분석 중 오류 발생: {str(e)}")
            
            st.write("")
            if st.button("💾 분석 저장", key=f"save_{key_prefix}", use_container_width=True):
                try:
                    save_analysis(file_id, analysis_type[0], analysis_type[1], edited_text)
                    st.success("분석 내용이 저장되었습니다!")
                except Exception as e:
                    st.error(f"저장 중 오류 발생: {str(e)}")

def show_oci_overall(file_id):
    st.subheader("OCI 전체 현황")
    
    # 기본 데이터 가져오기
    conn = get_db_connection()
    df = pd.read_sql("""
        SELECT 
            r.department,
            o.survey_id,
            o.question_text,
            o.response,
            COUNT(*) as count,
            ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY o.question_text), 1) as percentage
        FROM oci_results o
        JOIN respondents r ON o.respondent_id = r.respondent_id 
        WHERE o.file_id = %s
        GROUP BY r.department, o.survey_id, o.question_text, o.response
        ORDER BY o.survey_id, o.question_text, o.response
    """, conn, params=[file_id])
    
    # 파이썬에서 카테고리 매핑
    def get_category(survey_id):
        if '인간적' in survey_id: return '인간적-도움 (Humanistic-Helpful)'
        if '친화적' in survey_id: return '친화적 (Affiliative)'
        if '승인' in survey_id: return '승인 (Approval)'
        if '전통적' in survey_id: return '전통적 (Conventional)'
        if '의존적' in survey_id: return '의존적 (Dependent)'
        if '회피적' in survey_id: return '회피적 (Avoidance)'
        if '반대적' in survey_id: return '반대적 (Oppositional)'
        if '권력' in survey_id: return '권력 (Power)'
        if '경쟁' in survey_id: return '경쟁적 (Competitive)'
        if '능력' in survey_id: return '유능/완벽주의적 (Competence/Perfectionistic)'
        if '성취' in survey_id: return '성취 (Achievement)'
        if '자아' in survey_id: return '자기 실현적 (Self-Actualizing)'
        return survey_id
    
    df['question_category'] = df['survey_id'].apply(get_category)
    
    # 먼저 데이터 확인
    conn = get_db_connection()
    check_df = pd.read_sql("""
        SELECT DISTINCT survey_id, question_text, response 
        FROM oci_results 
        WHERE file_id = %s 
        LIMIT 5
    """, conn, params=[file_id])
    
    st.write("데이터 샘플:", check_df)
    
    # 실제 survey_id 패턴 확인
    survey_patterns = pd.read_sql("""
        SELECT DISTINCT survey_id 
        FROM oci_results 
        WHERE file_id = %s
    """, conn, params=[file_id])
    
    st.write("Survey ID 패턴:", survey_patterns)
    
    # 각 카테고리별 분석
    for category in df['question_category'].unique():
        st.markdown(f"### {category}")
        
        # 해당 카테고리 데이터
        cat_data = df[df['question_category'] == category]
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            # 응답 분포 테이블
            pivot_table = pd.pivot_table(
                cat_data,
                index=['question_text'],
                columns=['response'],
                values=['percentage'],
                fill_value=0
            ).round(1)
            
            st.dataframe(
                pivot_table.style.format('{:.1f}%'),
                use_container_width=True
            )
            
            save_to_powerbi_table(file_id, f"oci_{category.lower()}_distribution", cat_data)
        
        with col2:
            # 1. 막대 차트
            fig1 = px.bar(
                cat_data,
                x='question_text',
                y='count',
                color='response',
                title=f'{category} - 응답 분포',
                barmode='group'
            )
            st.plotly_chart(fig1, use_container_width=True, key=f"bar_chart_{category}")
            
            # 2. 100% 스택 차트
            fig2 = px.bar(
                cat_data,
                x='question_text',
                y='percentage',
                color='response',
                title=f'{category} - 응답 비율',
                barmode='stack'
            )
            fig2.update_traces(texttemplate='%{y:.1f}%')
            st.plotly_chart(fig2, use_container_width=True, key=f"stack_chart_{category}")
            
            # 3. 누적 분포 차트
            fig3 = px.line(
                cat_data,
                x='question_text',
                y='cumulative_pct',
                title=f'{category} - 누적 분포'
            )
            st.plotly_chart(fig3, use_container_width=True, key=f"line_chart_{category}")
        
        # AI 분석 섹션
        st.markdown("---")
        st.markdown("📊 AI 분석")
        
        # 기존 분석 불러오기
        analysis_text = load_existing_analysis(file_id, "oci", f"category_{category}")
        
        # 편집 가능한 텍스트 영역
        edited_text = st.text_area(
            "분석 내용",
            value=analysis_text if analysis_text else "",
            height=200,
            key=f"oci_{category}_analysis"
        )
        
        # AI 분석 요청과 저장 버튼
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("AI 분석 요청", key=f"request_oci_{category}_analysis"):
                analysis_text = generate_oci_analysis(cat_data, f"OCI {category} 분석")
                st.session_state[f"oci_{category}_analysis"] = analysis_text
                st.experimental_rerun()
        
        with col2:
            if st.button("분석 저장", key=f"save_oci_{category}_analysis"):
                save_analysis(file_id, "oci", f"category_{category}", edited_text)
                save_analysis_state(file_id, f"oci_{category}_analysis",
                                  data=cat_data,
                                  visualization=[fig1, fig2, fig3],
                                  analysis_text=edited_text)
                st.success("분석 내용이 저장되었습니다!")

def show_oci_by_department(file_id):
    st.subheader("OCI 부서별 분석")
    
    # 데이터 가져오기
    conn = get_db_connection()
    df = pd.read_sql("""
        SELECT 
            r.department,
            o.question_category,
            ROUND(AVG(CAST(o.response AS FLOAT)), 2) as avg_score,
            COUNT(DISTINCT r.respondent_id) as respondent_count
        FROM oci_results o
        JOIN respondents r ON o.respondent_id = r.respondent_id 
        WHERE o.file_id = %s
        GROUP BY r.department, o.question_category
        ORDER BY r.department, o.question_category
    """, conn, params=[file_id])
    
    # 1. 데이터 테이블 (좌측)
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("데이터 테이블")
        # 피벗 테이블 생성
        pivot_df = df.pivot(
            index='department',
            columns='question_category',
            values='avg_score'
        ).round(2)
        
        st.dataframe(
            pivot_df.style.format("{:.2f}"),
            use_container_width=True
        )
        
        save_to_powerbi_table(file_id, "oci_department_scores", df)
    
    # 2. 시각화 (우측)
    with col2:
        st.subheader("시각화")
        
        # 1) 막대 차트
        fig1 = px.bar(
            df,
            x='department',
            y='avg_score',
            color='question_category',
            title='부서별 OCI 평균 점수',
            barmode='group'
        )
        fig1.update_layout(
            xaxis_title="부서",
            yaxis_title="평균 점수",
            legend_title="카테고리"
        )
        st.plotly_chart(fig1, use_container_width=True)
        
        # 2) 레이더 차트
        fig2 = px.line_polar(
            df,
            r='avg_score',
            theta='question_category',
            color='department',
            line_close=True,
            title='부서별 OCI 프로파일'
        )
        fig2.update_traces(fill='toself')
        st.plotly_chart(fig2, use_container_width=True)
    
    # 3. AI 분석 섹션
    st.markdown("---")
    st.markdown("📊 AI 분석")
    
    # 기존 분석 불러오기
    analysis_text = load_existing_analysis(file_id, "oci", "department_analysis")
    
    # 편집 가능한 텍스트 영역
    edited_text = st.text_area(
        "분석 내용",
        value=analysis_text if analysis_text else "",
        height=200,
        key="oci_dept_analysis"
    )
    
    # AI 분석 요청과 저장 버튼
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("AI 분석 요청", key="request_oci_dept_analysis"):
            analysis_text = generate_department_analysis(df, "OCI 부서별 분석")
            st.session_state["oci_dept_analysis"] = analysis_text
            st.experimental_rerun()
    
    with col2:
        if st.button("분석 저장", key="save_oci_dept_analysis"):
            save_analysis(file_id, "oci", "department_analysis", edited_text)
            save_analysis_state(file_id, "oci_department_analysis",
                              data=df,
                              visualization=[fig1, fig2],
                              analysis_text=edited_text)
            st.success("분석 내용이 저장되었습니다!")

def show_oci_by_question(file_id):
    st.info("OCI 문항별 분석 -")
    # TODO: 구현 예정 

def generate_oci_analysis(df, category):
    """OCI 분석 결과 생성"""
    try:
        avg_score = df['avg_score'].mean()
        max_dept = df.iloc[0]['department']
        min_dept = df.iloc[-1]['department']
        
        analysis = f"""
        {category} 분석 결과:
        
        1. 전체 평균: {avg_score:.2f}점
        2. 최고 점수 부서: {max_dept} ({df.iloc[0]['avg_score']:.2f}점)
        3. 최저 점수 부서: {min_dept} ({df.iloc[-1]['avg_score']:.2f}점)
        4. 부서간 편차: {df['std_score'].mean():.2f}점
        
        주요 특징:
        - 부서별 점수 차이가 {df['avg_score'].max() - df['avg_score'].min():.2f}점으로 나타남
        - 전체 응답자의 {(df['avg_score'] > 3).mean() * 100:.1f}%가 평균 이상의 점수를 보임
        """
        return analysis
    except Exception as e:
        return f"분석 중 오류 발생: {str(e)}" 
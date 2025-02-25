import streamlit as st
from frontend.database import (
    get_db_connection,
    save_analysis,
    load_existing_analysis,  # 추가
    save_analysis_state
)
from frontend.pages.respondent_analysis import (
    show_basic_status,
    show_department_distribution,
    show_gender_distribution,
    show_age_distribution,
    show_education_distribution,
    show_certification_distribution  # experience_distribution 대신 certification_distribution으로 변경
)
from frontend.pages.oci_analysis import show_oci_analysis
from frontend.pages.cgs_analysis import show_cgs_analysis
import pandas as pd
from frontend.services.ai_analysis import (
    generate_department_analysis,
    generate_comprehensive_report  # 추가
)

def select_file():
    """파일 선택 함수"""
    conn = get_db_connection()
    
    # 업로드된 파일 목록 가져오기
    files_df = pd.read_sql("""
        SELECT 
            file_id,
            file_name,
            uploaded_at,
            status
        FROM uploaded_files
        WHERE status = 'completed'
        ORDER BY uploaded_at DESC
    """, conn)
    
    if files_df.empty:
        st.warning("처리된 파일이 없습니다. 먼저 파일을 업로드하고 처리해주세요.")
        return None
    
    # 파일 선택 옵션 만들기
    file_options = files_df.apply(
        lambda x: f"{x['file_name']} (업로드: {x['uploaded_at'].strftime('%Y-%m-%d %H:%M')})", 
        axis=1
    ).tolist()
    
    selected = st.selectbox(
        "분석할 파일 선택",
        options=file_options,
        index=0 if file_options else None
    )
    
    if selected:
        # 선택된 파일의 ID 반환 (int로 변환)
        selected_idx = file_options.index(selected)
        return int(files_df.iloc[selected_idx]['file_id'])  # int로 명시적 변환
    
    return None

def show_analysis_dashboard():
    st.title("분석 대시보드")
    
    # 파일 선택
    file_id = select_file()
    if not file_id:
        st.warning("분석할 파일을 선택해주세요.")
        return
    
    # 탭 구성
    tab1, tab2, tab3, tab4 = st.tabs([
        "응답자 분석", 
        "OCI 분석", 
        "CGS 분석",
        "AI 종합분석 리포트"
    ])
    
    with tab1:
        show_basic_status(file_id)
    with tab2:
        show_oci_analysis(file_id)
    with tab3:
        show_cgs_analysis(file_id)
    with tab4:
        show_comprehensive_report(file_id)

def show_comprehensive_report(file_id):
    st.subheader("AI 종합분석 리포트")
    
    # 분석 결과 확인
    conn = get_db_connection()
    analysis_count = pd.read_sql("""
        SELECT COUNT(*) as count 
        FROM analysis_results 
        WHERE file_id = %s AND analysis_text IS NOT NULL
    """, conn, params=[file_id]).iloc[0]['count']
    
    if analysis_count < 5:  # 최소 5개의 분석이 필요하다고 가정
        st.warning("분석 저장이 마무리되지 않았습니다. 각 분석 탭에서 AI 분석을 완료해주세요.")
        return
    
    # 분석 요청사항 입력
    analysis_request = st.text_area(
        "분석 요청사항 (선택사항)",
        placeholder="특별히 분석이 필요한 부분이나 중점적으로 살펴볼 내용을 입력해주세요.",
        height=100
    )
    
    # 기존 분석 불러오기
    existing_analysis = load_existing_analysis(file_id, "comprehensive", "report")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # 분석 내용 표시/편집 영역
        edited_text = st.text_area(
            "종합 분석 내용",
            value=existing_analysis if existing_analysis else "",
            height=500,
            key="comprehensive_analysis"
        )
    
    with col2:
        st.write("")
        st.write("")
        # AI 분석 요청 버튼
        if st.button("🤖 AI 분석 요청", use_container_width=True):
            with st.spinner("AI가 분석을 진행중입니다..."):
                analysis_text = generate_comprehensive_report(
                    file_id=file_id, 
                    requirements=analysis_request if analysis_request else None
                )
                st.session_state["comprehensive_analysis"] = analysis_text
                st.success("분석이 완료되었습니다!")
                st.experimental_rerun()
        
        st.write("")
        # 분석 저장 버튼
        if st.button("💾 분석 저장", use_container_width=True):
            save_analysis(file_id, "comprehensive", "report", edited_text)
            st.success("분석 내용이 저장되었습니다!")
        
        st.write("")
        # 다운로드 버튼
        if edited_text:
            st.download_button(
                label="📥 리포트 다운로드",
                data=edited_text.encode('utf-8'),
                file_name=f"AI_종합분석리포트_{file_id}.txt",
                mime="text/plain",
                use_container_width=True
            )

def show_department_analysis(file_id):
    # 상단 분석 항목 선택
    analysis_items = [
        "부서별 분포도",  # 첫 번째 항목으로 설정
        "성별 분포", 
        "연령대 분포",
        "학력 분포",
        "전공 분포",
        "경력 분포",
        "부서별 OCI 평균",
        "부서별 CGS 평균"
    ]
    selected_item = st.selectbox("분석 항목", analysis_items)
    
    # 2단 레이아웃
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # 데이터 테이블과 차트
        if selected_item == "부서별 분포도":
            show_department_distribution(file_id)
        elif selected_item == "성별 분포":
            show_gender_distribution(file_id)
        # ... 다른 분석 항목들
    
    with col2:
        # AI 분석 요약
        st.subheader("AI 분석 요약")
        show_ai_analysis(file_id, "department", selected_item)

def show_ai_analysis(file_id, analysis_type, item):
    # 기존 분석 가져오기
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT analysis_text 
        FROM analysis_results 
        WHERE file_id = %s AND analysis_type = %s AND analysis_item = %s
    """, (file_id, analysis_type, item))
    
    result = cur.fetchone()
    existing_analysis = result[0] if result else ""
    
    # 편집 가능한 분석 텍스트
    edited_analysis = st.text_area(
        "",
        value=existing_analysis,
        height=400,
        placeholder="AI 분석 결과나 수동 분석 내용을 입력하세요."
    )
    
    # 저장 버튼
    if st.button("분석 내용 저장", use_container_width=True):
        save_analysis(file_id, analysis_type, item, edited_analysis)
        st.success("분석 내용이 저장되었습니다.")

def save_to_powerbi_table(file_id, table_name, df):
    """PowerBI용 테이블 저장"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 테이블 생성 (없는 경우)
    create_powerbi_table(cur, table_name, df)
    
    # 데이터 저장
    for _, row in df.iterrows():
        columns = ", ".join(df.columns)
        placeholders = ", ".join(["%s"] * len(df.columns))
        
        cur.execute(f"""
            INSERT INTO powerbi_{table_name} (file_id, {columns})
            VALUES (%s, {placeholders})
            ON CONFLICT (file_id, department, gender) 
            DO UPDATE SET 
                count = EXCLUDED.count,
                percentage = EXCLUDED.percentage
        """, (file_id, *row))
    
    conn.commit()
    cur.close()
    conn.close()

def create_powerbi_table(cur, table_name, df):
    """PowerBI용 테이블 생성"""
    columns = ", ".join([
        f"{col} {get_sql_type(df[col])}"
        for col in df.columns
    ])
    
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS powerbi_{table_name} (
            id SERIAL PRIMARY KEY,
            file_id INTEGER REFERENCES uploaded_files(file_id),
            {columns},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(file_id, department, gender)
        )
    """)

def get_sql_type(series):
    """pandas 데이터타입을 PostgreSQL 타입으로 변환"""
    dtype = series.dtype
    if dtype == 'int64':
        return 'INTEGER'
    elif dtype == 'float64':
        return 'DECIMAL(10,2)'
    else:
        return 'VARCHAR(100)'

def save_analysis(file_id, analysis_type, item, analysis_text):
    """분석 결과 저장"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO analysis_results 
            (file_id, analysis_type, analysis_item, analysis_text, created_at)
        VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (file_id, analysis_type, analysis_item)
        DO UPDATE SET 
            analysis_text = EXCLUDED.analysis_text,
            updated_at = CURRENT_TIMESTAMP
    """, (file_id, analysis_type, item, analysis_text))
    
    conn.commit()
    cur.close()
    conn.close() 
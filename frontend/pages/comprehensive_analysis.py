import streamlit as st
import pandas as pd
from frontend.database import get_db_connection, save_analysis_for_powerbi
from frontend.services.ai_analysis import generate_comprehensive_report

def show_comprehensive_analysis(file_id=None):
    st.title("🤖 AI 종합분석 리포트")
    
    conn = get_db_connection()
    
    # 파일 목록 가져오기
    files = pd.read_sql("""
        SELECT file_id, file_name, uploaded_at 
        FROM uploaded_files 
        ORDER BY uploaded_at DESC
    """, conn)
    
    # 파일 선택
    selected = st.selectbox(
        "분석할 파일 선택",
        options=files['file_id'].tolist(),
        format_func=lambda x: files[files['file_id'] == x]['file_name'].iloc[0],
        index=files[files['file_id'] == file_id].index[0] if file_id in files['file_id'].values else 0
    )
    
    if selected:
        # 기존 분석 결과 가져오기
        existing_analysis = pd.read_sql("""
            SELECT analysis_text, created_at 
            FROM analysis_results 
            WHERE file_id = %s AND analysis_type = 'comprehensive'
            ORDER BY created_at DESC LIMIT 1
        """, conn, params=[selected])
        
        # 분석 요구사항 입력
        st.subheader("📝 분석 요구사항")
        requirements = st.text_area(
            "특별히 분석이 필요한 부분이나 중점적으로 살펴볼 내용을 입력해주세요.",
            placeholder="예시: 부서별 차이점 분석, 개선이 시급한 영역 도출, 세대 간 인식 차이 등",
            height=100
        )
        
        # 분석 결과 표시 영역
        st.subheader("📊 분석 결과")
        analysis_text = st.text_area(
            "",
            value=existing_analysis.iloc[0]['analysis_text'] if not existing_analysis.empty else "",
            height=800,
            key="analysis_result"
        )
        
        col1, col2 = st.columns(2)
        
        # AI 분석 시작 버튼
        with col1:
            if st.button("🔍 AI 분석 시작", use_container_width=True):
                st.warning("이미 분석이 완료되었습니다. 다음 업데이트에서 AI 분석이 제공될 예정입니다.")
        
        # 저장 버튼
        with col2:
            if st.button("💾 수정사항 저장", use_container_width=True):
                cur = conn.cursor()
                cur.execute("""
                    INSERT INTO analysis_results 
                        (file_id, analysis_type, analysis_text, created_at)
                    VALUES 
                        (%s, 'comprehensive', %s, CURRENT_TIMESTAMP)
                """, (selected, analysis_text))
                conn.commit()
                cur.close()
                st.success("수정사항이 저장되었습니다!")
    
    conn.close() 
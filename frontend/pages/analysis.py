import streamlit as st
import psycopg2
from datetime import datetime
from frontend.services.ai_analysis import run_ai_analysis
from frontend.database import get_db_connection

def show_analysis_page():
    st.title("🤖 AI 리포터")
    
    # 데이터베이스 연결
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 파일 목록 가져오기
    cur.execute("""
        SELECT f.file_id, f.file_name, a.analysis_text, a.created_at 
        FROM uploaded_files f 
        LEFT JOIN ai_analysis a ON f.file_id = a.file_id 
        ORDER BY f.uploaded_at DESC
    """)
    files = cur.fetchall()
    
    if not files:
        st.info("분석할 파일이 없습니다.")
        return
        
    # 파일 선택
    file_options = [f"{f[0]} - {f[1]}" for f in files]
    selected_file = st.selectbox("분석할 파일 선택", file_options)
    
    if selected_file:
        file_id = int(selected_file.split(" - ")[0])
        existing_analysis = next((f[2] for f in files if f[0] == file_id), None)
        
        # AI 분석 요약 섹션
        st.markdown("### AI 분석 요약")
        edited_analysis = st.text_area(
            "",
            value=existing_analysis if existing_analysis else "아직 분석되지 않은 파일입니다.",
            height=500
        )
        
        # 수정 후 저장 버튼 (기존 분석이 있을 때만)
        if existing_analysis:
            if st.button("수정사항 저장", use_container_width=True):
                try:
                    cur.execute("""
                        UPDATE ai_analysis 
                        SET analysis_text = %s, updated_at = CURRENT_TIMESTAMP 
                        WHERE file_id = %s
                    """, (edited_analysis, file_id))
                    conn.commit()
                    st.success("수정사항이 저장되었습니다!")
                except Exception as e:
                    conn.rollback()
                    st.error(f"저장 중 오류 발생: {str(e)}")
        
        # 구분선
        st.markdown("---")
        
        # 새로운 분석 섹션
        st.markdown("### 새로운 AI 분석")
        
        # 추가 지시사항 입력
        additional_prompt = st.text_area(
            "추가 분석 지시사항 (선택사항)",
            placeholder="예: 부서별 차이점을 자세히 분석해주세요.",
            height=100
        )
        
        # AI 분석 실행 버튼
        if st.button("AI 분석 실행", use_container_width=True):
            with st.spinner("AI가 분석 중입니다..."):
                analysis = run_ai_analysis(file_id, additional_prompt)
                
                # 분석 결과 저장
                try:
                    cur.execute("""
                        INSERT INTO ai_analysis (file_id, analysis_text, created_at)
                        VALUES (%s, %s, CURRENT_TIMESTAMP)
                        ON CONFLICT (file_id) 
                        DO UPDATE SET analysis_text = EXCLUDED.analysis_text,
                                    updated_at = CURRENT_TIMESTAMP
                    """, (file_id, analysis))
                    conn.commit()
                    st.success("새로운 분석이 완료되었습니다!")
                    st.experimental_rerun()  # 페이지 새로고침
                except Exception as e:
                    conn.rollback()
                    st.error(f"저장 중 오류 발생: {str(e)}")
    
    # 연결 종료
    cur.close()
    conn.close() 
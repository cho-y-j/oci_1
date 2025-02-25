import streamlit as st
from frontend.database import get_db_connection

def get_file_list():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT file_id, file_name 
        FROM uploaded_files 
        ORDER BY uploaded_at DESC
    """)
    files = cur.fetchall()
    cur.close()
    conn.close()
    return files

def show_manage_page():
    st.title("📁 파일 관리 페이지")
    
    # 파일 목록 가져오기
    files = get_file_list()
    
    # 파일 선택
    selected_file = st.selectbox("파일 선택", files)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("상세 보기"):
            show_file_details(selected_file, max_rows=5)
    
    with col3:
        if st.button("파일 삭제"):
            delete_file(selected_file)

def show_file_details(selected_file, max_rows=5):
    file_id = selected_file[0]
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 기초분석 데이터
    st.subheader("기초분석 데이터")
    cur.execute("SELECT * FROM respondents WHERE file_id = %s LIMIT %s", (file_id, max_rows))
    st.dataframe(cur.fetchall())
    
    # OCI 데이터
    st.subheader("OCI 데이터")
    cur.execute("SELECT * FROM oci_responses WHERE file_id = %s LIMIT %s", (file_id, max_rows))
    st.dataframe(cur.fetchall())
    
    # CGS 데이터
    st.subheader("CGS 데이터")
    cur.execute("SELECT * FROM cgs_responses WHERE file_id = %s LIMIT %s", (file_id, max_rows))
    st.dataframe(cur.fetchall())
    
    cur.close()
    conn.close() 

def show_analysis_results(selected_file):
    file_id = selected_file[0]
    conn = get_db_connection()
    cur = conn.cursor()
    
    # AI 분석 결과 가져오기
    cur.execute("""
        SELECT analysis_text, created_at 
        FROM ai_analysis 
        WHERE file_id = %s 
        ORDER BY created_at DESC
    """, (file_id,))
    
    result = cur.fetchone()
    if result:
        st.subheader("AI 분석 결과")
        st.write(f"분석 시간: {result[1]}")
        st.write(result[0])
    else:
        st.info("아직 분석되지 않은 파일입니다.")
    
    cur.close()
    conn.close() 

def delete_file(selected_file):
    file_id = selected_file[0]
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # CASCADE 설정으로 인해 관련된 모든 데이터가 함께 삭제됨
        cur.execute("DELETE FROM uploaded_files WHERE file_id = %s", (file_id,))
        conn.commit()
        st.success("파일이 삭제되었습니다.")
    except Exception as e:
        conn.rollback()
        st.error(f"삭제 중 오류 발생: {str(e)}")
    finally:
        cur.close()
        conn.close() 
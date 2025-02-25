import openai
import streamlit as st
from ..database import get_db_connection


openai.api_key = st.secrets["OPENAI_API_KEY"]


def get_basic_data(file_id, conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM respondents 
        WHERE file_id = %s
    """, (file_id,))
    return cur.fetchall()

def get_oci_data(file_id, conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM oci_results 
        WHERE file_id = %s
    """, (file_id,))
    return cur.fetchall()

def get_cgs_data(file_id, conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM cgs_results 
        WHERE file_id = %s
    """, (file_id,))
    return cur.fetchall()

def run_ai_analysis(file_id, additional_prompt=""):
    try:
        conn = get_db_connection()
        basic_data = get_basic_data(file_id, conn)
        oci_data = get_oci_data(file_id, conn)
        cgs_data = get_cgs_data(file_id, conn)
        
        # AI 분석 프롬프트
        prompt = f"""
        너는 최고의 설문 데이터 분석가입니다.
        다음 데이터를 분석하여 주요 발견사항과 시사점을 도출해주세요:
        데이터간 응답자 respondent_id 로 연결하여 3자지로 구분하여 질문결과를 받았으며 기초분석 데이터를 중심으로 oci 분석과 cgs 분석방식으로 분석하여 결과를 도출해주세요.
        1. 기초 분석 데이터:
        {basic_data}
        
        2. OCI 분석 데이터:
        {oci_data}
        
        3. CGS 분석 데이터:
        {cgs_data}
        """
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return response.choices[0].message.content 
    except Exception as e:
        print(f"Error in run_ai_analysis: {e}")
        return None 

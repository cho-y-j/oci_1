import streamlit as st
import pandas as pd
from frontend.database import get_db_connection

def show_analysis_history(file_id):
    st.subheader("분석 이력")
    
    # 분석 결과 조회
    conn = get_db_connection()
    results = pd.read_sql("""
        SELECT 
            analysis_type,
            category,
            analysis_text,
            created_at,
            metrics
        FROM analysis_results
        WHERE file_id = %s
        ORDER BY created_at DESC
    """, conn, params=[file_id])
    
    # 결과 표시
    st.dataframe(
        results.style.format({
            'created_at': lambda x: x.strftime('%Y-%m-%d %H:%M')
        }),
        use_container_width=True
    ) 
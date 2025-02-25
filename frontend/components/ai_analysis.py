import streamlit as st
from frontend.database import get_db_connection, save_analysis, load_existing_analysis
from frontend.services.ai_analysis import generate_department_analysis
import pandas as pd

def show_ai_analysis(file_id, df, analysis_type, key_prefix):
    """AI 분석 공통 컴포넌트"""
    with st.expander("📊 AI 분석"):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            existing = load_existing_analysis(file_id, analysis_type[0], analysis_type[1])
            text_key = f"analysis_{key_prefix}_{file_id}"
            
            edited_text = st.text_area(
                "분석 내용",
                value=existing if existing else "",
                height=300,
                key=text_key
            )
        
        with col2:
            if st.button("🤖 AI 분석", 
                        key=f"btn_analyze_{key_prefix}_{file_id}",
                        use_container_width=True):
                with st.spinner("분석 중..."):
                    # 분석 유형별 데이터 가져오기
                    conn = get_db_connection()
                    
                    if analysis_type[0] == "respondent":
                        if analysis_type[1] == "department":
                            query = """
                                SELECT 
                                    department,
                                    COUNT(*) as count,
                                    STRING_AGG(DISTINCT gender, ', ') as genders,
                                    STRING_AGG(DISTINCT age_group, ', ') as age_groups,
                                    STRING_AGG(DISTINCT education_level, ', ') as education_levels
                                FROM respondents 
                                WHERE file_id = %s
                                GROUP BY department
                            """
                        elif analysis_type[1] == "gender":
                            query = """
                                SELECT 
                                    gender,
                                    COUNT(*) as count,
                                    STRING_AGG(DISTINCT department, ', ') as departments,
                                    STRING_AGG(DISTINCT age_group, ', ') as age_groups
                                FROM respondents 
                                WHERE file_id = %s
                                GROUP BY gender
                            """
                        elif analysis_type[1] == "age":
                            query = """
                                SELECT 
                                    age_group,
                                    COUNT(*) as count,
                                    STRING_AGG(DISTINCT department, ', ') as departments,
                                    STRING_AGG(DISTINCT gender, ', ') as genders
                                FROM respondents 
                                WHERE file_id = %s
                                GROUP BY age_group
                            """
                        elif analysis_type[1] in ["education", "major"]:
                            query = """
                                SELECT 
                                    education_level,
                                    major,
                                    COUNT(*) as count,
                                    STRING_AGG(DISTINCT department, ', ') as departments
                                FROM respondents 
                                WHERE file_id = %s
                                GROUP BY education_level, major
                            """
                    elif analysis_type[0] == "oci":
                        query = """
                            SELECT 
                                r.department,
                                q.question_category,
                                AVG(CAST(r.response AS FLOAT))::numeric(10,2) as avg_score,
                                COUNT(*) as response_count
                            FROM oci_responses r
                            JOIN oci_questions q ON r.survey_id = q.survey_id
                            WHERE r.file_id = %s
                            GROUP BY r.department, q.question_category
                        """
                    elif analysis_type[0] == "cgs":
                        query = """
                            SELECT 
                                r.department,
                                q.question_category,
                                AVG(CAST(r.response AS FLOAT))::numeric(10,2) as avg_score,
                                COUNT(*) as response_count
                            FROM cgs_responses r
                            JOIN cgs_questions q ON r.survey_id = q.survey_id
                            WHERE r.file_id = %s
                            GROUP BY r.department, q.question_category
                        """
                    
                    analysis_data = pd.read_sql(query, conn, params=[file_id])
                    analysis = generate_department_analysis(analysis_data, analysis_type[1])
                    
                    if analysis:
                        save_analysis(file_id, analysis_type[0], analysis_type[1], analysis)
                        st.success("분석 완료!")
                        st.rerun()
            
            if st.button("💾 저장",
                        key=f"btn_save_{key_prefix}_{file_id}",
                        use_container_width=True):
                save_analysis(file_id, analysis_type[0], analysis_type[1], edited_text)
                st.success("저장 완료!") 
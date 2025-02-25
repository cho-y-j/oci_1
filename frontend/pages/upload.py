import streamlit as st
import pandas as pd
from frontend.database import get_db_connection

def show_upload_page():
    st.title("📂 파일 업로드 페이지")

    file_name_input = st.text_input("파일 이름을 입력하세요 (중복 방지)")
    uploaded_file = st.file_uploader("엑셀 파일을 업로드하세요 (xlsx)", type=["xlsx"])

    if uploaded_file and file_name_input:
        conn = get_db_connection()
        cur = conn.cursor()

        try:
            # uploaded_files 테이블에 등록
            cur.execute("""
                INSERT INTO uploaded_files (file_name, status)
                VALUES (%s, %s)
                RETURNING file_id;
            """, (file_name_input, "pending"))
            file_id = cur.fetchone()[0]
            
            # 엑셀 파일 처리
            xls = pd.ExcelFile(uploaded_file)
            
            with st.spinner("파일 처리 중..."):
                # 1. OCI_Q 시트 처리 (문항 정보)
                if "OCI_Q" in xls.sheet_names:
                    df_oci_q = xls.parse("OCI_Q")
                    for _, row in df_oci_q.iterrows():
                        cur.execute("""
                            INSERT INTO oci_questions (
                                survey_id, question_category, question_text
                            ) VALUES (%s, %s, %s)
                            ON CONFLICT (survey_id) DO UPDATE 
                            SET question_category = EXCLUDED.question_category,
                                question_text = EXCLUDED.question_text
                        """, (
                            row["survey_id"], 
                            row["question_category"],
                            row["question_text"]
                        ))
                    st.success("✅ OCI 문항 데이터 저장 완료")

                # 2. CGS_Q 시트 처리 (문항 정보)
                if "CGS_Q" in xls.sheet_names:
                    df_cgs_q = xls.parse("CGS_Q")
                    for _, row in df_cgs_q.iterrows():
                        cur.execute("""
                            INSERT INTO cgs_questions (
                                survey_id, question_category, question_text
                            ) VALUES (%s, %s, %s)
                            ON CONFLICT (survey_id) DO UPDATE 
                            SET question_category = EXCLUDED.question_category,
                                question_text = EXCLUDED.question_text
                        """, (
                            row["survey_id"], 
                            row["question_category"],
                            row["question_text"]
                        ))
                    st.success("✅ CGS 문항 데이터 저장 완료")

                # 3. Respondent 시트 처리 (응답자 정보)
                if "Respondent" in xls.sheet_names:
                    df = xls.parse("Respondent")
                    for _, row in df.iterrows():
                        cur.execute("""
                            INSERT INTO respondents (
                                respondent_id, file_id, department, gender, 
                                age_group, education_level, major, 
                                experience_innovation, experience_total,
                                certifications, programming_skills, comments
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        """, (
                            row["respondent_id"], file_id,
                            row["department"], row["gender"], row["age_group"],
                            row["education_level"], row["major"],
                            row["experience_innovation"], row["experience_total"],
                            row["certifications"], row["programming_skills"],
                            row["comments"]
                        ))
                    st.success("✅ 응답자 데이터 저장 완료")

                # 4. OCI_R 시트 처리 (응답 데이터)
                if "OCI_R" in xls.sheet_names:
                    df_oci_r = xls.parse("OCI_R")
                    for _, row in df_oci_r.iterrows():
                        cur.execute("""
                            INSERT INTO oci_responses (
                                file_id, respondent_id, survey_id,
                                response, response_meaning
                            ) VALUES (%s, %s, %s, %s, %s)
                        """, (
                            file_id, row["respondent_id"], 
                            row["survey_id"], row["response"],
                            row["response_meaning"]
                        ))
                    st.success("✅ OCI 응답 데이터 저장 완료")

                # 5. CGS_R 시트 처리 (응답 데이터)
                if "CGS_R" in xls.sheet_names:
                    df_cgs_r = xls.parse("CGS_R")
                    for _, row in df_cgs_r.iterrows():
                        cur.execute("""
                            INSERT INTO cgs_responses (
                                file_id, respondent_id, survey_id,
                                response, response_meaning
                            ) VALUES (%s, %s, %s, %s, %s)
                        """, (
                            file_id, row["respondent_id"], 
                            row["survey_id"], row["response"],
                            row["response_meaning"]
                        ))
                    st.success("✅ CGS 응답 데이터 저장 완료")

            # 상태 업데이트
            cur.execute("""
                UPDATE uploaded_files 
                SET status = 'completed' 
                WHERE file_id = %s
            """, (file_id,))
            
            conn.commit()
            st.success(f"✅ 파일 '{file_name_input}' 업로드 완료!")

        except Exception as e:
            conn.rollback()
            st.error(f"⚠️ 오류 발생: {str(e)}")
        
        finally:
            cur.close()
            conn.close()

    # 파일 목록 표시
    show_file_list()

def show_file_list():
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 간단한 쿼리로 변경
        cur.execute("""
            SELECT file_id, file_name, uploaded_at, status
            FROM uploaded_files
            WHERE uploaded_at > CURRENT_TIMESTAMP - INTERVAL '30 days'
            ORDER BY uploaded_at DESC
            LIMIT 20
        """)
        
        files = cur.fetchall()
        if files:
            df = pd.DataFrame(files, columns=['file_id', 'file_name', 'uploaded_at', 'status'])
            st.dataframe(
                df.style.format({
                    'uploaded_at': lambda x: x.strftime('%Y-%m-%d %H:%M')
                }),
                use_container_width=True
            )
        else:
            st.info("업로드된 파일이 없습니다.")
            
    finally:
        cur.close()
        conn.close()

def cleanup_old_data():
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 30일 이상 된 데이터 삭제
        cur.execute("""
            DELETE FROM uploaded_files 
            WHERE uploaded_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
            
            VACUUM FULL;
        """)
        conn.commit()
    except Exception as e:
        st.error(f"데이터 정리 중 오류: {str(e)}")
    finally:
        cur.close()
        conn.close() 
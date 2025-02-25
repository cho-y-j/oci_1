import psycopg2
import os
from dotenv import load_dotenv
import streamlit as st

load_dotenv()

def get_db_connection():
    try:
        # Streamlit Secrets에서 데이터베이스 URL 가져오기
        conn = psycopg2.connect(st.secrets["DATABASE_URL"])
        conn.set_session(autocommit=True)
        return conn
    except psycopg2.OperationalError as e:
        st.error(f"""
        Neon DB 연결 실패:
        1. Streamlit Secrets의 DATABASE_URL을 확인해주세요
        2. 네트워크 연결을 확인해주세요
        오류 메시지: {str(e)}
        """)
        return None
    except Exception as e:
        st.error(f"알 수 없는 오류: {str(e)}")
        return None

def init_database():
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 기본 테이블들 생성
        cur.execute("""
            -- 파일 업로드 테이블
            CREATE TABLE IF NOT EXISTS uploaded_files (
                file_id SERIAL PRIMARY KEY,
                file_name VARCHAR(200) UNIQUE NOT NULL,
                status VARCHAR(20),
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 응답자 정보 테이블
            CREATE TABLE IF NOT EXISTS respondents (
                respondent_id VARCHAR(50),
                file_id INTEGER REFERENCES uploaded_files(file_id) ON DELETE CASCADE,
                department VARCHAR(100),
                gender VARCHAR(20),
                age_group VARCHAR(20),
                education_level VARCHAR(50),
                major VARCHAR(100),
                experience_innovation VARCHAR(50),
                experience_total VARCHAR(50),
                certifications TEXT,
                programming_skills TEXT,
                comments TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (respondent_id, file_id)
            );

            -- OCI 설문 문항 테이블
            CREATE TABLE IF NOT EXISTS oci_questions (
                survey_id VARCHAR(50) PRIMARY KEY,
                question_category VARCHAR(100),
                question_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- CGS 설문 문항 테이블
            CREATE TABLE IF NOT EXISTS cgs_questions (
                survey_id VARCHAR(50) PRIMARY KEY,
                question_category VARCHAR(100),
                question_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- OCI 응답 테이블
            CREATE TABLE IF NOT EXISTS oci_responses (
                response_id SERIAL PRIMARY KEY,
                file_id INTEGER REFERENCES uploaded_files(file_id) ON DELETE CASCADE,
                respondent_id VARCHAR(50),
                survey_id VARCHAR(50) REFERENCES oci_questions(survey_id),
                response INTEGER,
                response_meaning VARCHAR(200),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- CGS 응답 테이블
            CREATE TABLE IF NOT EXISTS cgs_responses (
                response_id SERIAL PRIMARY KEY,
                file_id INTEGER REFERENCES uploaded_files(file_id) ON DELETE CASCADE,
                respondent_id VARCHAR(50),
                survey_id VARCHAR(50) REFERENCES cgs_questions(survey_id),
                response INTEGER,
                response_meaning VARCHAR(200),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- AI 분석 결과 테이블
            CREATE TABLE IF NOT EXISTS ai_analysis (
                analysis_id SERIAL PRIMARY KEY,
                file_id INTEGER REFERENCES uploaded_files(file_id) ON DELETE CASCADE,
                analysis_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                UNIQUE(file_id)
            );

            -- 분석 결과 저장 테이블
            CREATE TABLE IF NOT EXISTS analysis_results (
                result_id SERIAL PRIMARY KEY,
                file_id INTEGER REFERENCES uploaded_files(file_id) ON DELETE CASCADE,
                analysis_type VARCHAR(50),
                analysis_item VARCHAR(100),
                analysis_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP,
                UNIQUE(file_id, analysis_type, analysis_item)
            );
        """)

        conn.commit()
        print("✅ Database tables created successfully")
        
    except Exception as e:
        print(f"❌ Database initialization error: {str(e)}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def save_to_powerbi_table(file_id, analysis_type, data, visualization=None):
    """PowerBI 연동용 데이터 저장"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO powerbi_data (
                file_id,
                analysis_type,
                data_snapshot,
                visualization_config,
                updated_at
            ) VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (file_id, analysis_type) 
            DO UPDATE SET 
                data_snapshot = EXCLUDED.data_snapshot,
                visualization_config = EXCLUDED.visualization_config,
                updated_at = CURRENT_TIMESTAMP
        """, (file_id, analysis_type, data.to_json(), 
              visualization.to_json() if visualization else None))
        
        conn.commit()
    except Exception as e:
        print(f"PowerBI 데이터 저장 중 오류: {str(e)}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def save_analysis_state(file_id, analysis_type, data, visualization, analysis_text):
    """분석 상태 전체 저장 (RAG용)"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO analysis_states (
            file_id, analysis_type, data_snapshot, 
            visualization_config, analysis_text, created_at
        ) VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (file_id, analysis_type) 
        DO UPDATE SET 
            data_snapshot = EXCLUDED.data_snapshot,
            visualization_config = EXCLUDED.visualization_config,
            analysis_text = EXCLUDED.analysis_text,
            updated_at = CURRENT_TIMESTAMP
    """, (file_id, analysis_type, data.to_json(), 
          visualization.to_json(), analysis_text))
    
    conn.commit()
    cur.close()
    conn.close()

def load_existing_analysis(file_id, analysis_type, item):
    """저장된 분석 내용 불러오기"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT analysis_text 
        FROM analysis_results 
        WHERE file_id = %s AND analysis_type = %s AND analysis_item = %s
    """, (file_id, analysis_type, item))
    
    result = cur.fetchone()
    cur.close()
    conn.close()
    
    return result[0] if result else ""

def save_analysis(file_id, analysis_type, item, analysis_text):
    """분석 내용 저장"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        INSERT INTO analysis_results 
            (file_id, analysis_type, analysis_item, analysis_text)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (file_id, analysis_type, analysis_item)
        DO UPDATE SET 
            analysis_text = EXCLUDED.analysis_text,
            updated_at = CURRENT_TIMESTAMP
    """, (file_id, analysis_type, item, analysis_text))
    
    conn.commit()
    cur.close()
    conn.close()

def create_powerbi_table(cur, table_name, columns):
    """PowerBI용 테이블 생성"""
    # 컬럼 타입 매핑
    type_mapping = {
        'department': 'VARCHAR(100)',
        'gender': 'VARCHAR(20)',
        'age_group': 'VARCHAR(20)',
        'education': 'VARCHAR(50)',
        'major': 'VARCHAR(100)',
        'count': 'INTEGER',
        'percentage': 'DECIMAL(5,1)'
    }
    
    # 컬럼 정의 생성
    column_definitions = []
    for col in columns:
        col_type = type_mapping.get(col, 'VARCHAR(100)')
        column_definitions.append(f"{col} {col_type}")
    
    # 테이블 생성 쿼리
    create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS powerbi_{table_name} (
            id SERIAL PRIMARY KEY,
            file_id INTEGER REFERENCES uploaded_files(file_id),
            {', '.join(column_definitions)},
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """
    
    cur.execute(create_table_sql)

def maintain_database():
    """주기적인 데이터베이스 관리"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 오래된 데이터 삭제
        cur.execute("""
            DELETE FROM uploaded_files 
            WHERE uploaded_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
        """)
        
        # 분석 결과 정리
        cur.execute("""
            DELETE FROM analysis_results 
            WHERE created_at < CURRENT_TIMESTAMP - INTERVAL '30 days';
        """)
        
        # 데이터베이스 정리
        cur.execute("VACUUM FULL ANALYZE;")
        
        conn.commit()
        print("Database maintenance completed")
        
    except Exception as e:
        print(f"Database maintenance error: {str(e)}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def create_powerbi_tables():
    """PowerBI 연동용 테이블 생성"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # 1. 응답자 분석 결과 테이블
        cur.execute("""
            CREATE TABLE IF NOT EXISTS powerbi_respondent_analysis (
                id SERIAL PRIMARY KEY,
                file_id INTEGER REFERENCES uploaded_files(file_id),
                analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                department VARCHAR(100),
                total_count INTEGER,
                gender_ratio JSONB,
                age_distribution JSONB,
                education_stats JSONB,
                major_distribution JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. OCI 분석 결과 테이블
        cur.execute("""
            CREATE TABLE IF NOT EXISTS powerbi_oci_analysis (
                id SERIAL PRIMARY KEY,
                file_id INTEGER REFERENCES uploaded_files(file_id),
                analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                department VARCHAR(100),
                question_category VARCHAR(100),
                avg_score DECIMAL(5,2),
                response_count INTEGER,
                score_distribution JSONB,
                comparison_stats JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 3. CGS 분석 결과 테이블
        cur.execute("""
            CREATE TABLE IF NOT EXISTS powerbi_cgs_analysis (
                id SERIAL PRIMARY KEY,
                file_id INTEGER REFERENCES uploaded_files(file_id),
                analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                department VARCHAR(100),
                question_category VARCHAR(100),
                avg_score DECIMAL(5,2),
                response_count INTEGER,
                score_distribution JSONB,
                improvement_areas JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 4. 종합 분석 결과 테이블
        cur.execute("""
            CREATE TABLE IF NOT EXISTS powerbi_comprehensive_analysis (
                id SERIAL PRIMARY KEY,
                file_id INTEGER REFERENCES uploaded_files(file_id),
                analysis_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                analysis_type VARCHAR(50),
                category VARCHAR(100),
                metrics JSONB,
                insights JSONB,
                recommendations JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        print("✅ PowerBI 테이블 생성 완료")
        
    except Exception as e:
        print(f"❌ PowerBI 테이블 생성 오류: {str(e)}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def save_analysis_for_powerbi(file_id, analysis_type, data):
    """분석 결과를 PowerBI용 테이블에 저장"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        if analysis_type == 'respondent':
            cur.execute("""
                INSERT INTO powerbi_respondent_analysis 
                (file_id, department, total_count, gender_ratio, age_distribution, 
                 education_stats, major_distribution)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (file_id, data['department'], data['total_count'], 
                  data['gender_ratio'], data['age_distribution'],
                  data['education_stats'], data['major_distribution']))
                  
        elif analysis_type == 'oci':
            cur.execute("""
                INSERT INTO powerbi_oci_analysis 
                (file_id, department, question_category, avg_score, 
                 response_count, score_distribution, comparison_stats)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (file_id, data['department'], data['category'], 
                  data['avg_score'], data['count'], data['distribution'],
                  data['comparison']))
                  
        elif analysis_type == 'cgs':
            cur.execute("""
                INSERT INTO powerbi_cgs_analysis 
                (file_id, department, question_category, avg_score,
                 response_count, score_distribution, improvement_areas)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (file_id, data['department'], data['category'],
                  data['avg_score'], data['count'], data['distribution'],
                  data['improvements']))

        conn.commit()
        print(f"✅ {analysis_type} 분석 결과 저장 완료")
        
    except Exception as e:
        print(f"❌ 저장 오류: {str(e)}")
        conn.rollback()
    finally:
        cur.close()
        conn.close() 
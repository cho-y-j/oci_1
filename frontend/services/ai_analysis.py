from openai import OpenAI
import os
from dotenv import load_dotenv
import streamlit as st
from frontend.database import get_db_connection
import pandas as pd

load_dotenv()

# OpenAI client 초기화
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def run_ai_analysis(file_id, additional_prompt=""):
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # 1. 기초 분석 - 부서별 종합 통계
        cur.execute("""
            SELECT 
                department,
                COUNT(*) as count,
                STRING_AGG(DISTINCT gender, ', ') as genders,
                STRING_AGG(DISTINCT age_group, ', ') as age_groups,
                STRING_AGG(DISTINCT education, ', ') as education_levels,
                STRING_AGG(DISTINCT major, ', ') as majors,
                STRING_AGG(DISTINCT experience_total, ', ') as exp_ranges
            FROM respondents 
            WHERE file_id = %s
            GROUP BY department
            ORDER BY count DESC
            LIMIT 8  -- 주요 부서 8개
        """, (file_id,))
        basic_data = cur.fetchall()

        # 2. OCI 분석 - 상위/하위 점수 모두 포함
        cur.execute("""
            WITH dept_scores AS (
                SELECT 
                    r.department,
                    o.question_text,
                    CAST(AVG(CAST(o.response AS FLOAT)) AS DECIMAL(10,2)) as avg_score
                FROM oci_results o
                JOIN respondents r ON o.respondent_id = r.respondent_id 
                WHERE o.file_id = %s
                GROUP BY r.department, o.question_text
            ),
            total_scores AS (
                SELECT 
                    question_text,
                    CAST(AVG(CAST(response AS FLOAT)) AS DECIMAL(10,2)) as total_avg
                FROM oci_results
                WHERE file_id = %s
                GROUP BY question_text
            )
            SELECT 
                d.department,
                d.question_text,
                d.avg_score,
                t.total_avg
            FROM dept_scores d
            JOIN total_scores t ON d.question_text = t.question_text
            WHERE d.avg_score >= 4.0 OR d.avg_score <= 2.0  -- 높은/낮은 점수 모두 포함
            ORDER BY d.department, d.avg_score DESC
            LIMIT 20
        """, (file_id, file_id))
        oci_data = cur.fetchall()

        # 3. CGS 분석 - 부서별 특징적인 응답
        cur.execute("""
            WITH dept_scores AS (
                SELECT 
                    r.department,
                    c.question_text,
                    CAST(AVG(CAST(c.response AS FLOAT)) AS DECIMAL(10,2)) as avg_score,
                    COUNT(*) as response_count
                FROM cgs_results c
                JOIN respondents r ON c.respondent_id = r.respondent_id 
                WHERE c.file_id = %s
                GROUP BY r.department, c.question_text
                HAVING COUNT(*) >= 3  -- 최소 3명 이상 응답
            )
            SELECT *
            FROM dept_scores
            WHERE avg_score >= 4.0 OR avg_score <= 2.0  -- 특징적인 응답만
            ORDER BY department, avg_score DESC
            LIMIT 20
        """, (file_id,))
        cgs_data = cur.fetchall()

        # 4. 분석 프롬프트 생성
        prompt = f"""
        당신은 조직 문화와 거버넌스 분석 전문가입니다. 다음 설문 데이터를 종합적으로 분석해주세요:

        1. 부서별 응답자 특성:
        {basic_data}

        2. OCI(조직문화) 주요 특징:
        - 부서별 높은/낮은 점수 항목
        {oci_data}

        3. CGS(거버넌스) 특징:
        - 부서별 특징적 응답
        {cgs_data}

        추가 고려사항: {additional_prompt[:100] if additional_prompt else "없음"}

        다음 형식으로 분석해주세요:
        1. 응답자 구성 특성
           - 부서별 인원 분포
           - 주요 인구통계학적 특징

        2. 조직문화(OCI) 분석
           - 전반적인 조직문화 특성
           - 부서별 문화 차이점
           - 개선이 필요한 영역

        3. 거버넌스(CGS) 분석
           - 주요 강점과 약점
           - 부서별 특징적 차이
           - 개선 제안사항

        4. 종합 제언
           - 핵심 발견사항
           - 우선순위별 개선과제
           - 실행 방안
        """

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "조직 진단 전문가입니다. 데이터에 기반한 실용적이고 구체적인 인사이트를 제공합니다."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        analysis_result = response.choices[0].message.content
        
        # 결과 저장
        cur.execute("""
            INSERT INTO ai_analysis (file_id, analysis_text, created_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (file_id) 
            DO UPDATE SET analysis_text = EXCLUDED.analysis_text,
                         updated_at = CURRENT_TIMESTAMP
        """, (file_id, analysis_result))
        
        conn.commit()
        return analysis_result

    except Exception as e:
        print(f"Error in AI analysis: {str(e)}")
        return f"분석 중 오류 발생: {str(e)}"
    finally:
        cur.close()
        conn.close()

def analyze_part(part_name, data, client):
    """각 부분별 데이터 분석"""
    prompt = f"""
    다음은 {part_name} 데이터입니다:
    {data}

    이 데이터의 주요 특징과 시사점을 간단히 요약해주세요.
    """
    
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "데이터 분석 전문가입니다."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7,
        max_tokens=1000
    )
    
    return response.choices[0].message.content

def generate_department_analysis(df, analysis_type=""):
    try:
        # 기존 분석 데이터 가져오기 (RAG 활용)
        previous_analyses = get_previous_analyses()
        
        # 데이터프레임을 문자열로 변환
        data_str = df.to_string()
        
        prompt = f"""
        다음은 {analysis_type} 데이터입니다:
        
        {data_str}
        
        참고할 이전 분석 내용:
        {previous_analyses}
        
        이 데이터를 분석하여 다음 사항을 포함하여 설명해주세요:
        1. 주요 특징과 패턴
        2. 눈에 띄는 점이나 특이사항
        3. 시사점이나 제안사항
        4. 이전 분석과 비교하여 달라진 점
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "데이터 분석 전문가입니다."},
                {"role": "user", "content": prompt}
            ]
        )
        
        analysis_text = response.choices[0].message.content
        
        # 분석 결과 저장 (RAG용)
        save_analysis_for_rag(analysis_type, analysis_text, df)
        
        return analysis_text
        
    except Exception as e:
        return f"AI 분석 중 오류가 발생했습니다: {str(e)}"

def get_previous_analyses():
    """이전 분석 데이터 가져오기"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        SELECT analysis_type, analysis_text, created_at
        FROM analysis_results
        ORDER BY created_at DESC
        LIMIT 5
    """)
    
    results = cur.fetchall()
    cur.close()
    conn.close()
    
    return "\n\n".join([f"{r[0]} ({r[2]}): {r[1]}" for r in results])

def save_analysis_for_rag(analysis_type, analysis_text, data):
    """분석 결과를 RAG용으로 저장"""
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO analysis_history (
                analysis_type,
                analysis_text,
                data_snapshot,
                created_at
            ) VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
        """, (analysis_type, analysis_text, data.to_json()))
        
        conn.commit()
    except Exception as e:
        print(f"RAG 저장 중 오류: {str(e)}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

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

def generate_comprehensive_report(file_id, requirements=None):
    """종합 분석 리포트 생성"""
    try:
        analysis_text = ""
        conn = get_db_connection()
        
        # 1. 응답자 분석
        respondent_summary = pd.read_sql("""
            SELECT 
                department,
                COUNT(*) as count,
                array_agg(DISTINCT gender) as genders,
                array_agg(DISTINCT age_group) as age_groups
            FROM respondents 
            WHERE file_id = %s
            GROUP BY department
        """, conn, params=[file_id])
        
        # 2. OCI 분석
        oci_summary = pd.read_sql("""
            SELECT 
                department,
                question_category,
                AVG(CAST(response AS FLOAT))::numeric(10,2) as avg_score,
                COUNT(*) as response_count
            FROM oci_responses 
            WHERE file_id = %s
            GROUP BY department, question_category
        """, conn, params=[file_id])
        
        # 3. CGS 분석
        cgs_summary = pd.read_sql("""
            SELECT 
                department,
                question_category,
                AVG(CAST(response AS FLOAT))::numeric(10,2) as avg_score,
                COUNT(*) as response_count
            FROM cgs_responses 
            WHERE file_id = %s
            GROUP BY department, question_category
        """, conn, params=[file_id])

        # 분석 텍스트 생성
        analysis_text = f"""
### 1. 응답자 분석
- 총 응답자 수: {respondent_summary['count'].sum()}명
- 부서 수: {len(respondent_summary)}개
- 부서별 특징:
"""
        for _, dept in respondent_summary.iterrows():
            analysis_text += f"  * {dept['department']}: {dept['count']}명\n"

        analysis_text += "\n### 2. OCI 분석\n"
        for dept in oci_summary['department'].unique():
            dept_data = oci_summary[oci_summary['department'] == dept]
            analysis_text += f"\n#### {dept}\n"
            for _, row in dept_data.iterrows():
                analysis_text += f"- {row['question_category']}: {row['avg_score']}점\n"

        analysis_text += "\n### 3. CGS 분석\n"
        for dept in cgs_summary['department'].unique():
            dept_data = cgs_summary[cgs_summary['department'] == dept]
            analysis_text += f"\n#### {dept}\n"
            for _, row in dept_data.iterrows():
                analysis_text += f"- {row['question_category']}: {row['avg_score']}점\n"

        if requirements:
            analysis_text += f"\n### 4. 요구사항 기반 분석\n{requirements}\n"

        conn.close()
        return analysis_text

    except Exception as e:
        st.error(f"분석 중 오류 발생: {str(e)}")
        return None 
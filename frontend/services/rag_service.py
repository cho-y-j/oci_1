def save_for_rag(file_id, analysis_type, category, analysis_text, data):
    """RAG 학습용 데이터 저장"""
    embedding = generate_embedding(analysis_text)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        cur.execute("""
            INSERT INTO rag_data (
                file_id, analysis_type, category, 
                analysis_text, embedding, context_data
            ) VALUES (%s, %s, %s, %s, %s, %s)
        """, (file_id, analysis_type, category, 
              analysis_text, embedding, json.dumps(data)))
        conn.commit()
    finally:
        cur.close()
        conn.close() 
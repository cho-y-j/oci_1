def show_visualization_dashboard(file_id):
    st.title("데이터 시각화 대시보드")
    
    # 탭으로 구분된 차트 그룹
    tabs = st.tabs([
        "기본 분석",
        "OCI 분석",
        "CGS 분석",
        "통합 분석"
    ])
    
    with tabs[0]:
        show_basic_analysis_charts()
    
    with tabs[1]:
        show_oci_analysis_charts()
    
    with tabs[2]:
        show_cgs_analysis_charts()
    
    with tabs[3]:
        show_integrated_analysis() 
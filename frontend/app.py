import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

import streamlit as st
from frontend.pages.upload import show_upload_page
from frontend.pages.analysis_dashboard import show_analysis_dashboard
from frontend.pages.manage import show_manage_page
from frontend.pages.comprehensive_analysis import show_comprehensive_analysis
from frontend.database import init_database

def main():
    # 페이지 기본 설정
    st.set_page_config(
        page_title="조직문화 AI 분석 시스템",
        page_icon="🏢",
        layout="wide"
    )
    hide_streamlit_style = """
        <style>
            [data-testid="stSidebarNav"] { display: none; }  /* 자동 생성되는 기본 사이드바 숨김 */
        </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    # CSS 스타일 적용
    st.markdown("""
        <style>
        .subtitle {
            color: #666;
            font-size: 1.1rem;
            font-weight: 400;
            margin-bottom: 0.5rem;
        }
        .main-title {
            font-size: 2.2rem;
            font-weight: 700;
            background: linear-gradient(120deg, #1E88E5, #1565C0);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 2rem;
        }
        .menu-container {
            display: flex;
            gap: 20px;
            margin: 2rem 0;
        }
        .menu-item {
            background-color: white;
            padding: 2.5rem;
            border-radius: 10px;
            box-shadow: 0 2px 6px rgba(0,0,0,0.1);
            flex: 1;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            min-height: 200px;
        }
        .menu-item:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            background-color: #f8f9fa;
        }
        .menu-icon {
            font-size: 2.5rem;
            margin-bottom: 1rem;
            color: #1E88E5;
        }
        .menu-title {
            font-size: 1.2rem;
            font-weight: 600;
            color: #333;
        }
        .menu-link {
            font-size: 0.9rem;
            color: #1E88E5;
            margin-top: 1rem;
            opacity: 0.8;
            transition: opacity 0.3s;
        }
        .menu-item:hover .menu-link {
            opacity: 1;
            text-decoration: underline;
        }
        .sidebar-menu {
            padding: 12px 15px;
            margin: 8px 0;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s;
            border-left: 3px solid transparent;
        }
        .sidebar-menu:hover {
            background-color: #f0f2f6;
            border-left-color: #1E88E5;
        }
        .selected {
            background-color: #e3f2fd;
            border-left-color: #1E88E5;
        }
        .stButton button {
            background-color: #f8f9fa;
            border: 1px solid #dee2e6;
            color: #1E88E5;
            font-size: 0.9rem;
            padding: 0.5rem 1rem;
            transition: all 0.3s ease;
        }
        .stButton button:hover {
            background-color: #e9ecef;
            border-color: #1E88E5;
            transform: translateY(-2px);
        }
        </style>
    """, unsafe_allow_html=True)

    # 사이드바 메뉴
    with st.sidebar:
        st.markdown("### 빠른 메뉴")
        
        # 홈 메뉴 추가
        if st.button("🏠 홈으로", key="home_btn", use_container_width=True):
            st.session_state['page'] = 'home'
            st.rerun()
        
        st.markdown("---")
        
        menu_items = {
            "upload": {"icon": "📊", "title": "데이터 업로드"},
            "manage": {"icon": "📁", "title": "데이터 관리"},
            "analysis": {"icon": "🤖", "title": "AI 분석 대시보드"},
            "comprehensive": {"icon": "📑", "title": "AI 종합분석 리포트"}
        }
        
        for key, item in menu_items.items():
            selected = st.session_state.get('page') == key
            if st.button(
                f"{item['icon']} {item['title']}", 
                key=f"side_{key}",
                use_container_width=True,
                type="secondary" if not selected else "primary"
            ):
                st.session_state['page'] = key
                st.rerun()

    # 메인 페이지 (홈)
    if st.session_state.get('page') == 'home':
        st.markdown('<p class="subtitle">AI·빅데이터 OCI,CGS분석을 활용한 조직문화 진단</p>', unsafe_allow_html=True)
        st.markdown('<h1 class="main-title">조직문화 AI분석 및 데이터 관리 시스템</h1>', unsafe_allow_html=True)

        # 메인 메뉴 (클릭 가능한 큰 박스)
        st.markdown("""
            <div class="menu-container">
                <div class="menu-item" onclick="document.getElementById('upload_btn').click()">
                    <div class="menu-icon">📊</div>
                    <div class="menu-title">데이터 업로드</div>
                    <div class="menu-link">데이터를 업로드하면 AI로 테이블 생성</div>
                </div>
                <div class="menu-item" onclick="document.getElementById('manage_btn').click()">
                    <div class="menu-icon">📁</div>
                    <div class="menu-title">데이터 관리</div>
                    <div class="menu-link">데이터 관리,삭제를 합니다</div>
                </div>
                <div class="menu-item" onclick="document.getElementById('analysis_btn').click()">
                    <div class="menu-icon">🤖</div>
                    <div class="menu-title">AI 분석 대시보드</div>
                    <div class="menu-link">항목별 AI 분석을 볼수 있습니다</div>
                </div>
                <div class="menu-item" onclick="document.getElementById('comprehensive_btn').click()">
                    <div class="menu-icon">📑</div>
                    <div class="menu-title">AI 종합분석 리포트</div>
                    <div class="menu-link">모든 분석을 종합한 AI 리포트</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # 숨겨진 버튼 (JavaScript 클릭 이벤트용)
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            if st.button("데이터 업로드 바로가기", 
                        key="upload_btn",
                        help="데이터 업로드",
                        use_container_width=True):
                st.session_state['page'] = 'upload'
                st.rerun()
        with col2:
            if st.button("데이터 관리 바로가기",
                        key="manage_btn",
                        help="데이터 관리",
                        use_container_width=True):
                st.session_state['page'] = 'manage'
                st.rerun()
        with col3:
            if st.button("AI 분석 대시보드 바로가기",
                        key="analysis_btn",
                        help="AI 분석 대시보드",
                        use_container_width=True):
                st.session_state['page'] = 'analysis'
                st.rerun()
        with col4:
            if st.button("AI 종합분석 리포트 바로가기",
                        key="comprehensive_btn",
                        help="AI 종합분석 리포트",
                        use_container_width=True):
                st.session_state['page'] = 'comprehensive'
                st.rerun()

    # 페이지 라우팅
    elif st.session_state.get('page') == 'upload':
        show_upload_page()
    elif st.session_state.get('page') == 'manage':
        show_manage_page()
    elif st.session_state.get('page') == 'analysis':
        show_analysis_dashboard()
    elif st.session_state.get('page') == 'comprehensive':
        show_comprehensive_analysis(st.session_state.get('selected_file_id'))

def get_menu_description(key):
    descriptions = {
        "upload": "설문 데이터를 시스템에 업로드하고 관리합니다.",
        "analysis": "AI를 활용한 심층 분석 결과를 확인합니다.",
        "manage": "업로드된 데이터와 분석 결과를 관리합니다."
    }
    return descriptions.get(key, "")

if __name__ == "__main__":
    init_database()
    if 'page' not in st.session_state:
        st.session_state['page'] = 'home'
    main() 

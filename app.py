"""
책쓰기 코칭 자동화 웹앱 v2.0
============================
완전 초보자도 6만자 책을 완성할 수 있도록 설계
- 목차 순서대로 1꼭지씩 안내
- 실시간 진행률 표시
- 데이터 저장/불러오기
"""
import streamlit as st
import json
import re
from datetime import datetime
from prompts.templates import WRITING_TONES
from utils.claude_client import (
    generate_titles,
    generate_toc,
    generate_draft,
    get_feedback,
    refine_text,
    add_storytelling,
    chat_with_coach,
    edit_draft_with_instruction,
    generate_proposal,
    generate_landing_page,
)

# 페이지 설정
st.set_page_config(
    page_title="책쓰기 코칭",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# CSS 스타일 (초보자 친화적 + 접근성 개선)
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E1E1E;
        margin-bottom: 1rem;
    }
    .step-header {
        font-size: 1.8rem;
        font-weight: bold;
        color: #2E7D32;
        margin-top: 1rem;
        padding: 0.5rem;
        background: linear-gradient(90deg, #E8F5E9 0%, transparent 100%);
        border-radius: 8px;
    }
    /* 키보드 포커스 강조 */
    button:focus-visible {
        outline: 3px solid #667eea !important;
        outline-offset: 2px !important;
    }
    .stButton > button:focus-visible {
        box-shadow: 0 0 0 3px #667eea !important;
    }
    /* 버튼 상호작용 상태 명시 */
    .stButton > button {
        transition: all 0.2s ease-in-out;
    }
    .stButton > button:active {
        transform: translateY(1px);
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.2);
    }
    /* 로딩 상태 - 버튼 비활성화 */
    .loading-state {
        opacity: 0.6;
        pointer-events: none;
    }
    .progress-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        text-align: center;
    }
    .progress-text {
        font-size: 2rem;
        font-weight: bold;
    }
    .current-section-box {
        background: #FFF3E0;
        border-left: 5px solid #FF9800;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 0 8px 8px 0;
    }
    .completed-section {
        background: #E8F5E9;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        margin: 0.3rem 0;
        color: #2E7D32;
    }
    .pending-section {
        background: #F5F5F5;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        margin: 0.3rem 0;
        color: #757575;
    }
    .big-button {
        font-size: 1.2rem !important;
        padding: 1rem 2rem !important;
    }
    .help-box {
        background: #E3F2FD;
        border: 1px solid #2196F3;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .warning-box {
        background: #FFF8E1;
        border: 1px solid #FFC107;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }

    /* 모바일 반응형 스타일 */
    @media (max-width: 768px) {
        .main-header {
            font-size: 1.8rem !important;
        }
        .step-header {
            font-size: 1.4rem !important;
        }
        .progress-box {
            padding: 1rem;
        }
        .progress-text {
            font-size: 1.5rem !important;
        }
        .stButton > button {
            min-height: 48px !important;
            font-size: 1rem !important;
        }
        .stTextArea textarea {
            font-size: 16px !important;
        }
        .stTextInput input {
            font-size: 16px !important;
            min-height: 44px !important;
        }
    }

    @media (max-width: 480px) {
        .main-header {
            font-size: 1.5rem !important;
        }
        .step-header {
            font-size: 1.2rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """세션 상태 초기화"""
    defaults = {
        "current_step": 1,
        "book_info": {},
        "generated_titles": "",
        "selected_title": "",
        "generated_toc": "",
        "parsed_toc": [],  # 파싱된 목차 구조
        "drafts": {},
        "current_section_index": 0,  # 현재 작성 중인 꼭지 인덱스
        "chat_messages": [],
        "show_chatbot": False,
        "generated_proposal": "",
        "generated_landing_page": "",
        "author_info": {},
        "webinar_info": {},
        "button_loading_state": {},  # 버튼 로딩 상태 추적
        "last_action_feedback": None,  # 마지막 작업 피드백
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def show_action_feedback(success=True, message="", duration=2):
    """표준화된 작업 피드백 표시"""
    if success:
        with st.container():
            st.success(f"✅ {message}")
        import time
        time.sleep(duration)
    else:
        st.error(f"❌ {message}")


def parse_toc(toc_text):
    """목차 텍스트를 파싱하여 구조화된 리스트로 변환"""
    sections = []
    current_part = None
    current_part_title = ""

    lines = toc_text.strip().split('\n')

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Part 감지 (다양한 형식 지원)
        part_match = re.match(r'^(?:Part|PART|파트|제)\s*(\d+)[.:]\s*(.+)', line, re.IGNORECASE)
        if part_match:
            current_part = int(part_match.group(1))
            current_part_title = part_match.group(2).strip()
            continue

        # 꼭지 감지 (다양한 형식 지원)
        # 1-1, 1.1, 01., 1., 제1장 등
        section_patterns = [
            r'^(\d+)[-.:](\d+)[.:)]\s*(.+)',  # 1-1. 제목, 1.1 제목
            r'^(\d+)[.:)]\s*(.+)',  # 1. 제목
            r'^[-*•]\s*(.+)',  # - 제목, * 제목
            r'^제?(\d+)(?:장|절|화)?[.:)]\s*(.+)',  # 제1장 제목
        ]

        for pattern in section_patterns:
            match = re.match(pattern, line)
            if match:
                groups = match.groups()
                if len(groups) == 3:  # 1-1 형식
                    section_num = f"{groups[0]}-{groups[1]}"
                    section_title = groups[2].strip()
                elif len(groups) == 2:  # 1. 형식
                    section_num = groups[0]
                    section_title = groups[1].strip()
                else:  # 불릿 형식
                    section_num = str(len(sections) + 1)
                    section_title = groups[0].strip()

                sections.append({
                    "part": current_part or 1,
                    "part_title": current_part_title or f"Part {current_part or 1}",
                    "section_num": section_num,
                    "section_title": section_title,
                    "full_title": f"Part {current_part or 1} - {section_num}. {section_title}"
                })
                break

    # 파싱된 섹션이 없으면 줄 단위로 처리
    if not sections:
        for i, line in enumerate(lines):
            line = line.strip()
            if line and not line.startswith('#') and len(line) > 3:
                sections.append({
                    "part": 1,
                    "part_title": "Part 1",
                    "section_num": str(i + 1),
                    "section_title": line,
                    "full_title": f"{i + 1}. {line}"
                })

    return sections


def get_progress_stats():
    """진행 상황 통계 계산"""
    parsed_toc = st.session_state.parsed_toc
    drafts = st.session_state.drafts

    total_sections = len(parsed_toc)
    completed_sections = len(drafts)

    total_chars = sum(
        len(d.replace(" ", "").replace("\n", ""))
        for d in drafts.values()
    )

    target_chars = 60000  # 목표 6만자

    return {
        "total_sections": total_sections,
        "completed_sections": completed_sections,
        "progress_percent": (completed_sections / total_sections * 100) if total_sections > 0 else 0,
        "total_chars": total_chars,
        "target_chars": target_chars,
        "chars_percent": (total_chars / target_chars * 100) if target_chars > 0 else 0,
    }


def render_progress_bar():
    """진행률 표시 바"""
    stats = get_progress_stats()

    if stats["total_sections"] == 0:
        return

    st.markdown(f"""
    <div class="progress-box">
        <div class="progress-text">
            📝 {stats['completed_sections']} / {stats['total_sections']} 꼭지 완료
        </div>
        <div style="margin-top: 0.5rem;">
            진행률: {stats['progress_percent']:.1f}%
        </div>
        <div style="margin-top: 0.5rem; font-size: 0.9rem;">
            현재 {stats['total_chars']:,}자 / 목표 {stats['target_chars']:,}자 ({stats['chars_percent']:.1f}%)
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Streamlit 프로그레스 바
    st.progress(stats['progress_percent'] / 100)


def render_sidebar():
    """사이드바 네비게이션"""
    with st.sidebar:
        st.markdown("## 📚 책쓰기 코칭")
        st.markdown("---")

        steps = [
            ("1️⃣", "정보 입력"),
            ("2️⃣", "제목 생성"),
            ("3️⃣", "목차 생성"),
            ("4️⃣", "초안 작성"),
            ("5️⃣", "출간기획서"),
            ("6️⃣", "랜딩페이지"),
            ("7️⃣", "다운로드"),
        ]

        for i, (icon, name) in enumerate(steps, 1):
            if i == st.session_state.current_step:
                st.markdown(f"**➡️ {icon} {name}**")
            elif i < st.session_state.current_step:
                st.markdown(f"✅ {name}")
            else:
                st.markdown(f"⬜ {icon} {name}")

        st.markdown("---")

        # 진행률 미니 표시
        if st.session_state.parsed_toc:
            stats = get_progress_stats()
            st.markdown(f"### 📊 진행 현황")
            st.markdown(f"**{stats['completed_sections']}/{stats['total_sections']}** 꼭지")
            st.markdown(f"**{stats['total_chars']:,}**자 작성")
            st.progress(stats['progress_percent'] / 100)

        st.markdown("---")

        # 데이터 저장/불러오기
        st.markdown("### 💾 데이터 관리")

        # 저장 버튼
        if st.button("📥 진행상황 저장", use_container_width=True):
            save_data = {
                "saved_at": datetime.now().isoformat(),
                "book_info": st.session_state.book_info,
                "selected_title": st.session_state.selected_title,
                "generated_toc": st.session_state.generated_toc,
                "parsed_toc": st.session_state.parsed_toc,
                "drafts": st.session_state.drafts,
                "current_section_index": st.session_state.current_section_index,
                "current_step": st.session_state.current_step,
                "author_info": st.session_state.author_info,
            }
            json_str = json.dumps(save_data, ensure_ascii=False, indent=2)
            st.download_button(
                label="⬇️ JSON 다운로드",
                data=json_str,
                file_name=f"책쓰기_진행상황_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
                mime="application/json",
                use_container_width=True
            )

        # 불러오기
        uploaded_file = st.file_uploader("📤 진행상황 불러오기", type=['json'], label_visibility="collapsed")
        if uploaded_file is not None:
            try:
                load_data = json.load(uploaded_file)
                if st.button("✅ 데이터 적용하기", use_container_width=True):
                    st.session_state.book_info = load_data.get("book_info", {})
                    st.session_state.selected_title = load_data.get("selected_title", "")
                    st.session_state.generated_toc = load_data.get("generated_toc", "")
                    st.session_state.parsed_toc = load_data.get("parsed_toc", [])
                    st.session_state.drafts = load_data.get("drafts", {})
                    st.session_state.current_section_index = load_data.get("current_section_index", 0)
                    st.session_state.current_step = load_data.get("current_step", 1)
                    st.session_state.author_info = load_data.get("author_info", {})
                    st.success("데이터를 불러왔습니다!")
                    st.rerun()
            except Exception as e:
                st.error(f"파일 오류: {e}")

        st.markdown("---")

        # 챗봇 토글 버튼
        if st.button("💬 AI 코치와 대화", use_container_width=True):
            st.session_state.show_chatbot = not st.session_state.show_chatbot
            st.rerun()


def render_welcome():
    """첫 방문 환영 화면"""
    st.markdown("""
    <div class="help-box" style="background: #E8F5E9; border: 2px solid #4CAF50; padding: 1.5rem;">
    <h2 style="margin-top:0; color: #2E7D32;">AI와 함께 7단계로 책을 완성하세요</h2>
    <ol style="line-height: 2; font-size: 1.1rem;">
        <li><b>정보 입력</b> - 책 주제와 독자 정보 (5분)</li>
        <li><b>제목 생성</b> - AI가 10가지 제목 추천 (2분)</li>
        <li><b>목차 생성</b> - 40개 꼭지 자동 구성 (3분)</li>
        <li><b>초안 작성</b> - 꼭지별 1,500자 자동 생성</li>
        <li><b>출간기획서</b> - 출판사 제출용 기획서</li>
        <li><b>랜딩페이지</b> - 홍보용 페이지 카피</li>
        <li><b>다운로드</b> - 완성된 원고 받기</li>
    </ol>
    <p style="background: #fff; padding: 0.8rem; border-radius: 8px; margin-top: 1rem;">
        <b>예상 소요 시간:</b> 정보입력~목차까지 약 10분, 초안 40개 작성 약 2시간
    </p>
    </div>
    """, unsafe_allow_html=True)


def render_step1():
    """1단계: 컨설팅 정보 입력"""
    # 첫 방문이면 환영 메시지 표시
    if not st.session_state.book_info:
        render_welcome()
        st.markdown("---")

    st.markdown('<p class="step-header">1단계: 기본 정보 입력</p>', unsafe_allow_html=True)

    st.markdown("""
    <div class="help-box">
    💡 <b>안내:</b> 아래 4가지 필수 항목만 입력하면 됩니다. 완벽하지 않아도 괜찮아요!
    <br><br>
    <b>각 항목이 어디에 사용되는지 알려드릴게요:</b>
    <ul style="margin: 0.5rem 0; font-size: 0.9rem;">
    <li><b>이름</b> → 책 표지, 출간기획서에 표시</li>
    <li><b>책 주제</b> → AI가 제목과 목차 생성할 때 참고</li>
    <li><b>타겟 독자</b> → 글의 난이도와 톤 결정</li>
    <li><b>핵심 메시지</b> → 책 전체의 방향을 잡는 중심축</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    # 개선점 1: 입력 템플릿/예시 제공 (초보자 지원)
    with st.expander("📋 입력 템플릿 & 예시 (뭘 써야 할지 모르겠다면)", expanded=False):
        st.markdown("""
        **예시 1: 부동산 투자**
        - 이름: 김재무
        - 책 주제: 직장인을 위한 부동산 투자 완벽 가이드
        - 타겟 독자: 30-40대 회사원, 재테크 초보자
        - 핵심 메시지: 월급만으로도 10년 안에 경제적 자유를 얻을 수 있다

        **예시 2: 시간 관리**
        - 이름: 박시간
        - 책 주제: 워킹맘의 스마트한 시간 관리 비법
        - 타겟 독자: 20-40대 워킹맘, 일과 육아의 균형을 원하는 사람
        - 핵심 메시지: 하루 2시간의 진정한 집중으로 인생의 질이 달라진다

        **예시 3: AI 활용**
        - 이름: 이인공
        - 책 주제: 직장인을 위한 ChatGPT 완벽 활용법
        - 타겟 독자: 20-50대 직장인, 업무 효율화에 관심 있는 사람
        - 핵심 메시지: AI를 올바로 다루면 업무 생산성이 3배 높아진다
        """)

    with st.form("book_info_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input(
                "📝 이름 (필수)",
                value=st.session_state.book_info.get("name", ""),
                placeholder="홍길동",
                help="💡 저자 이름이나 필명을 입력하세요. 책 표지에 표시됩니다."
            )
            topic = st.text_area(
                "📚 책 주제 (필수)",
                value=st.session_state.book_info.get("topic", ""),
                placeholder="예: 직장인을 위한 부동산 투자\n예: 워킹맘의 시간 관리 비법\n예: AI를 활용한 업무 자동화",
                height=100,
                help="💡 [대상] + [분야] + [방법/특징] 형태로 작성하면 좋습니다. 예) '30대 직장인' + '부동산 투자' + '월급으로 시작하는'"
            )
            target_reader = st.text_area(
                "👥 타겟 독자 (필수)",
                value=st.session_state.book_info.get("target_reader", ""),
                placeholder="예: 30-40대 직장인\n예: 재테크에 관심 있는 초보자\n예: 부업을 찾는 주부",
                height=100,
                help="💡 구체적일수록 좋습니다. 나이, 직업, 관심사, 현재 상황 등을 포함하세요."
            )

        with col2:
            core_message = st.text_area(
                "💎 핵심 메시지 (필수)",
                value=st.session_state.book_info.get("core_message", ""),
                placeholder="예: 월급쟁이도 10년 안에 경제적 자유를 얻을 수 있다\n예: 하루 30분 투자로 인생이 바뀐다",
                height=100,
                help="💡 독자가 이 책으로 '얻게 될 가장 중요한 깨달음'을 한 문장으로 정리하세요."
            )
            experience = st.text_area(
                "🌟 내 경험/스토리 (선택)",
                value=st.session_state.book_info.get("experience", ""),
                placeholder="예: 월급 300만원에서 시작해 10년간 투자로 자산 10억 달성",
                height=100,
                help="💡 구체적인 숫자나 결과가 있으면 더 좋습니다. 없어도 괜찮아요!"
            )
            tone = st.selectbox(
                "🎨 글쓰기 톤",
                options=WRITING_TONES,
                index=WRITING_TONES.index(st.session_state.book_info.get("tone", WRITING_TONES[0]))
                if st.session_state.book_info.get("tone") in WRITING_TONES else 0,
                help="💡 책의 분위기를 결정합니다. 예: 전문가적→신뢰감, 친절함→편안함"
            )

        submitted = st.form_submit_button(
            "✅ 저장하고 다음으로 →",
            use_container_width=True,
            type="primary"
        )

        if submitted:
            if not all([name, topic, target_reader, core_message]):
                st.error("❌ 필수 항목을 모두 입력해주세요! (이름, 책 주제, 타겟 독자, 핵심 메시지)")
            else:
                # 시각적 피드백: 진행 표시
                progress_placeholder = st.empty()
                progress_placeholder.info("💾 정보를 저장하고 있습니다...")

                st.session_state.book_info = {
                    "name": name,
                    "topic": topic,
                    "target_reader": target_reader,
                    "core_message": core_message,
                    "experience": experience,
                    "tone": tone,
                }
                st.session_state.current_step = 2

                # 명확한 성공 피드백
                progress_placeholder.success("✅ 저장되었습니다!")
                st.markdown("""
                <div style="background: #C8E6C9; padding: 1rem; border-radius: 8px; margin-top: 1rem; border-left: 4px solid #4CAF50;">
                <b>다음 단계:</b> 이제 Step 2로 진행하여 AI가 추천하는 10가지 책 제목을 선택하세요!
                </div>
                """, unsafe_allow_html=True)
                import time
                time.sleep(2)
                st.rerun()


def render_step2():
    """2단계: 제목 생성"""
    st.markdown('<p class="step-header">2단계: 제목 생성</p>', unsafe_allow_html=True)

    st.markdown("""
    <div class="help-box">
    💡 <b>팁:</b> AI가 10가지 제목을 제안합니다. 마음에 드는 것을 선택하거나 수정하세요.
    <br><br>
    <b>이 제목이 사용되는 곳:</b> 책 표지, 목차, 마케팅 자료, 출간기획서 전체에서 사용됩니다!
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        # 제목 생성 버튼
        if st.button("🎯 제목 10개 생성하기", use_container_width=True, type="primary"):
            with st.spinner("✨ AI가 제목을 생성하고 있습니다..."):
                result = generate_titles(st.session_state.book_info)
                if result:
                    st.session_state.generated_titles = result
                    st.rerun()
                else:
                    st.error("""
                    **제목 생성에 실패했습니다**

                    - 인터넷 연결을 확인해주세요
                    - 잠시 후 다시 시도해보세요
                    - 문제가 계속되면 사이드바에서 '진행상황 저장' 후 새로고침
                    """)

        # 생성된 제목 표시
        if st.session_state.generated_titles:
            st.markdown("### 📝 생성된 제목 후보")
            st.markdown(st.session_state.generated_titles)

            st.markdown("---")

            # 제목 선택/수정
            selected = st.text_input(
                "✏️ 최종 제목 (위에서 복사하거나 직접 작성)",
                value=st.session_state.selected_title,
                placeholder="최종 제목을 입력하세요"
            )

            if selected:
                st.session_state.selected_title = selected
                st.session_state.book_info["title"] = selected

    with col2:
        st.markdown("### 💡 좋은 제목의 조건")
        st.info("""
        ✅ 10자 이내로 간결하게
        ✅ 타겟 독자가 공감하는 단어
        ✅ 호기심을 유발
        ✅ 구체적인 숫자나 결과 포함

        **예시:**
        - 부의 추월차선
        - 아침형 인간
        - 1만 시간의 법칙
        """)

        if st.session_state.generated_titles:
            if st.button("🔄 다시 생성하기"):
                with st.spinner("✨ 다시 생성 중..."):
                    result = generate_titles(st.session_state.book_info)
                    if result:
                        st.session_state.generated_titles = result
                        st.rerun()

    # 네비게이션
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← 이전"):
            st.session_state.current_step = 1
            st.rerun()
    with col2:
        if st.session_state.selected_title:
            if st.button("다음 →", use_container_width=True, type="primary"):
                st.session_state.current_step = 3
                st.markdown("""
                <div style="background: #C8E6C9; padding: 1rem; border-radius: 8px; margin-top: 1rem;">
                <b>다음 단계:</b> 이제 5부 40꼭지의 목차를 AI가 자동 생성합니다!
                </div>
                """, unsafe_allow_html=True)
                import time
                time.sleep(2)
                st.rerun()
        else:
            st.warning("⚠️ 제목을 선택해주세요")


def render_step3():
    """3단계: 목차 생성"""
    st.markdown('<p class="step-header">3단계: 목차 생성</p>', unsafe_allow_html=True)
    st.markdown(f"**📖 책 제목:** {st.session_state.selected_title}")

    st.markdown("""
    <div class="help-box">
    💡 <b>안내:</b> 5부 40꼭지 구조로 목차를 생성합니다. 각 꼭지가 약 1,500자면 총 6만자 책이 됩니다!
    <br><br>
    <b>목차의 역할:</b> 다음 단계에서 생성할 초안의 틀이 됩니다. 꼭지 하나씩 AI가 자동으로 1,500자를 작성해줄 거예요!
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        # 목차 생성 버튼
        if st.button("📋 목차 생성하기 (5부 40꼭지)", use_container_width=True, type="primary"):
            with st.spinner("✨ AI가 목차를 생성하고 있습니다... (약 1분 소요)"):
                result = generate_toc(st.session_state.book_info)
                if result:
                    st.session_state.generated_toc = result
                    st.session_state.parsed_toc = parse_toc(result)
                    st.rerun()
                else:
                    st.error("""
                    **목차 생성에 실패했습니다**

                    - 30초 후 다시 '목차 생성하기' 버튼을 클릭해주세요
                    - 인터넷 연결을 확인해주세요
                    """)

        # 생성된 목차 표시
        if st.session_state.generated_toc:
            st.markdown("### 📚 생성된 목차")

            # 파싱 결과 표시
            if st.session_state.parsed_toc:
                st.success(f"✅ {len(st.session_state.parsed_toc)}개 꼭지가 인식되었습니다!")

                # 그룹별로 표시
                current_part = None
                for section in st.session_state.parsed_toc:
                    if section["part"] != current_part:
                        current_part = section["part"]
                        st.markdown(f"**Part {current_part}. {section['part_title']}**")
                    st.markdown(f"  - {section['section_num']}. {section['section_title']}")

            # 편집 가능한 텍스트 영역
            with st.expander("📝 목차 직접 수정 (고급)", expanded=False):
                edited_toc = st.text_area(
                    "목차 수정",
                    value=st.session_state.generated_toc,
                    height=400,
                    label_visibility="collapsed"
                )
                if edited_toc != st.session_state.generated_toc:
                    if st.button("🔄 수정 적용"):
                        st.session_state.generated_toc = edited_toc
                        st.session_state.parsed_toc = parse_toc(edited_toc)
                        st.rerun()

    with col2:
        st.markdown("### 📐 5부 구조 설명")
        st.info("""
        **Part 1. WHY (왜?)**
        → 문제 인식 & 동기 부여

        **Part 2. WHAT (무엇?)**
        → 핵심 개념 & 원리

        **Part 3. HOW (어떻게?)**
        → 구체적 방법론

        **Part 4. DO (실행)**
        → 실전 적용 & 사례

        **Part 5. FUTURE (미래)**
        → 비전 & 다음 단계
        """)

        if st.session_state.generated_toc:
            if st.button("🔄 목차 다시 생성"):
                with st.spinner("✨ 다시 생성 중..."):
                    result = generate_toc(st.session_state.book_info)
                    if result:
                        st.session_state.generated_toc = result
                        st.session_state.parsed_toc = parse_toc(result)
                        st.rerun()

    # 네비게이션
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← 이전"):
            st.session_state.current_step = 2
            st.rerun()
    with col2:
        if st.session_state.parsed_toc:
            if st.button("다음: 초안 작성 시작 →", use_container_width=True, type="primary"):
                st.session_state.current_step = 4
                st.markdown("""
                <div style="background: #C8E6C9; padding: 1rem; border-radius: 8px; margin-top: 1rem;">
                <b>다음 단계:</b> 40개 꼭지 중 하나씩 선택해서 AI 초안 작성 또는 직접 작성을 할 수 있어요!
                <br>한 번에 1개씩 또는 Part 단위로 일괄 생성도 가능합니다.
                </div>
                """, unsafe_allow_html=True)
                import time
                time.sleep(2)
                st.rerun()
        else:
            st.warning("⚠️ 목차를 먼저 생성해주세요")


def render_step4():
    """4단계: 초안 생성 - 순차적 플로우"""
    st.markdown('<p class="step-header">4단계: 초안 작성</p>', unsafe_allow_html=True)

    # 진행률 표시
    render_progress_bar()

    parsed_toc = st.session_state.parsed_toc
    drafts = st.session_state.drafts

    # 현재 상태에 따른 명확한 안내 메시지
    completed_count = len(drafts)
    total_count = len(parsed_toc)

    if total_count > 0:
        if completed_count == 0:
            st.markdown("""
            <div class="help-box">
            👋 <b>시작해볼까요?</b> 아래 '✨ AI로 초안 생성하기' 버튼 하나만 클릭하면 됩니다!
            </div>
            """, unsafe_allow_html=True)
        elif completed_count < total_count:
            remaining = total_count - completed_count
            st.markdown(f"""
            <div class="help-box">
            💪 <b>잘하고 있어요!</b> {completed_count}개 완료! 남은 꼭지: {remaining}개
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="help-box" style="background: #E8F5E9; border-color: #4CAF50;">
            🎉 <b>모든 초안 완료!</b> 아래에서 수정하거나 다음 단계로 넘어가세요.
            </div>
            """, unsafe_allow_html=True)

    if not parsed_toc:
        st.warning("⚠️ 먼저 3단계에서 목차를 생성해주세요!")
        if st.button("← 목차 생성하러 가기"):
            st.session_state.current_step = 3
            st.rerun()
        return

    # 완료되지 않은 첫 번째 꼭지 찾기
    current_idx = st.session_state.current_section_index

    # 모든 꼭지 완료 체크
    completed_keys = set(drafts.keys())
    all_section_keys = [f"{s['section_num']}_{s['section_title']}" for s in parsed_toc]

    # 현재 섹션이 범위를 벗어나면 조정
    if current_idx >= len(parsed_toc):
        current_idx = 0
        st.session_state.current_section_index = 0

    current_section = parsed_toc[current_idx]
    section_key = f"{current_section['section_num']}_{current_section['section_title']}"

    col1, col2 = st.columns([2, 1])

    with col1:
        # 현재 작성할 꼭지 표시
        st.markdown(f"""
        <div class="current-section-box">
        <h3>✍️ 현재 작성할 꼭지</h3>
        <p><b>Part {current_section['part']}.</b> {current_section['part_title']}</p>
        <p style="font-size: 1.3rem;"><b>{current_section['section_num']}. {current_section['section_title']}</b></p>
        </div>
        """, unsafe_allow_html=True)

        # 이미 작성된 경우
        if section_key in drafts:
            st.success("✅ 이 꼭지는 이미 작성되었습니다!")

            # 수정 가능
            edited_draft = st.text_area(
                "작성된 내용 (수정 가능)",
                value=drafts[section_key],
                height=400
            )
            if edited_draft != drafts[section_key]:
                drafts[section_key] = edited_draft

            char_count = len(edited_draft.replace(" ", "").replace("\n", ""))
            st.caption(f"📊 글자 수: {char_count}자")

            col_a, col_b = st.columns(2)
            with col_a:
                if current_idx > 0:
                    if st.button("⬅️ 이전 꼭지"):
                        st.session_state.current_section_index = current_idx - 1
                        st.rerun()
            with col_b:
                if current_idx < len(parsed_toc) - 1:
                    if st.button("➡️ 다음 꼭지", type="primary"):
                        st.session_state.current_section_index = current_idx + 1
                        st.rerun()
        else:
            # 초안 생성
            st.markdown("### 🚀 초안 생성")

            # 추가 정보 입력 (선택)
            with st.expander("💡 추가 정보 입력 (선택사항)", expanded=False):
                st.caption("아래 정보를 입력하면 AI가 더 맞춤형 초안을 작성해줍니다!")
                section_message = st.text_area(
                    "이 꼭지의 핵심 메시지",
                    placeholder="예: 완벽주의가 가장 큰 적이다",
                    height=80,
                    help="이 꼭지에서 가장 중요하게 전달할 메시지"
                )
                section_examples = st.text_area(
                    "포함할 사례/데이터",
                    placeholder="예: 출간 포기자의 80%가 완벽주의 성향",
                    height=80,
                    help="구체적인 예시나 데이터를 추가하면 초안이 더 설득력 있어집니다"
                )

            # 생성 버튼
            if st.button("✨ AI로 초안 생성하기 (약 1,500자)", use_container_width=True, type="primary"):
                section_info = {
                    "part_number": current_section["part"],
                    "part_title": current_section["part_title"],
                    "section_number": current_section["section_num"],
                    "section_title": current_section["section_title"],
                    "core_message": section_message if 'section_message' in dir() else "",
                    "examples": section_examples if 'section_examples' in dir() else "",
                }

                # 생성 진행 상태 표시
                status_container = st.container()
                with status_container:
                    progress_bar = st.progress(0, text="초안 생성 시작...")
                    status_text = st.empty()

                with st.spinner("✨ AI가 초안을 생성하고 있습니다... (약 1분)"):
                    status_text.info("💭 생성 중: 약 30초~1분 소요됩니다")
                    progress_bar.progress(50, text="초안 생성 중...")

                    result = generate_draft(st.session_state.book_info, section_info)

                    if result:
                        st.session_state.drafts[section_key] = result
                        progress_bar.progress(100, text="초안 생성 완료!")

                        # 마일스톤 성취감 피드백
                        new_completed = len(st.session_state.drafts)
                        total = len(parsed_toc)

                        # 명확한 피드백 메시지
                        feedback_messages = {
                            1: ("🎉 첫 번째 꼭지 완료!", "훌륭한 시작이에요!"),
                            10: ("🎊 10개 꼭지 완료!", "25% 진행률 달성!"),
                            20: ("🏆 절반 완료!", "당신은 정말 대단해요!"),
                        }

                        if new_completed in feedback_messages:
                            title, subtitle = feedback_messages[new_completed]
                            st.balloons()
                            st.success(f"{title}\n\n{subtitle}")
                        elif new_completed == total:
                            st.balloons()
                            st.success("🎆 축하합니다! 모든 초안이 완성되었습니다!")
                        else:
                            # Part 완료 체크
                            current_part_sections = [s for s in parsed_toc if s['part'] == current_section['part']]
                            current_part_completed = all(
                                f"{s['section_num']}_{s['section_title']}" in st.session_state.drafts
                                for s in current_part_sections
                            )
                            if current_part_completed:
                                st.balloons()
                                st.success(f"🎉 Part {current_section['part']} 완료!")
                            else:
                                st.success(f"✅ 초안 생성 완료! ({new_completed}/{total})")
                    else:
                        progress_bar.progress(100, text="생성 실패")
                        st.error("❌ 초안 생성에 실패했습니다. 다시 시도해주세요.")

                    st.rerun()

            # 직접 작성 옵션
            st.markdown("---")
            st.markdown("**또는 직접 작성하기:**")
            manual_draft = st.text_area(
                "직접 초안 작성",
                height=300,
                placeholder="여기에 직접 내용을 작성하세요...",
                label_visibility="collapsed"
            )
            if manual_draft:
                if st.button("💾 저장하기", use_container_width=True, type="primary"):
                    st.session_state.drafts[section_key] = manual_draft
                    char_count = len(manual_draft.replace(" ", "").replace("\n", ""))
                    st.success(f"✅ 저장되었습니다! ({char_count}자 저장됨)")
                    st.rerun()

    with col2:
        st.markdown("### 📋 진행 현황")

        # 현재 Part만 표시 (인지 부하 감소)
        current_part_num = current_section['part']
        current_part_sections = [s for s in parsed_toc if s['part'] == current_part_num]
        part_completed = sum(1 for s in current_part_sections
                            if f"{s['section_num']}_{s['section_title']}" in drafts)

        st.markdown(f"**Part {current_part_num}** ({part_completed}/{len(current_part_sections)})")

        # 키보드 접근성 개선: 각 버튼에 명확한 상태 설명
        for section in current_part_sections:
            key = f"{section['section_num']}_{section['section_title']}"
            idx = parsed_toc.index(section)
            is_current = (idx == current_idx)
            is_completed = key in drafts

            if is_current:
                prefix = "➡️ (현재)"
                help_text = "현재 작성 중인 꼭지입니다"
            elif is_completed:
                prefix = "✅ (완료)"
                help_text = "이 꼭지는 작성이 완료되었습니다"
            else:
                prefix = "⬜ (미작성)"
                help_text = "이 꼭지는 아직 작성되지 않았습니다"

            display_text = f"{prefix} {section['section_num']}. {section['section_title'][:12]}..."
            if st.button(
                display_text,
                key=f"jump_{idx}",
                use_container_width=True,
                help=help_text  # 스크린리더 및 마우스오버 지원
            ):
                st.session_state.current_section_index = idx
                st.rerun()

        # 다른 Part는 접어서 표시
        with st.expander("📑 다른 Part 보기", expanded=False):
            for part_num in range(1, 6):
                if part_num == current_part_num:
                    continue
                part_sections = [s for s in parsed_toc if s['part'] == part_num]
                if not part_sections:
                    continue
                completed = sum(1 for s in part_sections
                               if f"{s['section_num']}_{s['section_title']}" in drafts)
                if st.button(f"Part {part_num} ({completed}/{len(part_sections)})",
                            key=f"part_{part_num}"):
                    first_section = part_sections[0]
                    st.session_state.current_section_index = parsed_toc.index(first_section)
                    st.rerun()

        st.markdown("---")

        # 일괄 생성 옵션 (접기 처리)
        with st.expander("⚡ 빠른 생성 (고급)", expanded=False):
            # 현재 Part 전체 생성
            current_part = current_section['part']
            part_secs = [s for s in parsed_toc if s['part'] == current_part]
            unfinished_in_part = [s for s in part_secs
                                  if f"{s['section_num']}_{s['section_title']}" not in drafts]

            if unfinished_in_part:
                if st.button(f"🚀 Part {current_part} 전체 생성 ({len(unfinished_in_part)}개)",
                            use_container_width=True):
                    progress_bar = st.progress(0)
                    status_text = st.empty()

                    for i, section in enumerate(unfinished_in_part):
                        key = f"{section['section_num']}_{section['section_title']}"
                        status_text.text(f"생성 중: {section['section_title'][:20]}...")

                        section_info = {
                            "part_number": section["part"],
                            "part_title": section["part_title"],
                            "section_number": section["section_num"],
                            "section_title": section["section_title"],
                            "core_message": "",
                            "examples": "",
                        }

                        result = generate_draft(st.session_state.book_info, section_info)
                        if result:
                            st.session_state.drafts[key] = result

                        progress_bar.progress((i + 1) / len(unfinished_in_part))

                    st.balloons()
                    st.success(f"✅ Part {current_part} 완료!")
                    st.rerun()
            else:
                st.info("✅ 이 Part의 모든 꼭지가 완료되었습니다!")

    # 네비게이션
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← 목차로"):
            st.session_state.current_step = 3
            st.rerun()
    with col2:
        if st.button("다음: 출간기획서 →", use_container_width=True):
            st.session_state.current_step = 5
            st.rerun()


def render_step5():
    """5단계: 출간기획서"""
    st.markdown('<p class="step-header">5단계: 출간기획서</p>', unsafe_allow_html=True)
    st.markdown("""
    출판사에 제출할 기획서를 생성합니다.

    **저자 정보가 중요한 이유:** 출판사는 저자의 신뢰도와 영향력을 확인합니다. 당신의 경력과 성과를 입력해주세요!
    """)

    col1, col2 = st.columns([2, 1])

    with col1:
        # 개선점 2: 저자 정보 입력 템플릿 제공
        with st.expander("📋 저자 정보 입력 템플릿 (참고용)", expanded=False):
            st.markdown("""
            **예시 1: 컨설턴트**
            - 직업/전문 분야: 부동산 컨설턴트
            - 경력/전문성: 10년간 부동산 투자, 100명 이상의 클라이언트 자산 관리
            - 대표 성과: 서울 강남 프로젝트 성공 사례 다수, 유튜브 구독자 5만명
            - SNS/블로그: 유튜브 채널 5만, 블로그 월 10만 방문

            **예시 2: 기업 임원**
            - 직업/전문 분야: 마케팅 이사 (업력 12년)
            - 경력/전문성: 500억 규모 마케팅 캠페인 성공 주도, 3개 회사 성장 경험
            - 대표 성과: MBC 경제 프로그램 출연, 비즈니스 신문 칼럼니스트
            - SNS/블로그: 링크드인 팔로워 2만
            """)

        # 저자 정보 입력
        with st.expander("📝 저자 정보 입력", expanded=not st.session_state.generated_proposal):
            profession = st.text_input(
                "직업/전문 분야",
                value=st.session_state.author_info.get("profession", ""),
                placeholder="예: 부동산 컨설턴트, 10년차 마케터",
                help="💡 현재 직업과 전문성을 명확히 입력하세요. 업력 정보가 있으면 좋습니다."
            )
            career = st.text_area(
                "경력/전문성",
                value=st.session_state.author_info.get("career", ""),
                placeholder="예: 부동산 투자 15년, 자산 100억 달성",
                height=80,
                help="💡 구체적인 숫자와 성과를 포함하세요. 예) '100명 클라이언트 관리', '500억 프로젝트 주도'"
            )
            achievements = st.text_area(
                "대표 성과",
                value=st.session_state.author_info.get("achievements", ""),
                placeholder="예: 베스트셀러 저자, TV 출연",
                height=80,
                help="💡 미디어 출연, 상장 사건, 저널 기고 등 신뢰도를 높이는 경력사항"
            )
            sns = st.text_input(
                "SNS/블로그",
                value=st.session_state.author_info.get("sns", ""),
                placeholder="예: 인스타 1만, 유튜브 5천",
                help="💡 팔로워 수를 명시해 주세요. 영향력 지표가 됩니다."
            )
            contact = st.text_input(
                "연락처",
                value=st.session_state.author_info.get("contact", ""),
                placeholder="예: email@example.com",
                help="💡 출판사가 연락할 이메일이나 전화번호"
            )

            if st.button("💾 저자 정보 저장", use_container_width=True, type="secondary"):
                st.session_state.author_info = {
                    "name": st.session_state.book_info.get("name", ""),
                    "profession": profession,
                    "career": career,
                    "achievements": achievements,
                    "sns": sns,
                    "contact": contact,
                }
                st.success("✅ 저자 정보가 저장되었습니다!")

        # 기획서 생성
        if st.button("📄 출간기획서 생성하기", use_container_width=True, type="primary"):
            if not st.session_state.author_info:
                st.warning("먼저 저자 정보를 저장해주세요.")
            else:
                with st.spinner("✨ 기획서를 생성하고 있습니다..."):
                    result = generate_proposal(
                        st.session_state.book_info,
                        st.session_state.author_info
                    )
                    if result:
                        st.session_state.generated_proposal = result
                        st.rerun()

        # 생성된 기획서 표시
        if st.session_state.generated_proposal:
            st.markdown("### 📋 생성된 출간기획서")
            edited_proposal = st.text_area(
                "기획서 수정 (직접 편집 가능)",
                value=st.session_state.generated_proposal,
                height=500,
                label_visibility="collapsed"
            )
            st.session_state.generated_proposal = edited_proposal

            st.download_button(
                label="📥 기획서 다운로드",
                data=edited_proposal,
                file_name=f"{st.session_state.selected_title}_출간기획서.md",
                mime="text/markdown",
                use_container_width=True
            )

    with col2:
        st.markdown("### 💡 기획서 팁")
        st.info("""
        **필수 7요소:**
        1. 제목 & 부제목
        2. 기획 의도
        3. 타겟 독자
        4. 시장 분석
        5. 목차 요약
        6. 저자 소개
        7. 마케팅 계획
        """)

    # 네비게이션
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← 이전"):
            st.session_state.current_step = 4
            st.rerun()
    with col2:
        if st.button("다음 →", use_container_width=True, type="primary"):
            st.session_state.current_step = 6
            st.rerun()


def render_step6():
    """6단계: 랜딩페이지"""
    st.markdown('<p class="step-header">6단계: 랜딩페이지</p>', unsafe_allow_html=True)
    st.markdown("책 홍보용 랜딩페이지 카피를 생성합니다.")

    col1, col2 = st.columns([2, 1])

    with col1:
        # 개선점 2: 웨비나 정보 입력 템플릿 제공
        with st.expander("📋 웨비나 정보 입력 템플릿 (참고용)", expanded=False):
            st.markdown("""
            **예시: 부동산 투자 웨비나**
            - 웨비나 제목: 월급쟁이도 10년 안에 경제적 자유를 얻는 부동산 투자법
            - 일시: 2025년 2월 15일 (토) 오후 2시 ~ 3시 30분
            - 강사: 김재무
            - 주요 내용:
              - 부동산 초보자가 저지르는 3가지 실수
              - 월 500만원으로 시작하는 포트폴리오 구성
              - 2024년 부동산 시장 분석 & 기회 포착법
              - 실전 사례: 강남, 여의도 프로젝트 경험담
            - 보너스/혜택:
              - 부동산 투자 체크리스트 (PDF)
              - 지역별 시세 분석 자료
              - 참석자 전용 1:1 상담 권리 (1명 선착순)
            """)

        # 웨비나 정보 입력
        with st.expander("📝 웨비나/이벤트 정보", expanded=not st.session_state.generated_landing_page):
            webinar_title = st.text_input(
                "웨비나 제목",
                value=st.session_state.webinar_info.get("webinar_title", ""),
                placeholder="예: 2달 만에 책 쓰는 비밀 공개",
                help="💡 책의 핵심 메시지를 담은 매력적인 제목을 작성하세요."
            )
            datetime_input = st.text_input(
                "일시",
                value=st.session_state.webinar_info.get("datetime", ""),
                placeholder="예: 2025년 2월 15일 (토) 오후 2시",
                help="💡 구체적인 날짜와 시간(소요 시간 포함)을 입력하세요."
            )
            speaker = st.text_input(
                "강사",
                value=st.session_state.webinar_info.get("speaker", st.session_state.book_info.get("name", "")),
                help="💡 웨비나를 주도할 강사(저자)의 이름"
            )
            content = st.text_area(
                "주요 내용",
                value=st.session_state.webinar_info.get("content", ""),
                height=80,
                placeholder="- 주제1: 구체적 내용\n- 주제2: 학습할 내용\n- 사례: 성공 사례 소개",
                help="💡 3-5개의 핵심 주제를 불릿 포인트로 작성하세요."
            )
            bonus = st.text_area(
                "보너스/혜택",
                value=st.session_state.webinar_info.get("bonus", ""),
                height=80,
                placeholder="- 제공 자료: PDF 템플릿\n- 혜택: 1:1 상담\n- 할인: 책 출간 기념 30% 할인 쿠폰",
                help="💡 참석자를 끌어당길 수 있는 구체적인 혜택을 나열하세요."
            )

            if st.button("💾 웨비나 정보 저장", use_container_width=True, type="secondary"):
                st.session_state.webinar_info = {
                    "webinar_title": webinar_title,
                    "datetime": datetime_input,
                    "speaker": speaker,
                    "content": content,
                    "bonus": bonus,
                }
                st.success("✅ 웨비나 정보가 저장되었습니다!")

        # 랜딩페이지 생성
        if st.button("🎨 랜딩페이지 카피 생성", use_container_width=True, type="primary"):
            if not st.session_state.webinar_info:
                st.warning("먼저 웨비나 정보를 저장해주세요.")
            else:
                with st.spinner("✨ 랜딩페이지를 생성하고 있습니다..."):
                    result = generate_landing_page(
                        st.session_state.book_info,
                        st.session_state.webinar_info
                    )
                    if result:
                        st.session_state.generated_landing_page = result
                        st.rerun()

        # 생성된 랜딩페이지 표시
        if st.session_state.generated_landing_page:
            st.markdown("### 🎨 생성된 랜딩페이지 카피")
            edited_landing = st.text_area(
                "카피 수정",
                value=st.session_state.generated_landing_page,
                height=500,
                label_visibility="collapsed"
            )
            st.session_state.generated_landing_page = edited_landing

            st.download_button(
                label="📥 랜딩페이지 다운로드",
                data=edited_landing,
                file_name=f"{st.session_state.selected_title}_랜딩페이지.md",
                mime="text/markdown",
                use_container_width=True
            )

    with col2:
        st.markdown("### 💡 랜딩페이지 구조")
        st.info("""
        1. 헤더 (Hero)
        2. 문제 제기
        3. 해결책 제시
        4. 강사 소개
        5. 커리큘럼
        6. 후기/성과
        7. 보너스
        8. 신청 폼
        9. FAQ
        10. 최종 CTA
        """)

    # 네비게이션
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← 이전"):
            st.session_state.current_step = 5
            st.rerun()
    with col2:
        if st.button("다음: 최종 다운로드 →", use_container_width=True, type="primary"):
            st.session_state.current_step = 7
            st.rerun()


def render_step7():
    """7단계: 결과물 다운로드"""
    st.markdown('<p class="step-header">7단계: 완성! 다운로드</p>', unsafe_allow_html=True)

    # 최종 진행률
    render_progress_bar()

    # 통계
    stats = get_progress_stats()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📝 총 글자 수", f"{stats['total_chars']:,}자")
    with col2:
        st.metric("📚 작성된 꼭지", f"{stats['completed_sections']}개")
    with col3:
        estimated_pages = stats['total_chars'] // 1800
        st.metric("📖 예상 페이지", f"약 {estimated_pages}쪽")

    st.markdown("---")

    # 전체 원고 생성
    full_manuscript = f"""# {st.session_state.selected_title}

**작성자:** {st.session_state.book_info.get('name', '')}

---

## 책 정보

- **주제:** {st.session_state.book_info.get('topic', '')}
- **타겟 독자:** {st.session_state.book_info.get('target_reader', '')}
- **핵심 메시지:** {st.session_state.book_info.get('core_message', '')}

---

## 목차

{st.session_state.generated_toc}

---

## 본문

"""

    # 초안 추가 (Part별로 정리)
    if st.session_state.parsed_toc:
        current_part = None
        for section in st.session_state.parsed_toc:
            key = f"{section['section_num']}_{section['section_title']}"

            if section['part'] != current_part:
                current_part = section['part']
                full_manuscript += f"\n# Part {current_part}. {section['part_title']}\n\n"

            if key in st.session_state.drafts:
                full_manuscript += f"""
## {section['section_num']}. {section['section_title']}

{st.session_state.drafts[key]}

---
"""

    # 미리보기
    with st.expander("📄 전체 원고 미리보기", expanded=False):
        st.markdown(full_manuscript)

    # 다운로드 버튼들
    st.markdown("### 📥 다운로드")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.download_button(
            label="📚 전체 원고 (Markdown)",
            data=full_manuscript,
            file_name=f"{st.session_state.selected_title}_전체원고.md",
            mime="text/markdown",
            use_container_width=True
        )

    with col2:
        toc_only = f"# {st.session_state.selected_title}\n\n## 목차\n\n{st.session_state.generated_toc}"
        st.download_button(
            label="📋 목차만 다운로드",
            data=toc_only,
            file_name=f"{st.session_state.selected_title}_목차.md",
            mime="text/markdown",
            use_container_width=True
        )

    with col3:
        # JSON 전체 데이터
        all_data = {
            "book_info": st.session_state.book_info,
            "selected_title": st.session_state.selected_title,
            "generated_toc": st.session_state.generated_toc,
            "drafts": st.session_state.drafts,
        }
        st.download_button(
            label="💾 전체 데이터 (JSON)",
            data=json.dumps(all_data, ensure_ascii=False, indent=2),
            file_name=f"{st.session_state.selected_title}_전체데이터.json",
            mime="application/json",
            use_container_width=True
        )

    st.markdown("---")

    # 축하 메시지
    if stats['completed_sections'] >= stats['total_sections'] * 0.8:
        st.balloons()
        st.success("""
        🎉 **축하합니다!**

        책 원고가 거의 완성되었습니다! 이제 다음 단계를 진행하세요:
        1. 전체 원고를 다운로드
        2. Word나 한글로 옮겨서 최종 편집
        3. 출판사에 출간기획서와 함께 제출
        """)

    # 처음으로 - 확인 절차 추가
    st.markdown("---")
    if "confirm_new_book" not in st.session_state:
        st.session_state.confirm_new_book = False

    if not st.session_state.confirm_new_book:
        if st.button("🔄 새 책 시작하기", use_container_width=True):
            st.session_state.confirm_new_book = True
            st.rerun()
    else:
        st.warning("⚠️ 정말로 모든 데이터를 삭제하고 새로 시작할까요?")
        st.caption("💾 삭제 전에 사이드바의 '진행상황 저장'으로 백업하세요!")
        col_confirm1, col_confirm2 = st.columns(2)
        with col_confirm1:
            if st.button("✅ 예, 삭제하고 새로 시작", type="primary"):
                for key in list(st.session_state.keys()):
                    del st.session_state[key]
                st.rerun()
        with col_confirm2:
            if st.button("❌ 취소"):
                st.session_state.confirm_new_book = False
                st.rerun()

    if st.button("← 이전 단계"):
        st.session_state.current_step = 6
        st.rerun()


def render_chatbot():
    """AI 코치 챗봇"""
    st.markdown("### 💬 AI 책쓰기 코치")

    # 대화 히스토리
    for msg in st.session_state.chat_messages:
        if msg["role"] == "user":
            st.markdown(f"**🧑 나:** {msg['content']}")
        else:
            st.markdown(f"**🤖 코치:** {msg['content']}")
            st.markdown("---")

    # 입력
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "메시지",
            placeholder="무엇이든 물어보세요!",
            height=80,
            label_visibility="collapsed"
        )
        col1, col2 = st.columns([3, 1])
        with col1:
            send_btn = st.form_submit_button("보내기", use_container_width=True)
        with col2:
            if st.form_submit_button("초기화"):
                st.session_state.chat_messages = []
                st.rerun()

    if send_btn and user_input:
        st.session_state.chat_messages.append({"role": "user", "content": user_input})

        with st.spinner("답변 중..."):
            response = chat_with_coach(
                st.session_state.chat_messages,
                st.session_state.book_info
            )
            if response:
                st.session_state.chat_messages.append({"role": "assistant", "content": response})
        st.rerun()

    # 빠른 질문 (키보드 접근성 개선)
    st.markdown("#### 💡 자주 묻는 질문")
    st.caption("아래 질문 버튼을 클릭하거나 Tab 키로 이동 후 Enter를 눌러 선택할 수 있습니다.")
    quick_questions = [
        "글이 막힐 때 어떻게 하나요?",
        "제목을 더 매력적으로 만들려면?",
    ]
    for idx, q in enumerate(quick_questions):
        if st.button(
            q,
            key=f"quick_{idx}",
            use_container_width=True,
            help=f"빠른 질문: {q}"  # 스크린리더 지원
        ):
            st.session_state.chat_messages.append({"role": "user", "content": q})
            with st.spinner("답변 중..."):
                response = chat_with_coach(st.session_state.chat_messages, st.session_state.book_info)
                if response:
                    st.session_state.chat_messages.append({"role": "assistant", "content": response})
            st.rerun()


def main():
    """메인 함수"""
    init_session_state()
    render_sidebar()

    # 레이아웃
    if st.session_state.show_chatbot:
        col1, col2 = st.columns([2, 1])
        with col1:
            st.markdown('<p class="main-header">📚 책쓰기 코칭</p>', unsafe_allow_html=True)
            st.markdown("AI와 함께 6만자 책을 완성하세요!")
            st.markdown("---")

            steps = {
                1: render_step1,
                2: render_step2,
                3: render_step3,
                4: render_step4,
                5: render_step5,
                6: render_step6,
                7: render_step7,
            }
            current_step = st.session_state.current_step
            if current_step in steps:
                steps[current_step]()

        with col2:
            render_chatbot()
    else:
        st.markdown('<p class="main-header">📚 책쓰기 코칭</p>', unsafe_allow_html=True)
        st.markdown("AI와 함께 6만자 책을 완성하세요!")
        st.markdown("---")

        steps = {
            1: render_step1,
            2: render_step2,
            3: render_step3,
            4: render_step4,
            5: render_step5,
            6: render_step6,
            7: render_step7,
        }
        current_step = st.session_state.current_step
        if current_step in steps:
            steps[current_step]()


if __name__ == "__main__":
    main()

"""
책쓰기 코칭 자동화 웹앱
========================
수강생이 URL 접속만으로 제목/목차/초안을 생성할 수 있는 웹앱
"""
import streamlit as st
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

# CSS 스타일
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E1E1E;
        margin-bottom: 1rem;
    }
    .step-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #4A90A4;
        margin-top: 1rem;
    }
    .info-box {
        background-color: #F5F7FA;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .success-box {
        background-color: #D4EDDA;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
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
        "toc_sections": [],
        "drafts": {},
        "current_section": None,
        "chat_messages": [],
        "show_chatbot": False,
        "generated_proposal": "",
        "generated_landing_page": "",
        "author_info": {},
        "webinar_info": {},
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def render_sidebar():
    """사이드바 네비게이션"""
    with st.sidebar:
        st.markdown("## 📚 책쓰기 코칭")
        st.markdown("---")

        steps = [
            ("1️⃣", "컨설팅 정보 입력"),
            ("2️⃣", "제목 생성"),
            ("3️⃣", "목차 생성"),
            ("4️⃣", "초안 생성"),
            ("5️⃣", "출간기획서"),
            ("6️⃣", "랜딩페이지"),
            ("7️⃣", "결과물 다운로드"),
        ]

        for i, (icon, name) in enumerate(steps, 1):
            if i == st.session_state.current_step:
                st.markdown(f"**{icon} {name}** ← 현재")
            elif i < st.session_state.current_step:
                st.markdown(f"✅ ~~{name}~~")
            else:
                st.markdown(f"{icon} {name}")

        st.markdown("---")

        # 챗봇 토글 버튼
        if st.button("💬 AI 코치와 대화", use_container_width=True):
            st.session_state.show_chatbot = not st.session_state.show_chatbot
            st.rerun()

        st.markdown("---")

        if st.session_state.book_info:
            st.markdown("### 📋 입력된 정보")
            info = st.session_state.book_info
            if info.get("name"):
                st.markdown(f"**이름:** {info['name']}")
            if info.get("topic"):
                st.markdown(f"**주제:** {info['topic'][:20]}...")
            if st.session_state.selected_title:
                st.markdown(f"**제목:** {st.session_state.selected_title[:15]}...")


def render_step1():
    """1단계: 컨설팅 정보 입력"""
    st.markdown('<p class="step-header">1단계: 컨설팅 정보 입력</p>', unsafe_allow_html=True)
    st.markdown("책을 쓰기 위한 기본 정보를 입력해주세요.")

    with st.form("book_info_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input(
                "이름 *",
                value=st.session_state.book_info.get("name", ""),
                placeholder="홍길동"
            )
            topic = st.text_area(
                "책 주제 *",
                value=st.session_state.book_info.get("topic", ""),
                placeholder="예: 직장인을 위한 부동산 투자",
                height=100
            )
            target_reader = st.text_area(
                "타겟 독자 *",
                value=st.session_state.book_info.get("target_reader", ""),
                placeholder="예: 30-40대 직장인, 재테크에 관심 있는 초보 투자자",
                height=100
            )

        with col2:
            core_message = st.text_area(
                "핵심 메시지 *",
                value=st.session_state.book_info.get("core_message", ""),
                placeholder="예: 소액으로 시작해도 10년 안에 경제적 자유를 얻을 수 있다",
                height=100
            )
            experience = st.text_area(
                "내 경험/스토리",
                value=st.session_state.book_info.get("experience", ""),
                placeholder="예: 월급 300만원에서 시작해 10년간 부동산 투자로 자산 10억 달성",
                height=100
            )
            tone = st.selectbox(
                "글쓰기 톤",
                options=WRITING_TONES,
                index=WRITING_TONES.index(st.session_state.book_info.get("tone", WRITING_TONES[0]))
                if st.session_state.book_info.get("tone") in WRITING_TONES else 0
            )

        submitted = st.form_submit_button("다음 단계로 →", use_container_width=True)

        if submitted:
            if not all([name, topic, target_reader, core_message]):
                st.error("필수 항목(*)을 모두 입력해주세요.")
            else:
                st.session_state.book_info = {
                    "name": name,
                    "topic": topic,
                    "target_reader": target_reader,
                    "core_message": core_message,
                    "experience": experience,
                    "tone": tone,
                }
                st.session_state.current_step = 2
                st.rerun()


def render_step2():
    """2단계: 제목 생성"""
    st.markdown('<p class="step-header">2단계: 제목 생성</p>', unsafe_allow_html=True)
    st.markdown("10가지 공식을 기반으로 책 제목을 생성합니다.")

    col1, col2 = st.columns([2, 1])

    with col1:
        # 제목 생성 버튼
        if st.button("🎯 제목 10개 생성하기", use_container_width=True):
            with st.spinner("제목을 생성하고 있습니다... (약 30초 소요)"):
                result = generate_titles(st.session_state.book_info)
                if result:
                    st.session_state.generated_titles = result
                    st.rerun()

        # 생성된 제목 표시
        if st.session_state.generated_titles:
            st.markdown("### 📝 생성된 제목")
            st.markdown(st.session_state.generated_titles)

            st.markdown("---")

            # 제목 선택/수정
            selected = st.text_input(
                "최종 제목 입력 (위에서 선택하거나 직접 작성)",
                value=st.session_state.selected_title,
                placeholder="최종 제목을 입력하세요"
            )

            if selected:
                st.session_state.selected_title = selected
                st.session_state.book_info["title"] = selected

    with col2:
        st.markdown("### 💡 도움말")
        st.info("""
        **좋은 제목의 조건:**
        - 10자 이내로 핵심 전달
        - 타겟 독자가 공감
        - 호기심 유발
        - 구체적인 숫자/결과 포함
        """)

        if st.session_state.generated_titles:
            if st.button("🔄 다시 생성하기"):
                with st.spinner("제목을 다시 생성하고 있습니다..."):
                    result = generate_titles(st.session_state.book_info)
                    if result:
                        st.session_state.generated_titles = result
                        st.rerun()

    # 네비게이션
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← 이전 단계"):
            st.session_state.current_step = 1
            st.rerun()
    with col2:
        if st.session_state.selected_title:
            if st.button("다음 단계로 →", use_container_width=True):
                st.session_state.current_step = 3
                st.rerun()
        else:
            st.warning("제목을 선택해주세요.")


def render_step3():
    """3단계: 목차 생성"""
    st.markdown('<p class="step-header">3단계: 목차 생성</p>', unsafe_allow_html=True)
    st.markdown(f"**선택된 제목:** {st.session_state.selected_title}")

    col1, col2 = st.columns([2, 1])

    with col1:
        # 목차 생성 버튼
        if st.button("📋 5부 구조 목차 생성하기", use_container_width=True):
            with st.spinner("목차를 생성하고 있습니다... (약 1분 소요)"):
                result = generate_toc(st.session_state.book_info)
                if result:
                    st.session_state.generated_toc = result
                    st.rerun()

        # 생성된 목차 표시
        if st.session_state.generated_toc:
            st.markdown("### 📚 생성된 목차 (5부 40꼭지)")

            # 편집 가능한 텍스트 영역
            edited_toc = st.text_area(
                "목차 수정 (직접 편집 가능)",
                value=st.session_state.generated_toc,
                height=500
            )
            st.session_state.generated_toc = edited_toc

    with col2:
        st.markdown("### 💡 5부 구조")
        st.info("""
        **Part 1. WHY (왜?)**
        문제 인식 & 동기 부여

        **Part 2. WHAT (무엇?)**
        핵심 개념 & 원리

        **Part 3. HOW (어떻게?)**
        구체적 방법론

        **Part 4. DO (실행)**
        실전 적용 & 사례

        **Part 5. FUTURE (미래)**
        비전 & 다음 단계
        """)

        if st.session_state.generated_toc:
            if st.button("🔄 목차 다시 생성"):
                with st.spinner("목차를 다시 생성하고 있습니다..."):
                    result = generate_toc(st.session_state.book_info)
                    if result:
                        st.session_state.generated_toc = result
                        st.rerun()

            if st.button("💬 AI 피드백 받기"):
                with st.spinner("피드백을 생성하고 있습니다..."):
                    feedback = get_feedback(st.session_state.generated_toc, "toc")
                    if feedback:
                        st.markdown("### 📝 AI 피드백")
                        st.markdown(feedback)

    # 네비게이션
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← 이전 단계"):
            st.session_state.current_step = 2
            st.rerun()
    with col2:
        if st.session_state.generated_toc:
            if st.button("다음 단계로 →", use_container_width=True):
                st.session_state.current_step = 4
                st.rerun()
        else:
            st.warning("목차를 먼저 생성해주세요.")


def render_step4():
    """4단계: 초안 생성"""
    st.markdown('<p class="step-header">4단계: 초안 생성</p>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown("### 꼭지 선택 및 초안 생성")

        # 꼭지 정보 입력
        with st.expander("📝 초안을 작성할 꼭지 정보 입력", expanded=True):
            part_number = st.selectbox(
                "Part 번호",
                options=[1, 2, 3, 4, 5],
                format_func=lambda x: f"Part {x}"
            )
            part_title = st.text_input(
                "Part 제목",
                placeholder="예: 왜 지금 책을 써야 하는가"
            )
            section_number = st.text_input(
                "꼭지 번호",
                placeholder="예: 1-1"
            )
            section_title = st.text_input(
                "꼭지 제목",
                placeholder="예: 당신이 3년째 책을 못 쓰는 진짜 이유"
            )
            section_message = st.text_area(
                "이 꼭지의 핵심 메시지 (선택)",
                placeholder="예: 완벽주의가 가장 큰 적이다"
            )
            section_examples = st.text_area(
                "포함할 사례/데이터 (선택)",
                placeholder="예: 출간 포기자의 80%가 완벽주의 성향"
            )

        if st.button("✍️ 초안 생성하기 (2000자)", use_container_width=True):
            if section_title:
                section_info = {
                    "part_number": part_number,
                    "part_title": part_title,
                    "section_number": section_number,
                    "section_title": section_title,
                    "core_message": section_message,
                    "examples": section_examples,
                }
                with st.spinner("초안을 생성하고 있습니다... (약 1분 소요)"):
                    result = generate_draft(st.session_state.book_info, section_info)
                    if result:
                        key = f"{section_number}_{section_title}"
                        st.session_state.drafts[key] = result
                        st.session_state.current_section = key
                        st.rerun()
            else:
                st.error("꼭지 제목을 입력해주세요.")

        # 생성된 초안 표시
        if st.session_state.current_section and st.session_state.current_section in st.session_state.drafts:
            st.markdown("---")
            st.markdown(f"### 📄 초안: {st.session_state.current_section}")

            draft = st.session_state.drafts[st.session_state.current_section]
            edited_draft = st.text_area(
                "초안 수정 (직접 편집 가능)",
                value=draft,
                height=400,
                key="draft_editor"
            )
            st.session_state.drafts[st.session_state.current_section] = edited_draft

            # 글자 수 표시
            char_count = len(edited_draft.replace(" ", "").replace("\n", ""))
            st.caption(f"글자 수: {char_count}자 (공백 제외)")

            # AI 초안 수정 기능
            st.markdown("#### 🤖 AI로 초안 수정하기")
            edit_instruction = st.text_area(
                "수정 지시사항",
                placeholder="예: 도입부를 더 강렬하게 바꿔줘 / 문장을 더 짧게 다듬어줘 / 사례를 추가해줘",
                height=80,
                key="edit_instruction"
            )

            col_edit1, col_edit2, col_edit3 = st.columns(3)
            with col_edit1:
                if st.button("✏️ AI로 수정하기", use_container_width=True):
                    if edit_instruction:
                        with st.spinner("초안을 수정하고 있습니다..."):
                            revised = edit_draft_with_instruction(edited_draft, edit_instruction)
                            if revised:
                                st.session_state.drafts[st.session_state.current_section] = revised
                                st.rerun()
                    else:
                        st.warning("수정 지시사항을 입력해주세요.")

            with col_edit2:
                if st.button("💬 피드백 받기", use_container_width=True):
                    with st.spinner("피드백을 생성하고 있습니다..."):
                        feedback = get_feedback(edited_draft, "draft")
                        if feedback:
                            st.markdown("##### 📝 AI 피드백")
                            st.markdown(feedback)

            with col_edit3:
                if st.button("✨ 문장 다듬기", use_container_width=True):
                    with st.spinner("문장을 다듬고 있습니다..."):
                        refined = refine_text(edited_draft)
                        if refined:
                            st.session_state.drafts[st.session_state.current_section] = refined
                            st.rerun()

    with col2:
        st.markdown("### 🛠️ 보조 기능")

        # 스토리텔링 추가
        with st.expander("📖 스토리텔링 추가"):
            experience_input = st.text_area(
                "내 경험을 간단히 입력",
                placeholder="예: 나는 5년간 실패만 했다. 그러다 한 가지를 바꿨다.",
                height=100
            )
            if st.button("스토리 생성"):
                if experience_input:
                    with st.spinner("스토리를 생성하고 있습니다..."):
                        story = add_storytelling(experience_input)
                        if story:
                            st.markdown(story)
                else:
                    st.warning("경험을 입력해주세요.")

        # 문장 다듬기
        with st.expander("✨ 문장 다듬기"):
            text_to_refine = st.text_area(
                "다듬을 문장 입력",
                height=100
            )
            if st.button("문장 다듬기"):
                if text_to_refine:
                    with st.spinner("문장을 다듬고 있습니다..."):
                        refined = refine_text(text_to_refine)
                        if refined:
                            st.markdown(refined)
                else:
                    st.warning("다듬을 문장을 입력해주세요.")

        # 저장된 초안 목록
        if st.session_state.drafts:
            st.markdown("---")
            st.markdown("### 📁 저장된 초안")
            for key in st.session_state.drafts.keys():
                if st.button(f"📄 {key}", key=f"load_{key}"):
                    st.session_state.current_section = key
                    st.rerun()

    # 네비게이션
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← 이전 단계"):
            st.session_state.current_step = 3
            st.rerun()
    with col2:
        if st.button("다음 단계로 →", use_container_width=True):
            st.session_state.current_step = 5
            st.rerun()


def render_step5():
    """5단계: 출간기획서"""
    st.markdown('<p class="step-header">5단계: 출간기획서</p>', unsafe_allow_html=True)
    st.markdown("출판사에 제출할 기획서를 생성합니다.")

    col1, col2 = st.columns([2, 1])

    with col1:
        # 저자 정보 입력
        with st.expander("📝 저자 정보 입력", expanded=not st.session_state.generated_proposal):
            profession = st.text_input(
                "직업/전문 분야",
                value=st.session_state.author_info.get("profession", ""),
                placeholder="예: 부동산 컨설턴트, 10년차 마케터"
            )
            career = st.text_area(
                "경력/전문성",
                value=st.session_state.author_info.get("career", ""),
                placeholder="예: 부동산 투자 15년, 자산 100억 달성, 수강생 500명 배출",
                height=80
            )
            achievements = st.text_area(
                "대표 성과",
                value=st.session_state.author_info.get("achievements", ""),
                placeholder="예: 베스트셀러 저자, TV 출연, 강연 100회",
                height=80
            )
            sns = st.text_input(
                "SNS/블로그",
                value=st.session_state.author_info.get("sns", ""),
                placeholder="예: 인스타 1만, 유튜브 5천, 블로그 월 10만"
            )
            contact = st.text_input(
                "연락처",
                value=st.session_state.author_info.get("contact", ""),
                placeholder="예: email@example.com / 010-1234-5678"
            )

            if st.button("💾 저자 정보 저장"):
                st.session_state.author_info = {
                    "name": st.session_state.book_info.get("name", ""),
                    "profession": profession,
                    "career": career,
                    "achievements": achievements,
                    "sns": sns,
                    "contact": contact,
                }
                st.success("저자 정보가 저장되었습니다.")

        # 기획서 생성
        if st.button("📄 출간기획서 생성하기", use_container_width=True):
            if not st.session_state.author_info:
                st.warning("먼저 저자 정보를 저장해주세요.")
            else:
                with st.spinner("기획서를 생성하고 있습니다... (약 1분 소요)"):
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
                height=500
            )
            st.session_state.generated_proposal = edited_proposal

            # 다운로드
            st.download_button(
                label="📥 기획서 다운로드 (마크다운)",
                data=edited_proposal,
                file_name=f"{st.session_state.selected_title}_출간기획서.md",
                mime="text/markdown",
                use_container_width=True
            )

    with col2:
        st.markdown("### 💡 기획서 팁")
        st.info("""
        **좋은 기획서 조건:**
        - A4 2페이지 분량
        - 5분 안에 읽을 수 있게
        - 구체적인 숫자 포함
        - 차별점 명확히

        **필수 7요소:**
        1. 제목 & 부제목
        2. 기획 의도
        3. 타겟 독자
        4. 시장 분석
        5. 목차 요약
        6. 저자 소개
        7. 마케팅 계획
        """)

        if st.session_state.generated_proposal:
            if st.button("🔄 기획서 다시 생성"):
                with st.spinner("기획서를 다시 생성하고 있습니다..."):
                    result = generate_proposal(
                        st.session_state.book_info,
                        st.session_state.author_info
                    )
                    if result:
                        st.session_state.generated_proposal = result
                        st.rerun()

    # 네비게이션
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← 이전 단계"):
            st.session_state.current_step = 4
            st.rerun()
    with col2:
        if st.button("다음 단계로 →", use_container_width=True):
            st.session_state.current_step = 6
            st.rerun()


def render_step6():
    """6단계: 랜딩페이지"""
    st.markdown('<p class="step-header">6단계: 랜딩페이지</p>', unsafe_allow_html=True)
    st.markdown("책 홍보용 랜딩페이지 카피를 생성합니다.")

    col1, col2 = st.columns([2, 1])

    with col1:
        # 웨비나 정보 입력
        with st.expander("📝 웨비나/이벤트 정보 입력", expanded=not st.session_state.generated_landing_page):
            webinar_title = st.text_input(
                "웨비나 제목",
                value=st.session_state.webinar_info.get("webinar_title", ""),
                placeholder="예: 2달 만에 책 쓰는 비밀 공개 웨비나"
            )
            datetime = st.text_input(
                "일시",
                value=st.session_state.webinar_info.get("datetime", ""),
                placeholder="예: 2025년 2월 15일 (토) 오후 2시"
            )
            speaker = st.text_input(
                "강사",
                value=st.session_state.webinar_info.get("speaker", st.session_state.book_info.get("name", "")),
                placeholder="예: 홍길동 (책쓰기 코치)"
            )
            content = st.text_area(
                "주요 내용",
                value=st.session_state.webinar_info.get("content", ""),
                placeholder="예: 1) 99%가 실패하는 이유 2) AI로 9배 빨리 쓰는 법 3) 오늘 바로 시작하는 액션플랜",
                height=80
            )
            bonus = st.text_area(
                "보너스/혜택",
                value=st.session_state.webinar_info.get("bonus", ""),
                placeholder="예: 제목 공식 10가지 PDF, AI 프롬프트 7종, 목차 템플릿",
                height=80
            )

            if st.button("💾 웨비나 정보 저장"):
                st.session_state.webinar_info = {
                    "webinar_title": webinar_title,
                    "datetime": datetime,
                    "speaker": speaker,
                    "content": content,
                    "bonus": bonus,
                }
                st.success("웨비나 정보가 저장되었습니다.")

        # 랜딩페이지 생성
        if st.button("🎨 랜딩페이지 카피 생성하기", use_container_width=True):
            if not st.session_state.webinar_info:
                st.warning("먼저 웨비나 정보를 저장해주세요.")
            else:
                with st.spinner("랜딩페이지를 생성하고 있습니다... (약 1분 소요)"):
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
                "카피 수정 (직접 편집 가능)",
                value=st.session_state.generated_landing_page,
                height=500
            )
            st.session_state.generated_landing_page = edited_landing

            # 다운로드
            st.download_button(
                label="📥 랜딩페이지 카피 다운로드",
                data=edited_landing,
                file_name=f"{st.session_state.selected_title}_랜딩페이지.md",
                mime="text/markdown",
                use_container_width=True
            )

    with col2:
        st.markdown("### 💡 랜딩페이지 구조")
        st.info("""
        **10개 섹션:**
        1. 헤더 (Hero)
        2. 문제 제기
        3. 해결책 제시
        4. 강사 소개
        5. 커리큘럼
        6. 후기/성과
        7. 보너스/혜택
        8. 신청 폼
        9. FAQ
        10. 최종 CTA

        **전환율 높이는 팁:**
        - 긴급성/희소성
        - 구체적 숫자
        - 사회적 증거
        """)

        if st.session_state.generated_landing_page:
            if st.button("🔄 랜딩페이지 다시 생성"):
                with st.spinner("랜딩페이지를 다시 생성하고 있습니다..."):
                    result = generate_landing_page(
                        st.session_state.book_info,
                        st.session_state.webinar_info
                    )
                    if result:
                        st.session_state.generated_landing_page = result
                        st.rerun()

    # 네비게이션
    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("← 이전 단계"):
            st.session_state.current_step = 5
            st.rerun()
    with col2:
        if st.button("다음 단계로 →", use_container_width=True):
            st.session_state.current_step = 7
            st.rerun()


def render_step7():
    """7단계: 결과물 다운로드"""
    st.markdown('<p class="step-header">7단계: 결과물 다운로드</p>', unsafe_allow_html=True)
    st.markdown("작성한 내용을 마크다운 파일로 다운로드할 수 있습니다.")

    # 전체 원고 생성
    full_manuscript = f"""# {st.session_state.selected_title}

**작성자:** {st.session_state.book_info.get('name', '')}

---

## 책 정보

- **주제:** {st.session_state.book_info.get('topic', '')}
- **타겟 독자:** {st.session_state.book_info.get('target_reader', '')}
- **핵심 메시지:** {st.session_state.book_info.get('core_message', '')}
- **글쓰기 톤:** {st.session_state.book_info.get('tone', '')}

---

## 목차

{st.session_state.generated_toc}

---

## 초안

"""

    # 초안 추가
    for section_key, draft in st.session_state.drafts.items():
        full_manuscript += f"""
### {section_key}

{draft}

---
"""

    # 미리보기
    with st.expander("📄 전체 원고 미리보기", expanded=True):
        st.markdown(full_manuscript)

    # 다운로드 버튼들
    st.markdown("### 📥 다운로드")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.download_button(
            label="📚 전체 원고 다운로드",
            data=full_manuscript,
            file_name=f"{st.session_state.selected_title}_전체원고.md",
            mime="text/markdown",
            use_container_width=True
        )

    with col2:
        toc_only = f"""# {st.session_state.selected_title}

## 목차

{st.session_state.generated_toc}
"""
        st.download_button(
            label="📋 목차만 다운로드",
            data=toc_only,
            file_name=f"{st.session_state.selected_title}_목차.md",
            mime="text/markdown",
            use_container_width=True
        )

    with col3:
        title_info = f"""# 책 제목 정보

**최종 제목:** {st.session_state.selected_title}

## 생성된 제목 후보

{st.session_state.generated_titles}
"""
        st.download_button(
            label="🏷️ 제목 정보 다운로드",
            data=title_info,
            file_name=f"제목정보.md",
            mime="text/markdown",
            use_container_width=True
        )

    # 통계
    st.markdown("---")
    st.markdown("### 📊 작성 통계")

    col1, col2, col3 = st.columns(3)

    with col1:
        total_chars = sum(
            len(d.replace(" ", "").replace("\n", ""))
            for d in st.session_state.drafts.values()
        )
        st.metric("총 글자 수", f"{total_chars:,}자")

    with col2:
        st.metric("작성된 꼭지 수", f"{len(st.session_state.drafts)}개")

    with col3:
        estimated_pages = total_chars // 1800  # 한 페이지 약 1800자 기준
        st.metric("예상 페이지", f"약 {estimated_pages}쪽")

    # 처음으로
    st.markdown("---")
    if st.button("🔄 처음부터 다시 시작", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # 이전 단계
    if st.button("← 이전 단계"):
        st.session_state.current_step = 6
        st.rerun()


def render_chatbot():
    """AI 코치 챗봇 렌더링"""
    st.markdown("### 💬 AI 책쓰기 코치")
    st.markdown("책쓰기에 대해 무엇이든 물어보세요!")

    # 대화 히스토리 표시
    chat_container = st.container()
    with chat_container:
        for msg in st.session_state.chat_messages:
            if msg["role"] == "user":
                st.markdown(f"**🧑 나:** {msg['content']}")
            else:
                st.markdown(f"**🤖 코치:** {msg['content']}")
                st.markdown("---")

    # 입력 영역
    with st.form("chat_form", clear_on_submit=True):
        user_input = st.text_area(
            "메시지 입력",
            placeholder="예: 제목을 더 강렬하게 바꾸고 싶어요. 어떻게 하면 좋을까요?",
            height=100,
            label_visibility="collapsed"
        )
        col1, col2 = st.columns([3, 1])
        with col1:
            send_btn = st.form_submit_button("보내기", use_container_width=True)
        with col2:
            if st.form_submit_button("대화 초기화"):
                st.session_state.chat_messages = []
                st.rerun()

    if send_btn and user_input:
        # 사용자 메시지 추가
        st.session_state.chat_messages.append({
            "role": "user",
            "content": user_input
        })

        # AI 응답 생성
        with st.spinner("코치가 답변을 작성하고 있습니다..."):
            response = chat_with_coach(
                st.session_state.chat_messages,
                st.session_state.book_info
            )
            if response:
                st.session_state.chat_messages.append({
                    "role": "assistant",
                    "content": response
                })
        st.rerun()

    # 빠른 질문 버튼
    st.markdown("#### 💡 자주 묻는 질문")
    quick_questions = [
        "제목을 더 매력적으로 만들려면?",
        "글이 막힐 때 어떻게 하나요?",
        "초안을 어떻게 수정해야 할까요?",
        "스토리텔링을 잘 하는 방법은?",
    ]

    cols = st.columns(2)
    for i, q in enumerate(quick_questions):
        with cols[i % 2]:
            if st.button(q, key=f"quick_{i}", use_container_width=True):
                st.session_state.chat_messages.append({
                    "role": "user",
                    "content": q
                })
                with st.spinner("코치가 답변을 작성하고 있습니다..."):
                    response = chat_with_coach(
                        st.session_state.chat_messages,
                        st.session_state.book_info
                    )
                    if response:
                        st.session_state.chat_messages.append({
                            "role": "assistant",
                            "content": response
                        })
                st.rerun()


def main():
    """메인 함수"""
    init_session_state()
    render_sidebar()

    # 챗봇 모드
    if st.session_state.show_chatbot:
        col1, col2 = st.columns([2, 1])
        with col1:
            # 헤더
            st.markdown('<p class="main-header">📚 책쓰기 코칭 자동화</p>', unsafe_allow_html=True)
            st.markdown("AI와 함께 제목, 목차, 초안을 완성하세요!")
            st.markdown("---")

            # 현재 단계 렌더링
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
        # 헤더
        st.markdown('<p class="main-header">📚 책쓰기 코칭 자동화</p>', unsafe_allow_html=True)
        st.markdown("AI와 함께 제목, 목차, 초안을 완성하세요!")
        st.markdown("---")

        # 현재 단계 렌더링
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

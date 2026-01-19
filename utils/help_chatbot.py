"""작가의집 AI 코칭 도움 시스템"""
import streamlit as st
from utils.claude_client import chat_with_coach


# 단계별 맥락 정보 (전문적이면서 친근한 코칭 톤)
STEP_CONTEXTS = {
    1: {
        "name": "책의 방향 설정",
        "description": "책의 콘셉트와 타겟을 명확히 정의하는 단계",
        "common_issues": [
            "어떤 주제로 책을 써야 할지 모르겠어요",
            "타겟 독자를 어떻게 구체화하나요?",
            "핵심 메시지가 너무 평범한 것 같아요",
        ],
        "help_tips": [
            "코치 팁: 친구나 동료에게 자주 조언해주는 주제가 책 소재입니다. 남들이 당신에게 자주 묻는 것이 무엇인가요?",
            "코치 팁: 타겟 독자는 '3년 전의 나'라고 생각해보세요. 그때 어떤 책이 있었으면 좋았을까요?",
            "코치 팁: 핵심 메시지는 '독자가 책을 덮고 단 하나만 기억한다면?'으로 생각하세요.",
        ],
    },
    2: {
        "name": "책 제목 결정",
        "description": "베스트셀러 공식을 활용한 제목 선정",
        "common_issues": [
            "AI가 추천한 제목이 마음에 안 들어요",
            "어떤 제목이 더 효과적인지 판단이 어려워요",
            "직접 제목을 만들고 싶은데 잘 안 돼요",
        ],
        "help_tips": [
            "코치 팁: 좋은 제목은 '서점 3초 테스트'를 통과해야 합니다. 서점에서 3초 만에 눈에 띄나요?",
            "코치 팁: 여러 제목의 장점을 조합해보세요. A제목의 키워드 + B제목의 구조 = 새 제목",
            "코치 팁: 숫자가 들어간 제목은 구체성을 주고, 질문형 제목은 호기심을 자극합니다.",
        ],
    },
    3: {
        "name": "목차 구성",
        "description": "5부 40장 체계적 목차 설계",
        "common_issues": [
            "목차 구조(Why-What-How-Do-Future)가 어렵게 느껴져요",
            "챕터 제목을 더 매력적으로 바꾸고 싶어요",
            "챕터 순서가 맞는지 확신이 안 서요",
        ],
        "help_tips": [
            "코치 팁: Part 1(Why)은 독자의 고민을 건드려 '이 책 꼭 읽어야겠다'고 느끼게 하는 부분입니다.",
            "코치 팁: 목차의 챕터 제목은 호기심을 유발하는 문장형이 좋습니다. '~의 비밀', '왜 ~인가'",
            "코치 팁: 앞 챕터를 읽어야 뒤 챕터를 이해할 수 있는 논리적 흐름이 중요합니다.",
        ],
    },
    4: {
        "name": "초안 작성",
        "description": "챕터별 2,000자 초안 생성 및 수정",
        "common_issues": [
            "첫 문장을 어떻게 시작해야 할지 막막해요",
            "AI가 쓴 글이 너무 일반적이에요",
            "내 경험을 어떻게 녹여야 할지 모르겠어요",
        ],
        "help_tips": [
            "코치 팁: 독자의 공감을 얻는 질문으로 시작하세요. '혹시 ~한 경험 있으신가요?'",
            "코치 팁: AI 초안은 뼈대입니다. 당신의 실제 경험, 사례, 감정을 추가하면 살아납니다.",
            "코치 팁: 한 문장 40자 이내, 한 문단 3~4문장이 읽기 좋습니다. 짧게 끊어 쓰세요.",
        ],
    },
    5: {
        "name": "출간기획서",
        "description": "출판사 투고용 기획서 작성",
        "common_issues": [
            "저자 소개를 어떻게 써야 전문적으로 보일까요?",
            "기획서에서 가장 중요한 포인트가 뭔가요?",
            "경쟁 도서 분석은 어떻게 하나요?",
        ],
        "help_tips": [
            "코치 팁: 저자 소개는 '왜 이 사람이 이 주제로 책을 쓸 자격이 있는가'를 답해야 합니다.",
            "코치 팁: 편집자는 '이 책이 팔릴까?'가 가장 궁금합니다. 시장성과 차별점을 강조하세요.",
            "코치 팁: 숫자로 된 성과(경력, 수강생 수, SNS 팔로워 등)는 신뢰도를 높입니다.",
        ],
    },
    6: {
        "name": "마케팅 랜딩페이지",
        "description": "책 홍보 및 웨비나 페이지 카피 작성",
        "common_issues": [
            "랜딩페이지가 꼭 필요한가요?",
            "효과적인 CTA(행동 유도 버튼) 문구는 뭔가요?",
            "웨비나 기획은 어떻게 하나요?",
        ],
        "help_tips": [
            "코치 팁: 랜딩페이지는 책 출간 전 독자 반응을 테스트하고 사전 예약을 받는 도구입니다.",
            "코치 팁: CTA는 '무료 참석 신청하기'처럼 독자가 얻는 혜택 + 행동 동사 조합이 효과적입니다.",
            "코치 팁: 이 단계는 선택사항입니다. 출판이 목표라면 바로 다음 단계로 넘어가셔도 됩니다.",
        ],
    },
    7: {
        "name": "원고 다운로드",
        "description": "완성된 원고 파일 다운로드",
        "common_issues": [
            "어떤 파일 형식으로 다운받는 게 좋을까요?",
            "다운로드 후 출판사 투고는 어떻게 하나요?",
            "원고를 더 수정하고 싶은데 어떻게 하나요?",
        ],
        "help_tips": [
            "코치 팁: Word/HWP 편집용은 TXT, 블로그/노션용은 Markdown, 미리보기용은 HTML을 추천합니다.",
            "코치 팁: 출판사마다 선호 형식이 다릅니다. 투고 전 해당 출판사 가이드라인을 확인하세요.",
            "코치 팁: 수정이 필요하면 4단계로 돌아가서 원하는 챕터를 선택해 편집할 수 있습니다.",
        ],
    },
}


# 자주 묻는 질문 (FAQ) - 전문 코칭 톤
FAQ_QUESTIONS = [
    {
        "question": "책 주제를 어떻게 정해야 하나요?",
        "answer": """
        <b>코치의 조언</b>

        책 주제를 찾는 3가지 질문:

        <b>1. 전문성 질문</b>
        "사람들이 나에게 자주 물어보는 것은?"
        → 당신이 의식하지 못해도 남들은 알고 있는 강점입니다.

        <b>2. 열정 질문</b>
        "시간 가는 줄 모르고 이야기하는 주제는?"
        → 열정이 있어야 6만자를 끝까지 쓸 수 있습니다.

        <b>3. 시장성 질문</b>
        "이 주제의 책을 살 사람이 있을까?"
        → 서점이나 온라인에서 유사 도서를 검색해보세요.

        세 가지가 겹치는 영역이 당신의 책 주제입니다.
        """,
        "icon": "🎯"
    },
    {
        "question": "제목을 더 매력적으로 바꾸고 싶어요",
        "answer": """
        <b>베스트셀러 제목 개선 공식</b>

        <b>1. 숫자 추가</b>
        "성공하는 법" → "3개월 만에 성공하는 법"
        숫자는 구체성과 신뢰감을 줍니다.

        <b>2. 타겟 명시</b>
        "투자의 기술" → "30대 직장인을 위한 투자의 기술"
        '이 책 내 얘기다!' 느낌을 줍니다.

        <b>3. 호기심 자극</b>
        "시간 관리" → "왜 성공한 사람들은 새벽에 일어날까?"
        질문형은 답을 알고 싶게 만듭니다.

        <b>4. 조합하기</b>
        AI 추천 제목 A의 키워드 + B의 구조를 조합해보세요.
        """,
        "icon": "💡"
    },
    {
        "question": "글쓰기가 막힐 때 어떻게 하나요?",
        "answer": """
        <b>작가들의 글쓰기 막힘 극복법</b>

        <b>1. 일단 쓰기 (가장 중요!)</b>
        완벽한 문장을 쓰려고 하지 마세요.
        "일단 쓰고, 나중에 고친다"가 프로 작가의 원칙입니다.

        <b>2. 말하듯이 쓰기</b>
        "이 내용을 친구에게 설명한다면?" 생각하며 써보세요.
        음성 녹음 후 텍스트로 변환하는 것도 좋은 방법입니다.

        <b>3. AI 초안 활용</b>
        '초안 생성' 버튼으로 뼈대를 만들고,
        당신의 경험과 사례를 추가하세요.

        <b>4. 작은 목표 설정</b>
        "오늘 2,000자" 대신 "오늘 500자만" 목표로 시작하세요.
        """,
        "icon": "✍️"
    },
    {
        "question": "AI가 쓴 글이 마음에 안 들어요",
        "answer": """
        <b>AI 초안을 '내 글'로 바꾸는 방법</b>

        AI 초안은 <b>뼈대</b>입니다. 살을 붙이는 건 당신의 역할이에요.

        <b>1. 내 경험 추가</b>
        "저도 처음에는..." "실제로 제가 겪은 일인데..."
        → 구체적인 에피소드가 글에 생명을 불어넣습니다.

        <b>2. 구체적 숫자/사례</b>
        "많은 사람들이" → "제가 코칭한 300명 중 80%가"
        → 숫자는 신뢰감을 높입니다.

        <b>3. 톤 조절</b>
        딱딱하면 → "~하세요", "~해보시는 건 어떨까요?"
        너무 가벼우면 → 전문 용어나 인용 추가

        <b>4. 과감한 삭제</b>
        AI가 쓴 내용 중 "이건 아닌데?"라는 부분은 과감히 삭제하세요.
        """,
        "icon": "🔧"
    },
    {
        "question": "진행 상황을 저장하고 싶어요",
        "answer": """
        <b>작업 저장 방법</b>

        <b>자동 저장</b>
        작가의집은 주요 작업(제목 선택, 목차 생성, 초안 완료)마다 자동 저장됩니다.

        <b>수동 저장</b>
        왼쪽 사이드바 → '진행상황 저장' 클릭
        → JSON 파일로 다운로드됩니다.

        <b>불러오기</b>
        시작 화면에서 '이어서 쓰기' 선택
        → 저장된 프로젝트 목록에서 선택

        <b>최종 원고 다운로드</b>
        7단계에서 TXT/Markdown/HTML 형식으로 다운로드 가능

        <b>팁:</b> 중요한 작업 후에는 수동 저장을 권장합니다.
        """,
        "icon": "💾"
    },
    {
        "question": "출판사에 어떻게 투고하나요?",
        "answer": """
        <b>출판사 투고 가이드</b>

        <b>1. 출간기획서 준비 (5단계)</b>
        작가의집에서 생성한 기획서를 바탕으로 완성하세요.
        - 책 소개 (왜 이 책이 필요한가)
        - 저자 소개 (왜 내가 쓸 자격이 있는가)
        - 목차 및 샘플 원고

        <b>2. 투고 대상 선정</b>
        - 유사 도서를 출판한 출판사 리스트업
        - 출판사 홈페이지에서 투고 가이드 확인

        <b>3. 투고 방법</b>
        - 대부분 이메일 투고 (기획서 + 샘플 원고 2-3장)
        - 출판사별 형식 요구사항 준수

        <b>4. 대기 기간</b>
        - 보통 2-4주 소요
        - 무응답 시 다른 출판사에 동시 투고 가능

        <b>팁:</b> 여러 출판사에 동시 투고해도 괜찮습니다.
        """,
        "icon": "📮"
    },
    {
        "question": "책 분량이 부족한 것 같아요",
        "answer": """
        <b>원고 분량 늘리는 방법</b>

        작가의집 기본 구조(40장 x 1,500자)는 6만자입니다.
        일반적인 자기계발서 분량이에요.

        <b>분량을 늘리고 싶다면:</b>

        <b>1. 사례 추가</b>
        각 챕터에 실제 사례 1-2개를 추가하세요.
        "실제로 A씨는..." 형태의 구체적 이야기

        <b>2. 데이터/연구 인용</b>
        주장을 뒷받침하는 통계나 연구 결과

        <b>3. 실습/워크시트</b>
        독자가 직접 해볼 수 있는 질문, 체크리스트

        <b>4. 저자 에피소드</b>
        당신의 실제 경험, 실패담, 성공담

        <b>팁:</b> 억지로 늘리면 독자가 느낍니다.
        정말 필요한 내용만 추가하세요.
        """,
        "icon": "📚"
    },
    {
        "question": "이 단계를 건너뛰어도 되나요?",
        "answer": """
        <b>단계별 필수/선택 안내</b>

        <b>필수 단계 (건너뛸 수 없음)</b>
        - 1단계: 책 정보 입력
        - 2단계: 제목 선택
        - 3단계: 목차 생성
        - 4단계: 초안 작성 (최소 1개 챕터)

        <b>선택 단계 (건너뛸 수 있음)</b>
        - 5단계: 출간기획서 → 자가출판이면 생략 가능
        - 6단계: 랜딩페이지 → 마케팅 불필요하면 생략

        <b>언제든 돌아올 수 있어요</b>
        나중에 필요하면 해당 단계로 돌아가서 작업할 수 있습니다.

        <b>추천:</b> 처음 쓰는 책이라면 5단계(출간기획서)까지는 완료하세요.
        출판 여부와 관계없이 책을 객관적으로 정리하는 데 도움이 됩니다.
        """,
        "icon": "⏭️"
    },
]


def get_step_context(current_step: int) -> dict:
    """현재 단계의 맥락 정보 가져오기"""
    return STEP_CONTEXTS.get(current_step, STEP_CONTEXTS[1])


def get_contextual_help(current_step: int) -> str:
    """현재 단계에 맞는 도움말 생성"""
    context = get_step_context(current_step)
    tips = context.get("help_tips", [])

    if tips:
        import random
        return random.choice(tips)
    return "무엇이든 편하게 질문해 주세요."


def render_floating_chatbot_button():
    """플로팅 챗봇 버튼 CSS (우측 하단) - 모든 화면에서 접근 가능"""
    st.markdown("""
    <style>
    /* 플로팅 챗봇 버튼 - 모든 화면에서 보이도록 개선 */
    .floating-chat-btn {
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 9999;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 50px;
        padding: 15px 25px;
        font-size: 1.1rem;
        font-weight: bold;
        cursor: pointer;
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
        transition: all 0.3s ease;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .floating-chat-btn:hover {
        transform: translateY(-3px);
        box-shadow: 0 6px 25px rgba(102, 126, 234, 0.5);
    }
    .floating-chat-btn:active {
        transform: translateY(0);
    }
    /* 알림 뱃지 */
    .chat-badge {
        position: absolute;
        top: -5px;
        right: -5px;
        background: #FF5252;
        color: white;
        border-radius: 50%;
        width: 24px;
        height: 24px;
        font-size: 0.8rem;
        display: flex;
        align-items: center;
        justify-content: center;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { transform: scale(1); }
        50% { transform: scale(1.1); }
        100% { transform: scale(1); }
    }
    /* 챗봇 창 - 화면 크기에 맞게 반응형 */
    .chatbot-window {
        position: fixed;
        bottom: 100px;
        right: 30px;
        width: min(380px, 90vw);
        max-height: min(500px, 70vh);
        background: white;
        border-radius: 16px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        z-index: 9998;
        overflow: hidden;
        display: none;
    }
    .chatbot-window.open {
        display: block;
        animation: slideUp 0.3s ease;
    }
    @keyframes slideUp {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    .chatbot-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .chatbot-body {
        padding: 20px;
        max-height: 350px;
        overflow-y: auto;
    }
    .chat-message {
        margin: 10px 0;
        padding: 12px 16px;
        border-radius: 12px;
        max-width: 85%;
    }
    .chat-message.user {
        background: #E3F2FD;
        margin-left: auto;
    }
    .chat-message.assistant {
        background: #F5F5F5;
    }
    /* FAQ 버튼 스타일 - 더 친근하게 */
    .faq-btn {
        background: linear-gradient(135deg, #F0F4FF 0%, #E8ECFF 100%);
        border: 2px solid #667eea;
        border-radius: 20px;
        padding: 10px 18px;
        margin: 4px;
        font-size: 0.95rem;
        cursor: pointer;
        transition: all 0.3s ease;
        font-weight: 500;
    }
    .faq-btn:hover {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        transform: scale(1.02);
        border-color: transparent;
    }
    /* 모바일 대응 */
    @media (max-width: 768px) {
        .floating-chat-btn {
            bottom: 20px;
            right: 20px;
            padding: 12px 20px;
            font-size: 1rem;
        }
        .chatbot-window {
            right: 10px;
            bottom: 80px;
            width: calc(100vw - 20px);
        }
    }
    </style>
    """, unsafe_allow_html=True)


def render_enhanced_chatbot(current_step: int, book_info: dict = None):
    """작가의집 AI 코칭 도움 시스템"""
    context = get_step_context(current_step)

    # 전문적인 코치 헤더 - 더 눈에 띄게 개선
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white; padding: 1.5rem; border-radius: 16px; margin-bottom: 1rem;
                box-shadow: 0 4px 20px rgba(102, 126, 234, 0.3);">
        <div style="display: flex; align-items: center; gap: 1rem;">
            <div style="background: rgba(255,255,255,0.2); border-radius: 50%;
                        width: 50px; height: 50px; display: flex; align-items: center;
                        justify-content: center; font-size: 1.8rem;">
                🤖
            </div>
            <div>
                <h3 style="margin: 0; color: white; font-size: 1.3rem; font-weight: 700;">
                    AI 코칭 도우미
                </h3>
                <p style="margin: 5px 0 0 0; font-size: 0.9rem; opacity: 0.9;">
                    무엇이든 질문해 주세요. 책쓰기 전문 AI가 도와드립니다.
                </p>
            </div>
        </div>
        <div style="background: rgba(255,255,255,0.15); border-radius: 10px;
                    padding: 0.8rem; margin-top: 1rem;">
            <p style="margin: 0; font-size: 0.95rem;">
                <strong>현재 단계:</strong> {context['name']}<br>
                <span style="opacity: 0.85;">{context['description']}</span>
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 현재 단계 맥락 안내 - 전문 코치 톤
    with st.container():
        tip = get_contextual_help(current_step)
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #F8F9FA 0%, #E9ECEF 100%);
                    padding: 1rem 1.2rem; border-radius: 0 0 16px 16px;
                    margin-top: 0; border: 2px solid #DEE2E6; border-top: none;
                    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);">
            <p style="margin: 0; font-size: 1rem; line-height: 1.5; color: #495057;">
                {tip}
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("")

    # FAQ 버튼들 - 전문적인 스타일
    st.markdown("""
    <h3 style="color: #2C3E50; margin-bottom: 0.3rem;">
        자주 묻는 질문
    </h3>
    <p style="color: #6C757D; font-size: 0.9rem; margin-top: 0;">
        질문을 선택하면 전문 코치의 답변을 확인할 수 있습니다.
    </p>
    """, unsafe_allow_html=True)

    # 2열로 FAQ 버튼 배치 - 키 충돌 방지
    cols = st.columns(2)
    for idx, faq in enumerate(FAQ_QUESTIONS):
        with cols[idx % 2]:
            if st.button(
                f"{faq['icon']} {faq['question']}",
                key=f"help_faq_btn_{idx}_{current_step}",
                use_container_width=True
            ):
                st.session_state.show_faq_answer = idx
                st.rerun()

    # FAQ 답변 표시 - 더 보기 쉽게
    if "show_faq_answer" in st.session_state and st.session_state.show_faq_answer is not None:
        faq_idx = st.session_state.show_faq_answer
        if 0 <= faq_idx < len(FAQ_QUESTIONS):
            faq = FAQ_QUESTIONS[faq_idx]

            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
                        padding: 1.5rem; border-radius: 16px;
                        margin: 1rem 0; border-left: 5px solid #4CAF50;
                        box-shadow: 0 3px 10px rgba(76, 175, 80, 0.15);">
                <h4 style="margin: 0 0 0.8rem 0; color: #2E7D32; font-size: 1.1rem;">
                    {faq['icon']} {faq['question']}
                </h4>
                <div style="font-size: 0.95rem; line-height: 1.7; color: #333;">
                    {faq['answer'].replace(chr(10), '<br>')}
                </div>
            </div>
            """, unsafe_allow_html=True)

            if st.button("닫기", key="close_faq_answer", use_container_width=True):
                st.session_state.show_faq_answer = None
                st.rerun()

    st.markdown("---")

    # 현재 단계 관련 문제들 - 더 명확하게
    st.markdown(f"""
    <h3 style="color: #333; margin-bottom: 0.3rem;">
        <span style="font-size: 1.3rem;">🎯</span> {context['name']} 단계에서 어려운 점
    </h3>
    """, unsafe_allow_html=True)

    common_issues = context.get("common_issues", [])
    for i, issue in enumerate(common_issues):
        issue_key = f"step_issue_{current_step}_{i}"
        if st.button(f"❓ {issue}", key=issue_key, use_container_width=True):
            # 대화 기록에 추가하고 자동 응답 생성
            if "help_chat_messages" not in st.session_state:
                st.session_state.help_chat_messages = []
            st.session_state.help_chat_messages.append({"role": "user", "content": issue})
            st.session_state.pending_help_question = issue
            st.rerun()

    st.markdown("---")

    # 자유 질문 입력
    st.markdown("""
    <h3 style="color: #333; margin-bottom: 0.3rem;">
        <span style="font-size: 1.3rem;">💬</span> 직접 질문하기
    </h3>
    <p style="color: #666; font-size: 0.9rem; margin-top: 0;">
        궁금하신 점을 자유롭게 질문해 주세요.
    </p>
    """, unsafe_allow_html=True)

    # 대화 히스토리 초기화
    if "help_chat_messages" not in st.session_state:
        st.session_state.help_chat_messages = []

    # 대기 중인 질문이 있으면 자동 응답 생성
    if "pending_help_question" in st.session_state:
        pending_q = st.session_state.pending_help_question
        del st.session_state.pending_help_question

        with st.spinner("답변을 준비하고 있습니다..."):
            try:
                response = chat_with_coach(
                    st.session_state.help_chat_messages,
                    book_info,
                    elementary_friendly=True
                )
                if response:
                    st.session_state.help_chat_messages.append({"role": "assistant", "content": response})
            except Exception as e:
                # 에러 시 기본 응답 제공
                fallback = get_fallback_response(pending_q, context)
                st.session_state.help_chat_messages.append({"role": "assistant", "content": fallback})
        st.rerun()

    # 최근 대화 표시 (최대 6개)
    recent_messages = st.session_state.help_chat_messages[-6:]
    if recent_messages:
        st.markdown('<div style="max-height: 300px; overflow-y: auto; padding: 0.5rem;">', unsafe_allow_html=True)
        for msg in recent_messages:
            if msg["role"] == "user":
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #E3F2FD 0%, #BBDEFB 100%);
                            padding: 12px 16px; border-radius: 18px 18px 4px 18px;
                            margin: 8px 0 8px 15%; font-size: 0.95rem;
                            box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <span style="font-size: 1.1rem;">🙋</span> {msg['content']}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #F5F5F5 0%, #EEEEEE 100%);
                            padding: 12px 16px; border-radius: 18px 18px 18px 4px;
                            margin: 8px 15% 8px 0; font-size: 0.95rem;
                            box-shadow: 0 1px 3px rgba(0,0,0,0.1);">
                    <span style="font-size: 1.1rem;">🤖</span> {msg['content']}
                </div>
                """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # 입력 폼
    with st.form("help_chat_form", clear_on_submit=True):
        user_input = st.text_input(
            "질문 입력",
            placeholder="질문을 입력해 주세요. 예: '어떤 내용으로 시작하면 좋을까요?'",
            label_visibility="collapsed"
        )
        col1, col2 = st.columns([3, 1])
        with col1:
            submit = st.form_submit_button("전송", use_container_width=True, type="primary")
        with col2:
            clear = st.form_submit_button("초기화", use_container_width=True)

    if clear:
        st.session_state.help_chat_messages = []
        st.rerun()

    if submit and user_input.strip():
        st.session_state.help_chat_messages.append({"role": "user", "content": user_input.strip()})
        st.session_state.pending_help_question = user_input.strip()
        st.rerun()


def get_fallback_response(question: str, context: dict) -> str:
    """API 실패 시 기본 응답 제공 - 전문 코치 톤"""
    step_name = context.get("name", "책쓰기")
    tips = context.get("help_tips", [])

    # 키워드 기반 전문적인 응답
    q_lower = question.lower()

    if "모르겠" in q_lower or "어려" in q_lower:
        base_tip = tips[0] if tips else "한 단계씩 차근차근 진행하시면 됩니다."
        return f"좋은 질문입니다. '{step_name}' 단계에서 고민하시는 분들이 많습니다. {base_tip}"
    elif "어떻게" in q_lower:
        tip = tips[1] if len(tips) > 1 else "위의 예시를 참고하시면 도움이 됩니다."
        return f"방법을 찾고 계시는군요. {tip} 궁금하신 점이 더 있으시면 구체적으로 질문해 주세요."
    elif "안 돼" in q_lower or "안돼" in q_lower:
        return "기술적인 문제가 발생한 것 같습니다. 페이지를 새로고침하시거나, 왼쪽 사이드바에서 '진행상황 저장' 후 다시 시도해 보세요. 문제가 지속되면 문의해 주세요."
    elif "좋은" in q_lower or "괜찮" in q_lower:
        return "좋은 방향으로 진행하고 계십니다. 자신감을 가지세요. 베스트셀러 작가들도 처음에는 같은 고민을 했습니다."
    else:
        fallback_tip = tips[2] if len(tips) > 2 else "FAQ를 확인하시거나 구체적인 질문을 해주시면 더 정확한 안내를 드릴 수 있습니다."
        return f"{fallback_tip} 작가님의 책쓰기 여정을 응원합니다."


def render_help_sidebar_button():
    """사이드바용 도움 버튼"""
    st.markdown("---")
    st.markdown("### 🆘 도움이 필요하시면")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💬 AI 도우미", use_container_width=True, help="AI 도우미와 상담"):
            st.session_state.show_help_chatbot = not st.session_state.get("show_help_chatbot", False)
            st.rerun()

    with col2:
        if st.button("📞 문의하기", use_container_width=True, help="담당자에게 문의"):
            st.session_state.show_contact_section = not st.session_state.get("show_contact_section", False)
            st.rerun()


def init_help_chatbot_state():
    """챗봇 상태 초기화"""
    if "help_chat_messages" not in st.session_state:
        st.session_state.help_chat_messages = []
    if "show_help_chatbot" not in st.session_state:
        st.session_state.show_help_chatbot = False
    if "show_contact_section" not in st.session_state:
        st.session_state.show_contact_section = False

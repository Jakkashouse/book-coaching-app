"""Claude API 클라이언트 모듈"""
import streamlit as st
from anthropic import Anthropic


def get_client():
    """Anthropic 클라이언트 인스턴스 반환"""
    api_key = st.secrets.get("ANTHROPIC_API_KEY")
    if not api_key:
        st.error("API 키가 설정되지 않았습니다. Streamlit Secrets에 ANTHROPIC_API_KEY를 추가해주세요.")
        st.stop()
    return Anthropic(api_key=api_key)


def generate_response(prompt: str, system_prompt: str = None, max_tokens: int = 4096) -> str:
    """
    Claude API를 통해 응답 생성

    Args:
        prompt: 사용자 프롬프트
        system_prompt: 시스템 프롬프트 (선택)
        max_tokens: 최대 토큰 수

    Returns:
        생성된 응답 텍스트
    """
    client = get_client()

    messages = [{"role": "user", "content": prompt}]

    try:
        kwargs = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": max_tokens,
            "messages": messages,
        }

        if system_prompt:
            kwargs["system"] = system_prompt

        response = client.messages.create(**kwargs)
        return response.content[0].text

    except Exception as e:
        st.error(f"API 호출 중 오류가 발생했습니다: {str(e)}")
        return None


def generate_titles(book_info: dict) -> str:
    """제목 10개 생성"""
    from prompts.templates import get_title_generation_prompt
    prompt = get_title_generation_prompt(book_info)
    system = "당신은 20년 경력의 베스트셀러 편집자입니다. 독자의 마음을 사로잡는 제목을 만드는 전문가입니다."
    return generate_response(prompt, system)


def generate_toc(book_info: dict) -> str:
    """목차 40꼭지 생성"""
    from prompts.templates import get_toc_generation_prompt
    prompt = get_toc_generation_prompt(book_info)
    system = "당신은 50권 이상 편집한 베테랑 출판 편집자입니다. 논리적이고 매력적인 책 구조를 설계하는 전문가입니다."
    return generate_response(prompt, system)


def generate_draft(book_info: dict, section_info: dict) -> str:
    """꼭지별 초안 생성 (2000자)"""
    from prompts.templates import get_draft_generation_prompt
    prompt = get_draft_generation_prompt(book_info, section_info)
    system = "당신은 베스트셀러 작가의 고스트라이터입니다. 독자가 술술 읽히는 글을 씁니다."
    return generate_response(prompt, system)


def get_feedback(content: str, feedback_type: str) -> str:
    """피드백 생성 (제목/목차/원고)"""
    from prompts.templates import get_feedback_prompt
    prompt = get_feedback_prompt(content, feedback_type)
    system = "당신은 20년 경력의 출판 편집자입니다. 건설적이고 구체적인 피드백을 제공합니다."
    return generate_response(prompt, system)


def refine_text(text: str) -> str:
    """문장 다듬기"""
    from prompts.templates import get_refine_prompt
    prompt = get_refine_prompt(text)
    system = "당신은 교열 전문 편집자입니다. 글을 더 자연스럽고 읽기 쉽게 다듬습니다."
    return generate_response(prompt, system)


def add_storytelling(experience: str) -> str:
    """스토리텔링 추가"""
    from prompts.templates import get_storytelling_prompt
    prompt = get_storytelling_prompt(experience)
    system = "당신은 스토리텔링 전문 작가입니다. 밋밋한 경험을 감동적인 이야기로 바꿉니다."
    return generate_response(prompt, system)


def chat_with_coach(messages: list, book_info: dict = None) -> str:
    """
    책쓰기 코치와 대화

    Args:
        messages: 대화 히스토리 [{"role": "user/assistant", "content": "..."}]
        book_info: 책 정보 (컨텍스트용)

    Returns:
        AI 응답 텍스트
    """
    client = get_client()

    # 시스템 프롬프트 구성
    system = """당신은 20년 경력의 책쓰기 코치입니다.
수강생이 책을 완성할 수 있도록 친절하고 구체적으로 도와줍니다.

당신의 역할:
- 책 주제, 제목, 목차에 대한 조언
- 글쓰기 막힘 해결
- 초안 피드백 및 수정 제안
- 스토리텔링 기법 안내
- 동기부여 및 격려

답변 스타일:
- 친근하고 따뜻한 톤
- 구체적인 예시 제공
- 실행 가능한 조언
- 한국어로 답변"""

    if book_info:
        context = f"""

현재 수강생 정보:
- 이름: {book_info.get('name', '미입력')}
- 책 주제: {book_info.get('topic', '미입력')}
- 타겟 독자: {book_info.get('target_reader', '미입력')}
- 핵심 메시지: {book_info.get('core_message', '미입력')}
- 선택한 제목: {book_info.get('title', '미선택')}
"""
        system += context

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            system=system,
            messages=messages,
        )
        return response.content[0].text

    except Exception as e:
        st.error(f"API 호출 중 오류가 발생했습니다: {str(e)}")
        return None


def edit_draft_with_instruction(draft: str, instruction: str) -> str:
    """
    사용자 지시에 따라 초안 수정

    Args:
        draft: 원본 초안
        instruction: 수정 지시사항

    Returns:
        수정된 초안
    """
    prompt = f"""다음 초안을 사용자의 지시에 따라 수정해주세요.

## 원본 초안:
{draft}

## 수정 지시사항:
{instruction}

## 요구사항:
1. 지시사항에 맞게 수정
2. 원본의 전체적인 톤과 스타일 유지
3. 수정된 전체 글을 출력
4. 수정한 부분은 자연스럽게 녹여서

수정된 글을 바로 출력해주세요."""

    system = "당신은 전문 편집자입니다. 작가의 의도를 살리면서 글을 수정합니다."
    return generate_response(prompt, system)

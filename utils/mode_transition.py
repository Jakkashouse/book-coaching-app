"""
모드 전환 관리 유틸리티
========================
- 채팅 모드 -> 일반 모드 전환
- 음성 모드 -> 일반 모드 전환
- 유튜브 모드 -> 일반 모드 전환
- 데이터 보존 및 복구
"""

import streamlit as st
from datetime import datetime
from typing import Dict, Any, Optional


def transfer_chat_mode_to_normal(chat_data: Dict[str, Any]) -> int:
    """
    채팅 모드 데이터를 일반 모드로 전환 - 입력 검증 강화

    Args:
        chat_data: 채팅 모드에서 수집된 데이터

    Returns:
        이동할 단계 번호
    """
    # 입력 검증
    if not chat_data or not isinstance(chat_data, dict):
        chat_data = {}

    # 책 정보 복사 - 안전한 데이터 추출
    topic = chat_data.get("topic", "")
    topic = topic if isinstance(topic, str) else ""

    st.session_state.book_info = {
        "name": str(chat_data.get("name", ""))[:100] if chat_data.get("name") else "",
        "topic": topic[:500],
        "target_reader": str(chat_data.get("target_reader", ""))[:200] if chat_data.get("target_reader") else "",
        "core_message": f"{topic}에 대한 이야기"[:500] if topic else "",
        "experience": "",
        "tone": "친절하고 따뜻한",
        "title": str(chat_data.get("title", ""))[:200] if chat_data.get("title") else "",
    }

    # 제목 복사
    if chat_data.get("title"):
        st.session_state.selected_title = chat_data["title"]

    # 생성된 제목 후보 복사
    if chat_data.get("generated_titles"):
        st.session_state.generated_titles = chat_data["generated_titles"]

    # 목차 복사
    if chat_data.get("generated_toc"):
        st.session_state.generated_toc = chat_data["generated_toc"]
    if chat_data.get("parsed_toc"):
        st.session_state.parsed_toc = chat_data["parsed_toc"]

    # 첫 번째 초안 복사
    if chat_data.get("first_draft") and st.session_state.parsed_toc:
        first_section = st.session_state.parsed_toc[0]
        key = f"{first_section['section_num']}_{first_section['section_title']}"
        st.session_state.drafts[key] = chat_data["first_draft"]
        # 다음 섹션으로 인덱스 이동
        st.session_state.current_section_index = min(1, len(st.session_state.parsed_toc) - 1)

    # 채팅 모드 비활성화
    st.session_state.chat_mode_active = False
    st.session_state.previous_mode = "chat"

    # 적절한 단계 결정
    return determine_next_step()


def transfer_voice_mode_to_normal(voice_text: str, create_book: bool = True) -> int:
    """
    음성 모드 데이터를 일반 모드로 전환

    Args:
        voice_text: 음성에서 변환된 텍스트
        create_book: True면 바로 책 만들기, False면 텍스트만 가져가기

    Returns:
        이동할 단계 번호
    """
    if create_book:
        # 음성 텍스트를 책 정보에 저장
        st.session_state.book_info["topic"] = voice_text[:500] if len(voice_text) > 500 else voice_text
        st.session_state.book_info["core_message"] = voice_text[:200] if len(voice_text) > 200 else voice_text
        st.session_state.book_info["experience"] = voice_text

        # 음성 모드 종료
        st.session_state.voice_mode_active = False
        st.session_state.previous_mode = "voice"

        # 이름이 있으면 Step 2로, 없으면 Step 1로
        if st.session_state.book_info.get("name"):
            return 2
        else:
            return 1
    else:
        # 텍스트만 가져가기
        st.session_state.voice_mode_active = False
        st.session_state.previous_mode = "voice"
        return 1


def transfer_youtube_mode_to_normal() -> int:
    """
    유튜브 모드 데이터를 일반 모드로 전환

    Returns:
        이동할 단계 번호
    """
    # 유튜브 모드에서 생성된 데이터가 이미 st.session_state에 있음
    st.session_state.youtube_mode_active = False
    st.session_state.previous_mode = "youtube"

    # 유튜브 모드 플래그 설정
    st.session_state.book_info["youtube_mode"] = True
    st.session_state.book_info["transcript"] = st.session_state.get("youtube_merged_transcript", "")

    return determine_next_step()


def determine_next_step() -> int:
    """현재 데이터 상태에 따라 적절한 다음 단계 결정 - 타입 검증 추가"""
    try:
        drafts = st.session_state.get("drafts")
        if drafts and isinstance(drafts, dict) and len(drafts) > 0:
            return 4  # 초안이 있으면 Step 4

        parsed_toc = st.session_state.get("parsed_toc")
        if parsed_toc and isinstance(parsed_toc, list) and len(parsed_toc) > 0:
            return 4  # 목차가 있으면 Step 4

        selected_title = st.session_state.get("selected_title")
        if selected_title and isinstance(selected_title, str) and selected_title.strip():
            return 3  # 제목이 있으면 Step 3

        book_info = st.session_state.get("book_info")
        if book_info and isinstance(book_info, dict) and any(book_info.values()):
            return 2  # 기본 정보가 있으면 Step 2

        return 1  # 처음부터
    except Exception:
        return 1


def safe_mode_transition(from_mode: str, to_mode: str, preserve_data: bool = True):
    """
    안전한 모드 전환 처리 - 예외 처리 강화

    Args:
        from_mode: 현재 모드 (chat, voice, youtube, normal)
        to_mode: 목표 모드
        preserve_data: 데이터 보존 여부
    """
    try:
        # 입력 검증
        valid_modes = ["chat", "voice", "youtube", "normal"]
        if not from_mode or from_mode not in valid_modes:
            from_mode = "normal"
        if not to_mode or to_mode not in valid_modes:
            to_mode = "normal"

        # 이전 모드 저장
        st.session_state.previous_mode = from_mode

        # 데이터 보존이 필요한 경우 임시 저장
        if preserve_data:
            book_info = st.session_state.get("book_info", {})
            parsed_toc = st.session_state.get("parsed_toc", [])
            drafts = st.session_state.get("drafts", {})

            st.session_state.mode_transition_data = {
                "book_info": dict(book_info) if isinstance(book_info, dict) else {},
                "selected_title": st.session_state.get("selected_title", "") or "",
                "generated_toc": st.session_state.get("generated_toc", "") or "",
                "parsed_toc": list(parsed_toc) if isinstance(parsed_toc, list) else [],
                "drafts": dict(drafts) if isinstance(drafts, dict) else {},
                "current_step": st.session_state.get("current_step", 1) or 1,
                "timestamp": datetime.now().isoformat(),
            }

        # 모드별 활성화 상태 변경
        mode_states = {
            "chat": "chat_mode_active",
            "voice": "voice_mode_active",
            "youtube": "youtube_mode_active",
            "normal": None,
        }

        # 모든 모드 비활성화
        for mode_key in mode_states.values():
            if mode_key:
                st.session_state[mode_key] = False

        # 새 모드 활성화
        if to_mode in mode_states and mode_states[to_mode]:
            st.session_state[mode_states[to_mode]] = True

    except Exception as e:
        # 전환 실패 시 기본 모드로
        st.session_state.chat_mode_active = False
        st.session_state.voice_mode_active = False
        st.session_state.youtube_mode_active = False
        print(f"모드 전환 오류: {e}")


def restore_from_mode_transition() -> bool:
    """
    모드 전환 데이터 복구

    Returns:
        복구 성공 여부
    """
    transition_data = st.session_state.get("mode_transition_data", {})
    if not transition_data:
        return False

    try:
        if transition_data.get("book_info"):
            if not st.session_state.get("book_info"):
                st.session_state.book_info = {}
            st.session_state.book_info.update(transition_data["book_info"])

        if transition_data.get("selected_title"):
            st.session_state.selected_title = transition_data["selected_title"]

        if transition_data.get("generated_toc"):
            st.session_state.generated_toc = transition_data["generated_toc"]

        if transition_data.get("parsed_toc"):
            st.session_state.parsed_toc = transition_data["parsed_toc"]

        if transition_data.get("drafts"):
            if not st.session_state.get("drafts"):
                st.session_state.drafts = {}
            st.session_state.drafts.update(transition_data["drafts"])

        return True
    except Exception:
        return False


def handle_api_error(error: Exception, context: str = "") -> str:
    """
    API 에러 처리 및 사용자 친화적 메시지 반환

    Args:
        error: 발생한 예외
        context: 에러 발생 컨텍스트

    Returns:
        사용자 친화적 에러 메시지
    """
    st.session_state.last_error = {
        "error": str(error),
        "context": context,
        "time": datetime.now().isoformat(),
    }
    st.session_state.retry_count = st.session_state.get("retry_count", 0) + 1

    error_str = str(error).lower()

    if "rate limit" in error_str or "429" in error_str:
        return "요청이 너무 많아요. 30초 후에 다시 시도해주세요!"
    elif "timeout" in error_str or "timed out" in error_str:
        return "서버 응답이 늦어요. 잠시 후 다시 시도해주세요!"
    elif "connection" in error_str or "network" in error_str:
        return "인터넷 연결을 확인해주세요!"
    elif "api key" in error_str or "authentication" in error_str:
        return "API 설정에 문제가 있어요. 관리자에게 문의해주세요."
    else:
        return f"문제가 발생했어요. 다시 시도해볼까요? (오류: {context})"


def reset_retry_count():
    """재시도 카운터 초기화"""
    st.session_state.retry_count = 0


def get_retry_count() -> int:
    """현재 재시도 횟수 반환"""
    return st.session_state.get("retry_count", 0)


def should_show_retry_warning() -> bool:
    """재시도 경고를 표시해야 하는지 확인"""
    return get_retry_count() >= 3


def init_mode_transition_state():
    """모드 전환 관련 세션 상태 초기화"""
    defaults = {
        "previous_mode": None,
        "mode_transition_data": {},
        "last_error": None,
        "retry_count": 0,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

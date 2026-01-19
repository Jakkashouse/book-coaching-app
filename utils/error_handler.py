"""
에러 핸들링 및 세션 검증 유틸리티 모듈
======================================
- 세션 상태 검증 및 복구
- 사용자 친화적 에러 메시지
- 에러 복구 옵션 제공

참고: 자동 저장 기능은 autosave_handler.py에서 담당
"""
import streamlit as st
from datetime import datetime

# 에러 메시지 (친근한 한국어)
FRIENDLY_ERROR_MESSAGES = {
    "session_expired": """
**세션이 만료되었어요!**

걱정 마세요! 자동 저장된 데이터가 있을 수 있어요.
페이지를 새로고침하면 복구할 수 있어요!
""",
    "data_lost": """
**일부 데이터가 손실되었을 수 있어요!**

자동 저장 기능이 마지막 상태를 복구할 수 있어요.
아래 버튼을 눌러 복구를 시도해보세요!
""",
    "save_failed": """
**저장에 실패했어요!**

다시 시도해볼까요?
""",
    "load_failed": """
**불러오기에 실패했어요!**

파일 형식을 확인해보세요. JSON 형식만 가능해요!
""",
    "unexpected": """
**앗! 예상치 못한 문제가 생겼어요!**

걱정 마세요! 이렇게 해봐요:
1. 페이지를 새로고침해보세요
2. 문제가 계속되면 진행상황을 저장해두세요
3. 선생님께 말씀해주세요
""",
    "api_error": """
**AI 서버와 연결이 안 돼요!**

잠시 후 다시 시도해주세요.
인터넷 연결도 확인해보세요!
""",
    "rate_limit": """
**요청이 너무 많아요!**

30초 정도 기다렸다가 다시 시도해주세요.
""",
}


def safe_session_init():
    """세션 상태 안전한 초기화 - 타입 검증 강화"""
    defaults = {
        # 책 정보
        "book_info": {},
        "selected_title": "",
        "generated_titles": "",
        "generated_toc": "",
        "parsed_toc": [],
        "drafts": {},
        "current_section_index": 0,
        "current_step": 1,

        # 저자/웨비나 정보
        "author_info": {},
        "webinar_info": {},
        "generated_proposal": "",
        "generated_landing_page": "",

        # UI 상태
        "show_chatbot": False,
        "chat_messages": [],
        "voice_mode_active": False,
        "chat_mode_active": False,
        "youtube_mode_active": False,
        "show_help_chatbot": False,
        "show_contact_section": False,

        # 폰트 크기
        "font_size": "large",

        # 저장 관련
        "last_save_time": None,

        # 버튼 중복 클릭 방지용 플래그
        "button_clicked": False,
        "last_button_click_time": None,
    }

    # 타입 검증 맵
    type_validators = {
        "book_info": dict,
        "author_info": dict,
        "webinar_info": dict,
        "drafts": dict,
        "parsed_toc": list,
        "chat_messages": list,
        "current_section_index": int,
        "current_step": int,
    }

    for key, default_value in defaults.items():
        try:
            if key not in st.session_state:
                st.session_state[key] = default_value
            else:
                # 기존 값의 타입 검증
                expected_type = type_validators.get(key)
                if expected_type and not isinstance(st.session_state[key], expected_type):
                    st.session_state[key] = default_value
        except Exception:
            pass  # 개별 키 초기화 실패는 무시


def validate_session_state():
    """
    세션 상태 유효성 검사 및 복구

    Returns:
        (is_valid, issues_list)
    """
    issues = []

    try:
        # 필수 키 확인
        required_keys = ["book_info", "current_step", "drafts"]
        for key in required_keys:
            if key not in st.session_state:
                issues.append(f"Missing: {key}")
                safe_session_init()
                break

        # 데이터 타입 검증
        if not isinstance(st.session_state.get("book_info"), dict):
            st.session_state.book_info = {}
            issues.append("Invalid book_info type")

        if not isinstance(st.session_state.get("drafts"), dict):
            st.session_state.drafts = {}
            issues.append("Invalid drafts type")

        if not isinstance(st.session_state.get("parsed_toc"), list):
            st.session_state.parsed_toc = []
            issues.append("Invalid parsed_toc type")

        # current_step 범위 검증
        step = st.session_state.get("current_step")
        if not isinstance(step, int) or step < 1 or step > 7:
            st.session_state.current_step = 1
            issues.append("Invalid current_step")

        return len(issues) == 0, issues

    except Exception as e:
        safe_session_init()
        return False, [str(e)]


def show_error_with_recovery(error_key: str, exception: Exception = None, show_recovery: bool = True):
    """에러 메시지와 복구 옵션 표시"""
    message = FRIENDLY_ERROR_MESSAGES.get(error_key, FRIENDLY_ERROR_MESSAGES["unexpected"])
    st.error(message)

    if exception:
        with st.expander("기술 정보 (선생님께 보여주세요)", expanded=False):
            st.code(f"에러 유형: {type(exception).__name__}\n에러 내용: {str(exception)[:500]}")

    if show_recovery:
        # autosave_handler의 기능 사용
        try:
            from utils.autosave_handler import get_all_backups, load_backup, restore_session_data

            backups = get_all_backups()
            if backups:
                st.info("자동 저장된 데이터가 있어요! 복구할 수 있어요.")
                for backup in backups[:3]:
                    try:
                        time_str = backup.get("saved_at", "")[:16]
                        if st.button(f"복구: {time_str}", key=f"restore_{backup['filename']}"):
                            data = load_backup(backup['filename'])
                            if data and restore_session_data(data):
                                st.success(f"복구 완료!")
                                st.rerun()
                            else:
                                st.error(f"복구 실패")
                    except Exception:
                        continue
        except ImportError:
            pass


def handle_exception(func):
    """함수 예외 처리 데코레이터"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            show_error_with_recovery("unexpected", e)
            return None
    return wrapper


def get_friendly_error_message(error_key: str) -> str:
    """에러 키에 해당하는 친근한 에러 메시지 반환"""
    return FRIENDLY_ERROR_MESSAGES.get(error_key, FRIENDLY_ERROR_MESSAGES["unexpected"])


def render_autosave_indicator():
    """자동 저장 상태 표시기 (autosave_handler로 위임)"""
    try:
        from utils.autosave_handler import render_autosave_status
        render_autosave_status()
    except ImportError:
        # 폴백: 간단한 상태 표시
        last_save = st.session_state.get("last_save_time")
        if last_save:
            st.caption(f"마지막 저장: {last_save[:16]}")


def check_autosave_reminder():
    """자동 저장 알림 확인"""
    try:
        last_save = st.session_state.get("last_save_time")
        if not last_save:
            # 작업 내용이 있는지 확인
            if st.session_state.get("drafts") or st.session_state.get("generated_toc"):
                return True
        return False
    except Exception:
        return False


# autosave_handler로 위임되는 함수들 (하위 호환성 유지)
def perform_autosave_if_needed():
    """필요시 자동 저장 수행 (autosave_handler로 위임)"""
    try:
        from utils.autosave_handler import perform_autosave_if_needed as _perform_autosave
        _perform_autosave()
    except ImportError:
        pass


def get_autosave_files():
    """자동 저장 파일 목록 (autosave_handler로 위임)"""
    try:
        from utils.autosave_handler import get_all_backups
        return get_all_backups()
    except ImportError:
        return []


def restore_from_autosave(filepath):
    """자동 저장 파일에서 복구 (autosave_handler로 위임)"""
    try:
        from utils.autosave_handler import load_backup, restore_session_data
        from pathlib import Path

        filename = Path(filepath).name if isinstance(filepath, (str, Path)) else filepath
        data = load_backup(filename)
        if data:
            success = restore_session_data(data)
            return success, data.get("saved_at", "알 수 없는 시간")
        return False, "파일을 찾을 수 없습니다"
    except Exception as e:
        return False, str(e)


# ============================================================
# 버튼 중복 클릭 방지 유틸리티
# ============================================================

def prevent_double_click(button_key: str, cooldown_seconds: float = 1.0) -> bool:
    """
    버튼 중복 클릭 방지

    Args:
        button_key: 버튼 식별 키
        cooldown_seconds: 재클릭 가능까지 대기 시간

    Returns:
        True면 클릭 허용, False면 중복 클릭으로 차단
    """
    import time

    current_time = time.time()
    last_click_key = f"last_click_{button_key}"

    # 마지막 클릭 시간 확인
    last_click = st.session_state.get(last_click_key, 0)

    if current_time - last_click < cooldown_seconds:
        return False  # 중복 클릭 차단

    # 현재 클릭 시간 저장
    st.session_state[last_click_key] = current_time
    return True


def reset_button_state(button_key: str):
    """버튼 상태 초기화"""
    last_click_key = f"last_click_{button_key}"
    if last_click_key in st.session_state:
        del st.session_state[last_click_key]


def safe_button_click(button_key: str, cooldown_seconds: float = 1.0):
    """
    안전한 버튼 클릭을 위한 컨텍스트 매니저 데코레이터

    Usage:
        if st.button("클릭"):
            if prevent_double_click("my_button"):
                # 실제 로직 수행
    """
    return prevent_double_click(button_key, cooldown_seconds)

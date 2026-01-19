"""
자동 저장 및 복구 핸들러
==========================
- 5분마다 자동 저장
- 중요 변경 시 즉시 저장
- 여러 버전 백업 (최대 5개)
- 이전 작업 복구 기능
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
import streamlit as st


# 기본 설정
AUTOSAVE_DIR = Path(__file__).parent.parent / "data" / "autosave"
MAX_BACKUPS = 5
AUTOSAVE_INTERVAL_SECONDS = 300  # 5분


def ensure_autosave_directory() -> Path:
    """자동 저장 디렉토리 생성 - 예외 처리 강화"""
    try:
        AUTOSAVE_DIR.mkdir(parents=True, exist_ok=True)
        return AUTOSAVE_DIR
    except PermissionError:
        # 권한 오류 시 사용자 홈 디렉토리에 대체 경로 사용
        fallback_dir = Path.home() / ".book_coaching" / "autosave"
        fallback_dir.mkdir(parents=True, exist_ok=True)
        return fallback_dir
    except Exception:
        return AUTOSAVE_DIR


def sanitize_filename(name: str) -> str:
    """파일명에 사용할 수 없는 문자 제거 - 입력 검증 강화"""
    # 입력 검증
    if not name or not isinstance(name, str):
        return "unknown"

    try:
        # 한글, 영문, 숫자, 언더스코어만 허용
        sanitized = re.sub(r'[^\w가-힣]', '_', name)
        # 연속된 언더스코어 제거
        sanitized = re.sub(r'_+', '_', sanitized)
        # 앞뒤 언더스코어 제거
        sanitized = sanitized.strip('_')
        return sanitized[:50] if sanitized else "unknown"
    except Exception:
        return "unknown"


def generate_save_filename(student_name: str, timestamp: datetime = None) -> str:
    """저장 파일명 생성 (학생이름_날짜시간.json)"""
    if timestamp is None:
        timestamp = datetime.now()

    safe_name = sanitize_filename(student_name) if student_name else "unknown"
    time_str = timestamp.strftime("%Y%m%d_%H%M%S")
    return f"{safe_name}_{time_str}.json"


def get_session_data() -> Dict[str, Any]:
    """현재 세션 데이터 수집"""
    return {
        "saved_at": datetime.now().isoformat(),
        "version": "2.0",
        "book_info": st.session_state.get("book_info", {}),
        "selected_title": st.session_state.get("selected_title", ""),
        "generated_titles": st.session_state.get("generated_titles", ""),
        "generated_toc": st.session_state.get("generated_toc", ""),
        "parsed_toc": st.session_state.get("parsed_toc", []),
        "drafts": st.session_state.get("drafts", {}),
        "current_section_index": st.session_state.get("current_section_index", 0),
        "current_step": st.session_state.get("current_step", 1),
        "author_info": st.session_state.get("author_info", {}),
        "generated_proposal": st.session_state.get("generated_proposal", ""),
        "generated_landing_page": st.session_state.get("generated_landing_page", ""),
        "chat_mode_data": st.session_state.get("chat_mode_data", {}),
        "youtube_transcripts": st.session_state.get("youtube_transcripts", {}),
        "youtube_merged_transcript": st.session_state.get("youtube_merged_transcript", ""),
    }


def restore_session_data(data: Dict[str, Any]) -> bool:
    """세션 데이터 복원 - 타입 검증 강화"""
    # 입력 검증
    if not data or not isinstance(data, dict):
        return False

    try:
        # 타입 검증 후 복원
        book_info = data.get("book_info", {})
        st.session_state.book_info = book_info if isinstance(book_info, dict) else {}

        selected_title = data.get("selected_title", "")
        st.session_state.selected_title = selected_title if isinstance(selected_title, str) else ""

        generated_titles = data.get("generated_titles", "")
        st.session_state.generated_titles = generated_titles if isinstance(generated_titles, str) else ""

        generated_toc = data.get("generated_toc", "")
        st.session_state.generated_toc = generated_toc if isinstance(generated_toc, str) else ""

        parsed_toc = data.get("parsed_toc", [])
        st.session_state.parsed_toc = parsed_toc if isinstance(parsed_toc, list) else []

        drafts = data.get("drafts", {})
        st.session_state.drafts = drafts if isinstance(drafts, dict) else {}

        current_section_index = data.get("current_section_index", 0)
        st.session_state.current_section_index = current_section_index if isinstance(current_section_index, int) else 0

        current_step = data.get("current_step", 1)
        st.session_state.current_step = current_step if isinstance(current_step, int) and 1 <= current_step <= 7 else 1

        author_info = data.get("author_info", {})
        st.session_state.author_info = author_info if isinstance(author_info, dict) else {}

        generated_proposal = data.get("generated_proposal", "")
        st.session_state.generated_proposal = generated_proposal if isinstance(generated_proposal, str) else ""

        generated_landing_page = data.get("generated_landing_page", "")
        st.session_state.generated_landing_page = generated_landing_page if isinstance(generated_landing_page, str) else ""

        chat_mode_data = data.get("chat_mode_data", {})
        st.session_state.chat_mode_data = chat_mode_data if isinstance(chat_mode_data, dict) else {}

        youtube_transcripts = data.get("youtube_transcripts", {})
        st.session_state.youtube_transcripts = youtube_transcripts if isinstance(youtube_transcripts, dict) else {}

        youtube_merged_transcript = data.get("youtube_merged_transcript", "")
        st.session_state.youtube_merged_transcript = youtube_merged_transcript if isinstance(youtube_merged_transcript, str) else ""

        return True
    except Exception as e:
        print(f"세션 데이터 복원 실패: {e}")
        return False


def save_progress(student_name: str = None, is_autosave: bool = True) -> Optional[str]:
    """
    진행 상황 저장 - 예외 처리 및 파일 권한 검증 강화

    Args:
        student_name: 학생 이름 (None이면 세션에서 가져옴)
        is_autosave: 자동 저장 여부 (True면 기존 파일 관리, False면 새 파일만 생성)

    Returns:
        저장된 파일 경로 또는 None (실패 시)
    """
    try:
        save_dir = ensure_autosave_directory()

        # 학생 이름 가져오기 - 타입 검증 추가
        if student_name is None:
            book_info = st.session_state.get("book_info", {})
            if isinstance(book_info, dict):
                student_name = book_info.get("name", "")
            else:
                student_name = ""

        if not student_name or not isinstance(student_name, str):
            student_name = "unknown"

        # 세션 데이터 수집
        data = get_session_data()
        data["student_name"] = student_name
        data["is_autosave"] = is_autosave

        # 파일명 생성 및 저장
        filename = generate_save_filename(student_name)
        filepath = save_dir / filename

        # 임시 파일로 먼저 저장 후 이름 변경 (원자성 확보)
        temp_filepath = filepath.with_suffix('.tmp')
        try:
            with open(temp_filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            # 성공 시 임시 파일을 실제 파일로 이름 변경
            temp_filepath.replace(filepath)
        except Exception:
            # 임시 파일 저장 실패 시 직접 저장 시도
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        # 자동 저장인 경우 오래된 백업 정리
        if is_autosave:
            cleanup_old_backups(student_name)

        # 마지막 저장 시간 업데이트
        st.session_state.last_save_time = datetime.now().isoformat()
        st.session_state.last_save_filename = filename

        return str(filepath)

    except PermissionError as e:
        print(f"저장 권한 오류: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"JSON 인코딩 오류: {e}")
        return None
    except Exception as e:
        print(f"저장 실패: {e}")
        return None


def cleanup_old_backups(student_name: str) -> int:
    """
    오래된 백업 파일 정리 (최대 5개 유지)

    Returns:
        삭제된 파일 수
    """
    try:
        safe_name = sanitize_filename(student_name)
        pattern = f"{safe_name}_*.json"

        # 해당 학생의 모든 백업 파일 찾기
        backup_files = list(AUTOSAVE_DIR.glob(pattern))

        if len(backup_files) <= MAX_BACKUPS:
            return 0

        # 수정 시간 기준으로 정렬 (최신 순)
        backup_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        # 오래된 파일 삭제
        deleted_count = 0
        for old_file in backup_files[MAX_BACKUPS:]:
            try:
                old_file.unlink()
                deleted_count += 1
            except Exception:
                pass

        return deleted_count

    except Exception:
        return 0


def get_all_backups() -> List[Dict[str, Any]]:
    """모든 백업 파일 목록 조회"""
    try:
        ensure_autosave_directory()
        backup_files = list(AUTOSAVE_DIR.glob("*.json"))

        backups = []
        for filepath in backup_files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # 메타 정보 추출
                saved_at = data.get("saved_at", "")
                student_name = data.get("student_name", data.get("book_info", {}).get("name", "알 수 없음"))
                selected_title = data.get("selected_title", "")
                current_step = data.get("current_step", 1)
                drafts_count = len(data.get("drafts", {}))
                total_chars = sum(len(d) for d in data.get("drafts", {}).values())

                backups.append({
                    "filename": filepath.name,
                    "filepath": str(filepath),
                    "saved_at": saved_at,
                    "student_name": student_name,
                    "selected_title": selected_title,
                    "current_step": current_step,
                    "drafts_count": drafts_count,
                    "total_chars": total_chars,
                    "file_size": filepath.stat().st_size,
                    "modified_time": datetime.fromtimestamp(filepath.stat().st_mtime),
                })
            except Exception:
                continue

        # 최신순 정렬
        backups.sort(key=lambda x: x["modified_time"], reverse=True)
        return backups

    except Exception:
        return []


def get_student_backups(student_name: str) -> List[Dict[str, Any]]:
    """특정 학생의 백업 파일 목록 조회"""
    all_backups = get_all_backups()
    safe_name = sanitize_filename(student_name)
    return [b for b in all_backups if b["filename"].startswith(safe_name)]


def load_backup(filename: str) -> Optional[Dict[str, Any]]:
    """백업 파일 로드"""
    try:
        filepath = AUTOSAVE_DIR / filename
        if not filepath.exists():
            return None

        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    except Exception:
        return None


def delete_backup(filename: str) -> bool:
    """백업 파일 삭제"""
    try:
        filepath = AUTOSAVE_DIR / filename
        if filepath.exists():
            filepath.unlink()
            return True
        return False
    except Exception:
        return False


def check_for_previous_work() -> Optional[Dict[str, Any]]:
    """
    이전 작업 확인 (앱 시작 시)

    Returns:
        가장 최근 백업 정보 또는 None
    """
    backups = get_all_backups()
    if backups:
        return backups[0]  # 가장 최근 백업
    return None


def should_autosave() -> bool:
    """자동 저장이 필요한지 확인"""
    # 저장할 데이터가 있는지 확인
    if not st.session_state.get("drafts") and not st.session_state.get("selected_title"):
        return False

    # 마지막 저장 시간 확인
    last_save = st.session_state.get("last_save_time")
    if last_save is None:
        return True

    try:
        last_save_dt = datetime.fromisoformat(last_save)
        time_diff = datetime.now() - last_save_dt
        return time_diff.total_seconds() >= AUTOSAVE_INTERVAL_SECONDS
    except Exception:
        return True


def get_time_since_last_save() -> str:
    """마지막 저장 이후 경과 시간 문자열 반환"""
    last_save = st.session_state.get("last_save_time")
    if last_save is None:
        return "저장 안 됨"

    try:
        last_save_dt = datetime.fromisoformat(last_save)
        time_diff = datetime.now() - last_save_dt

        seconds = int(time_diff.total_seconds())

        if seconds < 60:
            return "방금 전"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes}분 전"
        elif seconds < 86400:
            hours = seconds // 3600
            return f"{hours}시간 전"
        else:
            days = seconds // 86400
            return f"{days}일 전"
    except Exception:
        return "알 수 없음"


def format_backup_info(backup: Dict[str, Any]) -> str:
    """백업 정보를 사용자 친화적 문자열로 포맷"""
    saved_at = backup.get("saved_at", "")
    student_name = backup.get("student_name", "알 수 없음")
    selected_title = backup.get("selected_title", "제목 없음")
    current_step = backup.get("current_step", 1)
    drafts_count = backup.get("drafts_count", 0)
    total_chars = backup.get("total_chars", 0)

    # 저장 시간 포맷
    try:
        dt = datetime.fromisoformat(saved_at)
        time_str = dt.strftime("%m/%d %H:%M")
    except Exception:
        time_str = "알 수 없음"

    step_names = {
        1: "정보 입력",
        2: "제목 만들기",
        3: "목차 만들기",
        4: "첫 번째 글",
        5: "책 소개서",
        6: "책 홍보 페이지",
        7: "다운로드",
    }
    step_name = step_names.get(current_step, f"단계 {current_step}")

    title_preview = selected_title[:20] + "..." if len(selected_title) > 20 else selected_title
    if not title_preview:
        title_preview = "제목 미정"

    return f"{student_name} | {title_preview} | {step_name} | {drafts_count}장 ({total_chars:,}자) | {time_str}"


# ===== UI 렌더링 함수 =====

def render_autosave_status():
    """자동 저장 상태 표시 UI"""
    time_since_save = get_time_since_last_save()

    if time_since_save == "저장 안 됨":
        status_color = "#FF9800"
        status_text = "저장 안 됨"
        status_icon = "💾"
    elif time_since_save == "방금 전":
        status_color = "#4CAF50"
        status_text = f"저장됨 {time_since_save}"
        status_icon = "✅"
    else:
        status_color = "#4CAF50"
        status_text = f"저장됨 {time_since_save}"
        status_icon = "✅"

    st.markdown(f"""
    <div style="
        display: inline-flex;
        align-items: center;
        background: {status_color}20;
        border: 2px solid {status_color};
        color: {status_color};
        padding: 8px 16px;
        border-radius: 25px;
        font-size: 0.95rem;
        font-weight: 600;
        margin: 8px 0;
    ">
        <span style="margin-right: 8px;">{status_icon}</span>
        <span>{status_text}</span>
    </div>
    """, unsafe_allow_html=True)


def render_save_buttons():
    """저장 버튼 UI"""
    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 지금 저장하기", use_container_width=True, type="primary"):
            student_name = st.session_state.get("book_info", {}).get("name", "")
            result = save_progress(student_name, is_autosave=False)
            if result:
                st.success("✅ 저장 완료!")
                st.rerun()
            else:
                st.error("❌ 저장 실패")

    with col2:
        if st.button("📂 저장된 작업 불러오기", use_container_width=True):
            st.session_state.show_backup_list = True
            st.rerun()


def render_backup_list():
    """저장된 작업 목록 UI"""
    st.markdown("### 📂 저장된 작업 목록")

    backups = get_all_backups()

    if not backups:
        st.info("💡 저장된 작업이 없어요.")
        if st.button("❌ 닫기", key="close_empty_backup"):
            st.session_state.show_backup_list = False
            st.rerun()
        return

    st.markdown(f"총 **{len(backups)}**개의 저장된 작업이 있어요.")

    for idx, backup in enumerate(backups[:10]):  # 최대 10개 표시
        info = format_backup_info(backup)

        col1, col2, col3 = st.columns([5, 1, 1])

        with col1:
            st.markdown(f"**{idx + 1}.** {info}")

        with col2:
            if st.button("📥 불러오기", key=f"load_{backup['filename']}", help="이 작업을 불러옵니다"):
                data = load_backup(backup['filename'])
                if data and restore_session_data(data):
                    st.session_state.show_backup_list = False
                    st.session_state.last_save_time = data.get("saved_at")
                    st.success("✅ 불러오기 완료!")
                    st.rerun()
                else:
                    st.error("❌ 불러오기 실패")

        with col3:
            if st.button("🗑️", key=f"delete_{backup['filename']}", help="이 작업을 삭제합니다"):
                if delete_backup(backup['filename']):
                    st.success("삭제됨")
                    st.rerun()

    st.markdown("---")
    if st.button("❌ 닫기", use_container_width=True):
        st.session_state.show_backup_list = False
        st.rerun()


def render_recovery_prompt():
    """이전 작업 복구 안내 UI (앱 시작 시)"""
    # 이미 복구 선택했으면 표시하지 않음
    if st.session_state.get("recovery_checked", False):
        return False

    # 이전 작업 확인
    previous_work = check_for_previous_work()

    if not previous_work:
        st.session_state.recovery_checked = True
        return False

    # 복구 안내 표시
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #FFF3E0, #FFE0B2);
        border: 3px solid #FF9800;
        border-radius: 20px;
        padding: 2rem;
        margin: 1.5rem 0;
        text-align: center;
    ">
        <h2 style="color: #E65100; margin-top: 0;">🔔 이전에 작업하던 게 있어요!</h2>
        <p style="font-size: 1.2rem; color: #5D4037;">이어서 할까요?</p>
    </div>
    """, unsafe_allow_html=True)

    # 이전 작업 정보 표시
    info = format_backup_info(previous_work)
    st.markdown(f"""
    <div style="
        background: white;
        border: 2px solid #E0E0E0;
        border-radius: 15px;
        padding: 1.5rem;
        margin: 1rem 0;
    ">
        <p style="margin: 0; font-size: 1.1rem;">📄 {info}</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        if st.button("✅ 네, 이어서 할래요!", use_container_width=True, type="primary"):
            data = load_backup(previous_work['filename'])
            if data and restore_session_data(data):
                st.session_state.recovery_checked = True
                st.session_state.last_save_time = data.get("saved_at")
                st.success("✅ 이전 작업을 불러왔어요!")
                st.rerun()
            else:
                st.error("❌ 불러오기 실패")

    with col2:
        if st.button("❌ 아니요, 새로 시작!", use_container_width=True):
            st.session_state.recovery_checked = True
            st.rerun()

    return True  # 복구 화면이 표시됨


def perform_autosave_if_needed():
    """자동 저장 수행 (필요한 경우)"""
    if should_autosave():
        student_name = st.session_state.get("book_info", {}).get("name", "")
        if student_name or st.session_state.get("drafts"):
            save_progress(student_name, is_autosave=True)


def trigger_important_save(event_name: str = ""):
    """중요 변경 후 즉시 저장 트리거"""
    student_name = st.session_state.get("book_info", {}).get("name", "")
    result = save_progress(student_name, is_autosave=True)
    if result:
        st.session_state.last_important_save = {
            "time": datetime.now().isoformat(),
            "event": event_name
        }
    return result


def init_autosave_state():
    """자동 저장 관련 세션 상태 초기화"""
    defaults = {
        "last_save_time": None,
        "last_save_filename": None,
        "last_important_save": None,
        "recovery_checked": False,
        "show_backup_list": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

"""관리자 연락 기능 모듈 - 강화된 에러 핸들링"""
import streamlit as st
import csv
import json
import os
from datetime import datetime
from pathlib import Path
import time


# 데이터 파일 경로
DATA_DIR = Path(__file__).parent.parent / "data"
MESSAGES_CSV = DATA_DIR / "messages.csv"
MESSAGES_JSON = DATA_DIR / "messages.json"

# 에러 메시지 (전문적이고 정중한 한국어)
ERROR_MESSAGES = {
    "save_failed": """
**메시지 저장 중 오류가 발생했습니다.**

다시 한번 시도해 주시겠습니까?
카카오톡이나 이메일로도 연락하실 수 있습니다.
""",
    "load_failed": """
**저장된 메시지를 불러오는 중 오류가 발생했습니다.**

페이지를 새로고침해 주세요.
""",
    "permission": """
**파일 접근 권한 오류가 발생했습니다.**

관리자에게 "파일 권한 설정이 필요합니다"라고 문의해 주세요.
""",
    "empty_message": """
**메시지를 입력해 주세요.**

궁금하신 내용을 자유롭게 작성해 주세요.
""",
    "too_short": """
**메시지가 너무 짧습니다.**

조금 더 구체적으로 작성해 주시면 더 정확한 답변을 드릴 수 있습니다.
""",
    "too_long": """
**메시지가 너무 깁니다.**

5,000자 이내로 작성해 주세요.
""",
    "unknown": """
**일시적인 오류가 발생했습니다.**

다시 한번 시도해 주시겠습니까?
"""
}

# 설정
MAX_MESSAGE_LENGTH = 5000
MIN_MESSAGE_LENGTH = 5


def get_admin_settings():
    """관리자 설정 가져오기 - 안전한 기본값 제공"""
    try:
        return {
            "kakao_link": st.secrets.get("ADMIN_KAKAO_LINK", "https://open.kakao.com/o/example"),
            "email": st.secrets.get("ADMIN_EMAIL", "coach@example.com"),
            "phone": st.secrets.get("ADMIN_PHONE", "010-1234-5678"),
            "show_phone": st.secrets.get("ADMIN_SHOW_PHONE", True),
        }
    except Exception:
        # Streamlit secrets 접근 실패 시 기본값 반환
        return {
            "kakao_link": "",
            "email": "",
            "phone": "",
            "show_phone": False,
        }


def ensure_data_directory():
    """데이터 디렉토리 확인 및 생성 - 안전한 처리"""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        # CSV 파일 헤더 생성
        if not MESSAGES_CSV.exists():
            try:
                with open(MESSAGES_CSV, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        'student_name', 'timestamp', 'message', 'current_step',
                        'status', 'admin_reply', 'reply_timestamp'
                    ])
            except Exception:
                pass  # CSV 생성 실패해도 JSON으로 동작 가능

        # JSON 파일 초기화
        if not MESSAGES_JSON.exists():
            try:
                with open(MESSAGES_JSON, 'w', encoding='utf-8') as f:
                    json.dump([], f, ensure_ascii=False)
            except Exception:
                pass  # JSON 생성 실패해도 메모리에서 동작 가능

        return True

    except PermissionError:
        return False
    except Exception:
        return False


def validate_message(message: str) -> tuple:
    """
    메시지 유효성 검사

    Returns:
        (is_valid, cleaned_message_or_error_key)
    """
    # 빈 입력 검사
    if not message:
        return False, "empty_message"

    if not isinstance(message, str):
        return False, "empty_message"

    message = message.strip()

    if not message:
        return False, "empty_message"

    # 길이 검사
    if len(message) < MIN_MESSAGE_LENGTH:
        return False, "too_short"

    if len(message) > MAX_MESSAGE_LENGTH:
        return False, "too_long"

    return True, message


def save_message_to_csv(student_name: str, message: str, current_step: int) -> bool:
    """메시지를 CSV 파일에 저장 - 강화된 에러 처리"""
    try:
        ensure_data_directory()

        # 입력 검증
        if not student_name:
            student_name = "익명"
        elif not isinstance(student_name, str):
            student_name = "익명"
        else:
            student_name = student_name.strip()[:100]  # 100자 제한

        if not message:
            return False

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        step_name = get_step_name(current_step)

        with open(MESSAGES_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                student_name, timestamp, message, step_name,
                'pending', '', ''
            ])
        return True

    except PermissionError:
        # 세션에 에러 저장 (화면에는 바로 표시하지 않음)
        st.session_state.last_contact_error = "permission"
        return False
    except Exception as e:
        st.session_state.last_contact_error = str(e)
        return False


def save_message_to_json(student_name: str, message: str, current_step: int, book_info: dict = None) -> bool:
    """메시지를 JSON 파일에 저장 - 강화된 에러 처리"""
    try:
        ensure_data_directory()

        # 입력 검증
        if not student_name:
            student_name = "익명"
        elif not isinstance(student_name, str):
            student_name = "익명"
        else:
            student_name = student_name.strip()[:100]

        if not message:
            return False

        # 기존 데이터 로드
        messages = load_all_messages_json()

        # book_info 안전하게 처리
        book_title = ""
        book_topic = ""
        if book_info and isinstance(book_info, dict):
            book_title = str(book_info.get("title", ""))[:200]
            book_topic = str(book_info.get("topic", ""))[:500]

        # 새 메시지 추가
        new_message = {
            "id": len(messages) + 1,
            "student_name": student_name,
            "timestamp": datetime.now().isoformat(),
            "message": message[:MAX_MESSAGE_LENGTH],  # 길이 제한
            "current_step": current_step,
            "step_name": get_step_name(current_step),
            "status": "pending",
            "book_title": book_title,
            "book_topic": book_topic,
            "admin_reply": "",
            "reply_timestamp": "",
        }
        messages.append(new_message)

        # 저장
        with open(MESSAGES_JSON, 'w', encoding='utf-8') as f:
            json.dump(messages, f, ensure_ascii=False, indent=2)

        return True

    except PermissionError:
        st.session_state.last_contact_error = "permission"
        return False
    except json.JSONDecodeError:
        st.session_state.last_contact_error = "json_error"
        return False
    except Exception as e:
        st.session_state.last_contact_error = str(e)
        return False


def load_all_messages_json() -> list:
    """모든 메시지 로드 (JSON) - 안전한 로딩"""
    try:
        ensure_data_directory()
        if MESSAGES_JSON.exists():
            with open(MESSAGES_JSON, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content or not content.strip():
                    return []
                data = json.loads(content)
                # 데이터 유효성 검사
                if isinstance(data, list):
                    # 각 항목이 dict인지 확인
                    return [item for item in data if isinstance(item, dict)]
                return []
        return []
    except json.JSONDecodeError:
        # JSON 파싱 실패 시 빈 배열 반환
        return []
    except PermissionError:
        return []
    except Exception:
        return []


def load_all_messages_csv() -> list:
    """모든 메시지 로드 (CSV) - 안전한 로딩"""
    try:
        ensure_data_directory()
        messages = []
        if MESSAGES_CSV.exists():
            with open(MESSAGES_CSV, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row:  # 빈 행 스킵
                        messages.append(row)
        return messages
    except PermissionError:
        return []
    except Exception:
        return []


def update_message_status(message_id: int, status: str, admin_reply: str = "") -> bool:
    """메시지 상태 업데이트 (관리자 답변) - 안전한 업데이트"""
    try:
        # 입력 검증
        if not message_id:
            return False

        if not status:
            status = "pending"

        messages = load_all_messages_json()

        updated = False
        for msg in messages:
            if msg.get("id") == message_id:
                msg["status"] = status
                if admin_reply:
                    msg["admin_reply"] = str(admin_reply)[:10000]  # 10000자 제한
                    msg["reply_timestamp"] = datetime.now().isoformat()
                updated = True
                break

        if updated:
            with open(MESSAGES_JSON, 'w', encoding='utf-8') as f:
                json.dump(messages, f, ensure_ascii=False, indent=2)
            return True

        return False

    except PermissionError:
        return False
    except Exception:
        return False


def get_step_name(step: int) -> str:
    """단계 번호를 이름으로 변환 - 안전한 변환"""
    step_names = {
        1: "1단계_정보입력",
        2: "2단계_제목생성",
        3: "3단계_목차생성",
        4: "4단계_초안작성",
        5: "5단계_출간기획서",
        6: "6단계_랜딩페이지",
        7: "7단계_다운로드",
    }
    try:
        if not isinstance(step, int):
            step = int(step) if step else 0
        return step_names.get(step, f"단계_{step}")
    except Exception:
        return "단계_알수없음"


def get_pending_messages_count() -> int:
    """대기 중인 메시지 수 - 안전한 카운트"""
    try:
        messages = load_all_messages_json()
        return sum(1 for m in messages if m.get("status") == "pending")
    except Exception:
        return 0


def get_student_messages(student_name: str) -> list:
    """특정 학생의 메시지 조회 - 안전한 조회"""
    try:
        if not student_name:
            return []

        if not isinstance(student_name, str):
            return []

        student_name = student_name.strip()
        if not student_name:
            return []

        messages = load_all_messages_json()
        # 대소문자 구분 없이 비교
        return [m for m in messages if m.get("student_name", "").lower() == student_name.lower()]
    except Exception:
        return []


def render_contact_button():
    """담당자에게 문의하기 버튼 렌더링 - 전문적인 UI"""
    admin_settings = get_admin_settings()

    st.markdown("""
    <style>
    .contact-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        padding: 1.5rem;
        margin: 1rem 0;
        color: white;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    .contact-box h4 {
        margin: 0 0 0.5rem 0;
        color: white;
    }
    .contact-option {
        background: rgba(255,255,255,0.2);
        border-radius: 12px;
        padding: 1rem;
        margin: 0.5rem 0;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        transition: all 0.3s ease;
    }
    .contact-option:hover {
        background: rgba(255,255,255,0.3);
        transform: translateY(-2px);
    }
    .contact-option a {
        color: white;
        text-decoration: none;
        font-weight: 600;
    }
    .contact-option a:hover {
        text-decoration: underline;
    }
    .contact-btn {
        display: inline-block;
        padding: 14px 28px;
        border-radius: 12px;
        text-decoration: none;
        font-weight: bold;
        width: 100%;
        text-align: center;
        transition: all 0.3s ease;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }
    .contact-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    }
    .kakao-btn {
        background: linear-gradient(135deg, #FEE500 0%, #F9D000 100%);
        color: #3C1E1E;
    }
    .email-btn {
        background: linear-gradient(135deg, #4285F4 0%, #356AC3 100%);
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

    # 헤더 - 전문적인 스타일
    st.markdown("""
    <div style="background: linear-gradient(135deg, #FF9800 0%, #F57C00 100%);
                color: white; padding: 1.5rem; border-radius: 16px; margin-bottom: 1rem;
                box-shadow: 0 4px 20px rgba(255, 152, 0, 0.3);">
        <div style="display: flex; align-items: center; gap: 1rem;">
            <div style="background: rgba(255,255,255,0.2); border-radius: 50%;
                        width: 50px; height: 50px; display: flex; align-items: center;
                        justify-content: center; font-size: 1.8rem;">
                📞
            </div>
            <div>
                <h3 style="margin: 0; color: white; font-size: 1.3rem; font-weight: 700;">
                    담당자에게 문의하기
                </h3>
                <p style="margin: 5px 0 0 0; font-size: 0.9rem; opacity: 0.9;">
                    궁금하신 점이 있으시면 언제든 문의해 주세요.
                </p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 컨테이너
    st.markdown("""
    <div style="background: #F8F9FF; padding: 1.2rem; border-radius: 0 0 16px 16px;
                border: 2px solid #E0E8FF; border-top: none;">
    """, unsafe_allow_html=True)

    st.markdown("#### 바로 연락하기")
    st.caption("실시간으로 담당자와 상담하실 수 있습니다.")

    col1, col2 = st.columns(2)

    with col1:
        # 카카오톡 오픈채팅 - 링크 검증 추가 + 명확한 안내
        kakao_link = admin_settings.get('kakao_link', '')
        if kakao_link and "kakao" in kakao_link.lower():
            st.markdown(f"""
            <a href="{kakao_link}" target="_blank" class="contact-btn kakao-btn">
                카카오톡으로 연락
            </a>
            """, unsafe_allow_html=True)
            # 명확한 안내 추가
            st.markdown("""
            <div style="background: #FFF8E1; border-radius: 8px; padding: 8px 12px;
                        margin-top: 8px; border-left: 3px solid #FFC107; font-size: 0.85rem;">
                <p style="margin: 0; color: #5D4037;">
                    <strong>카카오톡 오픈채팅</strong>으로 연결됩니다<br>
                    <span style="color: #666;">새 창에서 열려요!</span>
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("카카오톡 링크가 아직 설정되지 않았습니다.")

    with col2:
        # 이메일 - 링크 검증 추가 + 명확한 안내
        email = admin_settings.get('email', '')
        if email and "@" in email:
            st.markdown(f"""
            <a href="mailto:{email}?subject=[책쓰기 코칭] 질문이 있어요" class="contact-btn email-btn">
                이메일 보내기
            </a>
            """, unsafe_allow_html=True)
            # 명확한 안내 추가
            st.markdown(f"""
            <div style="background: #E3F2FD; border-radius: 8px; padding: 8px 12px;
                        margin-top: 8px; border-left: 3px solid #2196F3; font-size: 0.85rem;">
                <p style="margin: 0; color: #1565C0;">
                    <strong>{email}</strong>로 메일이 열려요<br>
                    <span style="color: #666;">기본 메일 앱이 실행됩니다</span>
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.info("이메일이 아직 설정되지 않았습니다.")

    # 전화번호 표시 (설정된 경우) - 더 눈에 띄게
    if admin_settings.get('show_phone', False):
        phone = admin_settings.get('phone', '')
        if phone:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
                        padding: 12px 16px; border-radius: 10px; margin-top: 1rem;
                        border: 1px solid #A5D6A7; text-align: center;">
                <span style="font-size: 1.2rem;"></span>
                <span style="font-weight: bold; font-size: 1.1rem; color: #2E7D32;">
                    {phone}
                </span>
                <p style="margin: 5px 0 0 0; font-size: 0.8rem; color: #666;">
                    급한 문의는 전화로 연락해 주셔도 됩니다.
                </p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("")
    st.markdown("#### 메시지 남기기")

    # 메시지 전송 안내 - 어디로 가는지 명확히 표시
    admin_email = admin_settings.get('email', '')
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
                border-radius: 12px; padding: 1rem; margin: 0.5rem 0;
                border-left: 4px solid #4CAF50;">
        <p style="margin: 0; font-size: 0.95rem; color: #2E7D32;">
            <strong>메시지 처리 안내:</strong><br>
            담당자 확인 후 <strong>카카오톡</strong> 또는 <strong>앱 내 알림</strong>으로 답변드립니다.
        </p>
        {f'<p style="margin: 0.5rem 0 0 0; font-size: 0.85rem; color: #666;">담당자 이메일: {admin_email}</p>' if admin_email else ''}
    </div>
    """, unsafe_allow_html=True)


def render_message_form(student_name: str, current_step: int, book_info: dict = None):
    """메시지 전송 폼 렌더링 - 강화된 에러 핸들링"""

    # 학생 이름이 없으면 입력 요청
    try:
        display_name = student_name if student_name else "익명"
    except Exception:
        display_name = "익명"

    # 현재 단계 정보 표시
    step_name = get_step_name(current_step)

    st.markdown(f"""
    <div style="background: #FFF3E0; padding: 10px 15px; border-radius: 10px;
                margin-bottom: 1rem; border-left: 4px solid #FF9800;">
        <p style="margin: 0; font-size: 0.9rem;">
            <b>보내는 사람:</b> {display_name} |
            <b>현재 단계:</b> {step_name}
        </p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("contact_message_form", clear_on_submit=True):
        message = st.text_area(
            "문의 내용",
            placeholder="궁금하신 점이나 도움이 필요한 부분을 자유롭게 작성해 주세요.\n\n예시:\n- 제목 방향에 대한 조언이 필요합니다\n- 목차 구성에 대해 상담받고 싶습니다\n- 원고 작성 시작 방법이 궁금합니다",
            height=150,
            help="작성하신 내용은 담당자에게 전달됩니다."
        )

        # 글자 수 표시
        if message:
            try:
                char_count = len(message)
                if char_count > MAX_MESSAGE_LENGTH * 0.8:
                    st.warning(f"글자 수: {char_count:,} / {MAX_MESSAGE_LENGTH:,} (거의 다 찼습니다)")
                else:
                    st.caption(f"글자 수: {char_count:,}")
            except Exception:
                pass

        # 긴급도 선택 (선택사항)
        urgency = st.radio(
            "긴급도 선택",
            ["보통", "다소 급함", "매우 급함"],
            horizontal=True,
            help="긴급도에 따라 답변 우선순위를 조정합니다"
        )

        # 답변 받을 방법 선택
        st.markdown("---")
        st.markdown("**답변 수신 방법을 선택해 주세요:**")
        reply_method = st.radio(
            "답변 방법",
            ["앱 내에서 확인 (기본)", "카카오톡으로 연락 요청", "이메일로 답변 요청", "전화 연락 요청"],
            horizontal=False,
            help="선호하시는 방법으로 답변드립니다",
            label_visibility="collapsed"
        )

        # 연락처 입력 (필요한 경우)
        contact_info = ""
        if reply_method == "카카오톡으로 연락 요청":
            contact_info = st.text_input(
                "카카오톡 ID 또는 연락처",
                placeholder="카카오톡 ID를 입력해 주세요",
                help="담당자가 카카오톡으로 연락드립니다"
            )
        elif reply_method == "이메일로 답변 요청":
            contact_info = st.text_input(
                "이메일 주소",
                placeholder="example@email.com",
                help="이메일로 답변을 보내드립니다"
            )
        elif reply_method == "전화 연락 요청":
            contact_info = st.text_input(
                "전화번호",
                placeholder="010-1234-5678",
                help="편하신 시간에 연락드리겠습니다"
            )

        col1, col2 = st.columns([3, 1])
        with col1:
            submit = st.form_submit_button(
                "문의하기",
                use_container_width=True,
                type="primary"
            )

        if submit:
            # 메시지 유효성 검사
            is_valid, result = validate_message(message)

            if not is_valid:
                st.error(ERROR_MESSAGES.get(result, ERROR_MESSAGES["unknown"]))
            else:
                # 긴급도 및 답변 방법 추가
                reply_info = f"[답변방법: {reply_method}]"
                if contact_info:
                    reply_info += f" [연락처: {contact_info}]"
                final_message = f"[{urgency}] {reply_info} {result}"

                # CSV와 JSON 모두에 저장
                try:
                    success_csv = save_message_to_csv(student_name or "익명", final_message, current_step)
                    success_json = save_message_to_json(student_name or "익명", final_message, current_step, book_info)

                    if success_csv or success_json:
                        # 성공 메시지 - 전문적이고 명확하게 + 답변 방법 안내
                        reply_method_text = ""
                        if reply_method == "앱 내에서 확인 (기본)":
                            reply_method_text = "'내 문의 확인하기'에서 답변을 확인하실 수 있습니다."
                        elif reply_method == "카카오톡으로 연락 요청":
                            reply_method_text = f"카카오톡 ({contact_info if contact_info else '등록된 연락처'})으로 답변드리겠습니다."
                        elif reply_method == "이메일로 답변 요청":
                            reply_method_text = f"이메일 ({contact_info if contact_info else '등록된 이메일'})로 답변드리겠습니다."
                        elif reply_method == "전화 연락 요청":
                            reply_method_text = f"전화 ({contact_info if contact_info else '등록된 번호'})로 연락드리겠습니다."

                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
                                    padding: 1.5rem; border-radius: 16px; text-align: center;
                                    border: 2px solid #4CAF50; margin: 1rem 0;
                                    animation: success-pop 0.5s ease-out;">
                            <h3 style="color: #2E7D32; margin: 0 0 0.5rem 0;">
                                문의가 접수되었습니다.
                            </h3>
                            <p style="margin: 0.5rem 0; color: #333; font-size: 1rem;">
                                담당자 확인 후 빠르게 답변드리겠습니다.
                            </p>
                            <div style="background: white; border-radius: 10px; padding: 0.8rem;
                                        margin-top: 0.8rem; border: 1px solid #A5D6A7;">
                                <p style="margin: 0; font-size: 0.95rem; color: #1B5E20;">
                                    <strong>답변 방법:</strong> {reply_method_text}
                                </p>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        st.balloons()

                        # 저장 확인 로그 (디버그용)
                        st.caption(f"저장 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                        # 폼 초기화를 위해 잠시 대기 후 rerun
                        time.sleep(1)
                    else:
                        # 저장 실패
                        error_key = st.session_state.get('last_contact_error', 'save_failed')
                        if error_key == "permission":
                            st.error(ERROR_MESSAGES["permission"])
                        else:
                            st.error(ERROR_MESSAGES["save_failed"])

                        # 대안 제시
                        admin_settings = get_admin_settings()
                        if admin_settings.get('kakao_link') or admin_settings.get('email'):
                            st.info("상단의 카카오톡이나 이메일로도 연락하실 수 있습니다.")

                except Exception as e:
                    st.error(ERROR_MESSAGES["save_failed"])
                    with st.expander("기술 정보 (관리자에게 전달해 주세요)", expanded=False):
                        st.code(str(e))


def render_my_questions(student_name: str):
    """내 문의 목록 보기 - 안전한 렌더링"""
    try:
        messages = get_student_messages(student_name)

        if not messages:
            st.markdown("""
            <div style="background: #F5F5F5; padding: 1.5rem; border-radius: 12px; text-align: center;">
                <p style="font-size: 1.1rem; color: #666; margin: 0;">
                    아직 접수된 문의가 없습니다.<br>
                    궁금하신 점이 있으시면 상단에서 문의해 주세요.
                </p>
            </div>
            """, unsafe_allow_html=True)
            return

        # 답변 상태 요약
        answered_count = sum(1 for m in messages if m.get("status") == "answered")
        pending_count = len(messages) - answered_count

        st.markdown(f"""
        <div style="display: flex; gap: 1rem; margin-bottom: 1rem;">
            <div style="flex: 1; background: #E3F2FD; padding: 10px; border-radius: 10px; text-align: center;">
                <span style="font-size: 1.5rem;"></span>
                <p style="margin: 5px 0 0 0; font-weight: bold;">총 {len(messages)}개</p>
            </div>
            <div style="flex: 1; background: #E8F5E9; padding: 10px; border-radius: 10px; text-align: center;">
                <span style="font-size: 1.5rem;"></span>
                <p style="margin: 5px 0 0 0; font-weight: bold;">답변 {answered_count}개</p>
            </div>
            <div style="flex: 1; background: #FFF3E0; padding: 10px; border-radius: 10px; text-align: center;">
                <span style="font-size: 1.5rem;"></span>
                <p style="margin: 5px 0 0 0; font-weight: bold;">대기 {pending_count}개</p>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 내 문의 목록")

        for msg in reversed(messages):  # 최신순
            try:
                status = msg.get("status", "pending")
                is_answered = status == "answered"

                status_text = "답변 완료" if is_answered else "답변 대기 중"

                # 메시지 미리보기 (긴급도 태그 제거)
                message_preview = msg.get('message', '')
                if message_preview.startswith('['):
                    # [보통이에요] 같은 태그 제거
                    bracket_end = message_preview.find(']')
                    if bracket_end > 0:
                        message_preview = message_preview[bracket_end + 2:]
                message_preview = message_preview[:40] + "..." if len(message_preview) > 40 else message_preview

                # 날짜 포맷
                timestamp = msg.get('timestamp', '')
                try:
                    date_str = timestamp[:10] if len(timestamp) >= 10 else timestamp
                except Exception:
                    date_str = "날짜 없음"

                status_emoji = "[완료]" if is_answered else "[대기]"
                with st.expander(f"{status_emoji} [{date_str}] {message_preview}", expanded=is_answered):
                    # 문의 내용
                    st.markdown(f"""
                    <div style="background: #E3F2FD; padding: 12px; border-radius: 10px;
                                border-left: 4px solid #2196F3; margin-bottom: 10px;">
                        <p style="margin: 0; font-size: 0.85rem; color: #666;">내 문의</p>
                        <p style="margin: 5px 0 0 0; font-size: 1rem;">{msg.get('message', '')}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    st.caption(f"단계: {msg.get('step_name', '')} | 상태: {status_text}")

                    if msg.get("admin_reply"):
                        try:
                            reply_timestamp = msg.get('reply_timestamp', '')
                            reply_date_str = reply_timestamp[:16] if reply_timestamp else ""
                        except Exception:
                            reply_date_str = ""

                        st.markdown(f"""
                        <div style="background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
                                    padding: 12px; border-radius: 10px;
                                    border-left: 4px solid #4CAF50; margin-top: 10px;">
                            <p style="margin: 0; font-size: 0.85rem; color: #2E7D32;">담당자 답변</p>
                            <p style="margin: 5px 0 0 0; font-size: 1rem;">{msg.get('admin_reply', '')}</p>
                            <p style="margin: 8px 0 0 0; font-size: 0.8rem; color: #666;">
                                답변 시간: {reply_date_str}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)
                    elif not is_answered:
                        st.markdown("""
                        <div style="background: #FFF3E0; padding: 10px; border-radius: 8px;
                                    text-align: center; margin-top: 10px;">
                            <p style="margin: 0; font-size: 0.9rem; color: #E65100;">
                                담당자가 검토 중입니다. 빠른 시일 내에 답변드리겠습니다.
                            </p>
                        </div>
                        """, unsafe_allow_html=True)

            except Exception:
                # 개별 메시지 렌더링 실패는 건너뛰기
                continue

    except Exception as e:
        st.warning("문의 목록을 불러오는 중 오류가 발생했습니다. 페이지를 새로고침해 주세요.")
        with st.expander("기술 정보", expanded=False):
            st.code(str(e))


def render_contact_section(student_name: str, current_step: int, book_info: dict = None):
    """전체 연락 섹션 렌더링 - 안전한 렌더링"""
    try:
        render_contact_button()
        render_message_form(student_name, current_step, book_info)

        # 내 문의 보기 (이름이 있는 경우만)
        if student_name:
            with st.expander("내 문의 확인하기", expanded=False):
                render_my_questions(student_name)

    except Exception as e:
        st.error("연락 섹션을 불러오는 중 오류가 발생했습니다. 페이지를 새로고침해 주세요.")
        with st.expander("기술 정보", expanded=False):
            st.code(str(e))

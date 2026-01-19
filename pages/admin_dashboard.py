"""관리자 대시보드 - 수강생 질문 관리 및 모니터링 (강화 버전)"""
import streamlit as st
import json
from datetime import datetime, timedelta
from collections import Counter, defaultdict
import sys
from pathlib import Path

# 상위 디렉토리를 경로에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.contact_handler import (
    load_all_messages_json,
    update_message_status,
    get_pending_messages_count,
    ensure_data_directory,
)

# 페이지 설정
st.set_page_config(
    page_title="관리자 대시보드",
    page_icon="🛠️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# 관리자 비밀번호 (실제 운영 시 secrets.toml에서 관리)
try:
    ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "admin123")
except Exception:
    ADMIN_PASSWORD = "admin123"

# 빠른 답변 템플릿
QUICK_REPLY_TEMPLATES = {
    "격려": "열심히 하고 계시네요! 지금 방향이 맞습니다. 계속 진행해 주세요. 추가 질문 있으시면 언제든 말씀해 주세요!",
    "제목_조언": "제목은 독자가 가장 먼저 보는 부분이에요. 1) 핵심 키워드를 포함하고 2) 구체적인 혜택을 담고 3) 호기심을 자극하는 방향으로 수정해 보세요.",
    "목차_조언": "목차는 책의 뼈대입니다. 1) 독자의 여정을 생각하며 2) 논리적 흐름으로 3) 각 장이 명확한 가치를 전달하도록 구성해 보세요.",
    "글쓰기_팁": "초안은 완벽하지 않아도 됩니다. 일단 생각나는 대로 써보세요. 퇴고는 나중에 해도 돼요. 중요한 건 멈추지 않는 것입니다!",
    "확인_완료": "네, 확인했습니다. 질문하신 내용에 대해 검토해봤는데 잘 진행하고 계세요. 다음 단계로 넘어가셔도 됩니다!",
    "상세_안내": "이 부분은 조금 더 자세한 설명이 필요해 보여요. 카카오톡이나 이메일로 연락 주시면 더 자세히 안내해 드릴게요!",
}

# 단계별 정보
STEP_NAMES = {
    1: "1단계_정보입력",
    2: "2단계_제목생성",
    3: "3단계_목차생성",
    4: "4단계_초안작성",
    5: "5단계_출간기획서",
    6: "6단계_랜딩페이지",
    7: "7단계_다운로드",
}


def check_admin_auth():
    """관리자 인증 확인 - 보안 강화"""
    if "admin_authenticated" not in st.session_state:
        st.session_state.admin_authenticated = False
    if "login_attempts" not in st.session_state:
        st.session_state.login_attempts = 0

    if not st.session_state.admin_authenticated:
        # 로그인 시도 횟수 제한
        if st.session_state.login_attempts >= 5:
            st.error("""
            **로그인 시도 횟수를 초과했습니다.**

            잠시 후 다시 시도해주세요.
            계속 문제가 발생하면 시스템 관리자에게 문의하세요.
            """)
            return False

        st.markdown("""
        <div style="max-width: 400px; margin: 2rem auto; padding: 2rem;
                    background: white; border-radius: 16px;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.1);">
            <h2 style="text-align: center; color: #333; margin-bottom: 1rem;">
                관리자 로그인
            </h2>
            <p style="text-align: center; color: #666; font-size: 0.9rem;">
                관리자 대시보드에 접근하려면<br>비밀번호를 입력하세요.
            </p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("admin_login"):
            password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")
            submit = st.form_submit_button("로그인", type="primary", use_container_width=True)

            if submit:
                if not password:
                    st.warning("비밀번호를 입력해주세요.")
                elif password == ADMIN_PASSWORD:
                    st.session_state.admin_authenticated = True
                    st.session_state.login_attempts = 0
                    st.success("로그인 성공!")
                    st.rerun()
                else:
                    st.session_state.login_attempts += 1
                    remaining = 5 - st.session_state.login_attempts
                    if remaining > 0:
                        st.error(f"비밀번호가 틀렸습니다. (남은 시도: {remaining}회)")
                    else:
                        st.error("로그인 시도 횟수를 초과했습니다.")
                        st.rerun()

        # 남은 시도 횟수 표시
        if st.session_state.login_attempts > 0:
            st.caption(f"로그인 시도: {st.session_state.login_attempts}/5")

        return False

    return True


def get_today_stats():
    """오늘의 통계 계산 - 예외 처리 강화"""
    try:
        messages = load_all_messages_json()
        if not messages or not isinstance(messages, list):
            messages = []
    except Exception:
        messages = []

    today = datetime.now().date()

    today_questions = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        try:
            timestamp = m.get("timestamp", "")
            if timestamp and isinstance(timestamp, str):
                msg_date = datetime.fromisoformat(timestamp).date()
                if msg_date == today:
                    today_questions.append(m)
        except Exception:
            continue

    # 수강생 정보 수집
    students = set()
    completed_books = 0
    total_char_count = 0

    for m in messages:
        if not isinstance(m, dict):
            continue
        students.add(m.get("student_name", "익명") or "익명")
        # 7단계(다운로드)에 도달한 경우 완료로 간주
        step_name = m.get("step_name", "") or ""
        if m.get("current_step") == 7 or "7단계" in step_name:
            completed_books += 1

    pending_count = sum(1 for m in messages if isinstance(m, dict) and m.get("status") == "pending")

    return {
        "total_students": len(students),
        "today_questions": len(today_questions),
        "pending_count": pending_count,
        "completed_books": completed_books,
        "total_messages": len(messages),
    }


def get_recent_activities(limit=10):
    """최근 활동 목록 조회"""
    messages = load_all_messages_json()

    activities = []
    for m in messages:
        timestamp = m.get("timestamp", "")
        activities.append({
            "time": timestamp,
            "type": "question",
            "student": m.get("student_name", "익명"),
            "step": m.get("step_name", ""),
            "content": m.get("message", "")[:50] + "..." if len(m.get("message", "")) > 50 else m.get("message", ""),
            "status": m.get("status", "pending"),
        })

        # 답변이 있는 경우
        if m.get("admin_reply") and m.get("reply_timestamp"):
            activities.append({
                "time": m.get("reply_timestamp"),
                "type": "reply",
                "student": m.get("student_name", "익명"),
                "step": m.get("step_name", ""),
                "content": m.get("admin_reply", "")[:50] + "...",
                "status": "answered",
            })

    # 시간순 정렬 (최신순)
    activities.sort(key=lambda x: x.get("time", ""), reverse=True)
    return activities[:limit]


def render_dashboard_home():
    """대시보드 홈 - 오늘의 통계 및 최근 활동"""
    st.markdown("## 대시보드 홈")

    # 오늘의 통계
    stats = get_today_stats()

    st.markdown("### 오늘의 통계")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    padding: 1.5rem; border-radius: 16px; text-align: center; color: white;">
            <p style="margin: 0; font-size: 2.5rem; font-weight: bold;">{stats['total_students']}</p>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">총 수강생 수</p>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                    padding: 1.5rem; border-radius: 16px; text-align: center; color: white;">
            <p style="margin: 0; font-size: 2.5rem; font-weight: bold;">{stats['today_questions']}</p>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">오늘 질문 수</p>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        urgency_bg = "linear-gradient(135deg, #eb3349 0%, #f45c43 100%)" if stats['pending_count'] > 5 else \
                     "linear-gradient(135deg, #f7971e 0%, #ffd200 100%)" if stats['pending_count'] > 0 else \
                     "linear-gradient(135deg, #56ab2f 0%, #a8e063 100%)"
        st.markdown(f"""
        <div style="background: {urgency_bg};
                    padding: 1.5rem; border-radius: 16px; text-align: center; color: white;">
            <p style="margin: 0; font-size: 2.5rem; font-weight: bold;">{stats['pending_count']}</p>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">답변 대기 중</p>
        </div>
        """, unsafe_allow_html=True)

    with col4:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #654ea3 0%, #eaafc8 100%);
                    padding: 1.5rem; border-radius: 16px; text-align: center; color: white;">
            <p style="margin: 0; font-size: 2.5rem; font-weight: bold;">{stats['completed_books']}</p>
            <p style="margin: 0.5rem 0 0 0; opacity: 0.9;">완료된 책 수</p>
        </div>
        """, unsafe_allow_html=True)

    # 긴급 알림
    if stats['pending_count'] > 0:
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #FFEBEE 0%, #FFCDD2 100%);
                    padding: 1rem 1.5rem; border-radius: 12px; margin: 1.5rem 0;
                    border-left: 4px solid #F44336; display: flex; align-items: center; gap: 1rem;">
            <span style="font-size: 1.5rem;">⚠️</span>
            <div>
                <p style="margin: 0; font-weight: bold; color: #C62828;">
                    {stats['pending_count']}개의 질문이 답변을 기다리고 있습니다!
                </p>
                <p style="margin: 0.25rem 0 0 0; font-size: 0.9rem; color: #666;">
                    '질문 관리' 메뉴에서 답변해 주세요.
                </p>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 최근 활동 타임라인
    st.markdown("### 최근 활동")

    activities = get_recent_activities(10)

    if not activities:
        st.info("아직 활동 기록이 없습니다.")
        return

    for activity in activities:
        icon = "❓" if activity['type'] == 'question' else "✅"
        bg_color = "#E3F2FD" if activity['type'] == 'question' else "#E8F5E9"
        border_color = "#2196F3" if activity['type'] == 'question' else "#4CAF50"

        try:
            time_str = activity['time'][:16].replace("T", " ") if activity['time'] else "시간 정보 없음"
        except Exception:
            time_str = "시간 정보 없음"

        action_text = "질문함" if activity['type'] == 'question' else "답변함"

        st.markdown(f"""
        <div style="background: {bg_color}; padding: 1rem; border-radius: 12px;
                    margin-bottom: 0.75rem; border-left: 4px solid {border_color};
                    display: flex; align-items: center; gap: 1rem;">
            <span style="font-size: 1.5rem;">{icon}</span>
            <div style="flex: 1;">
                <p style="margin: 0; font-weight: bold;">
                    {activity['student']} <span style="font-weight: normal; color: #666;">({action_text})</span>
                </p>
                <p style="margin: 0.25rem 0 0 0; font-size: 0.9rem; color: #666;">
                    [{activity['step']}] {activity['content']}
                </p>
            </div>
            <span style="font-size: 0.8rem; color: #999;">{time_str}</span>
        </div>
        """, unsafe_allow_html=True)


def render_student_management():
    """수강생 관리 - 검색/필터/상세 정보"""
    st.markdown("## 수강생 관리")

    messages = load_all_messages_json()

    if not messages:
        st.info("아직 등록된 수강생이 없습니다.")
        return

    # 수강생별 데이터 집계
    students = {}
    for msg in messages:
        name = msg.get("student_name", "익명")
        if name not in students:
            students[name] = {
                "questions": [],
                "book_title": "",
                "book_topic": "",
                "last_step": "",
                "last_activity": "",
                "completed_chapters": set(),
                "total_char_count": 0,
            }

        students[name]["questions"].append(msg)

        # 가장 최근 활동 기준 업데이트
        if msg.get("timestamp", "") > students[name]["last_activity"]:
            students[name]["last_activity"] = msg.get("timestamp", "")
            students[name]["last_step"] = msg.get("step_name", "")
            if msg.get("book_title"):
                students[name]["book_title"] = msg.get("book_title")
            if msg.get("book_topic"):
                students[name]["book_topic"] = msg.get("book_topic")

        # 완료한 단계 추적
        step = msg.get("step_name", "")
        if step:
            students[name]["completed_chapters"].add(step)

        # 총 글자 수 (메시지 길이 합계로 추정)
        students[name]["total_char_count"] += len(msg.get("message", ""))

    # 검색/필터 UI
    col1, col2, col3 = st.columns(3)

    with col1:
        search_query = st.text_input("수강생 검색", placeholder="이름으로 검색...")

    with col2:
        step_filter = st.selectbox(
            "단계 필터",
            ["전체"] + list(STEP_NAMES.values())
        )

    with col3:
        status_filter = st.selectbox(
            "상태 필터",
            ["전체", "답변 대기 중", "정상"]
        )

    # 필터 적용
    filtered_students = {}
    for name, data in students.items():
        # 검색 필터
        if search_query and search_query.lower() not in name.lower():
            continue

        # 단계 필터
        if step_filter != "전체" and step_filter != data["last_step"]:
            continue

        # 상태 필터
        pending = sum(1 for q in data["questions"] if q.get("status") == "pending")
        if status_filter == "답변 대기 중" and pending == 0:
            continue
        if status_filter == "정상" and pending > 0:
            continue

        filtered_students[name] = data

    st.markdown(f"**총 {len(filtered_students)}명의 수강생**")
    st.markdown("---")

    # 수강생 목록
    for name, data in filtered_students.items():
        pending_count = sum(1 for q in data["questions"] if q.get("status") == "pending")

        # 마지막 활동 시간 계산
        last_activity_str = ""
        if data["last_activity"]:
            try:
                last_dt = datetime.fromisoformat(data["last_activity"])
                diff = datetime.now() - last_dt
                if diff.days > 0:
                    last_activity_str = f"{diff.days}일 전"
                elif diff.seconds > 3600:
                    last_activity_str = f"{diff.seconds // 3600}시간 전"
                else:
                    last_activity_str = f"{diff.seconds // 60}분 전"
            except Exception:
                last_activity_str = data["last_activity"][:16]

        # 상태 배지
        if pending_count > 0:
            status_badge = f'<span style="background: #FFEBEE; color: #C62828; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem;">{pending_count}개 대기</span>'
        else:
            status_badge = '<span style="background: #E8F5E9; color: #2E7D32; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem;">정상</span>'

        with st.expander(f"👤 {name} | {data['last_step']} | 마지막 활동: {last_activity_str}"):
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("#### 기본 정보")
                st.markdown(f"**책 제목:** {data['book_title'] or '미정'}")
                st.markdown(f"**책 주제:** {data['book_topic'] or '미정'}")
                st.markdown(f"**현재 단계:** {data['last_step']}")
                st.markdown(f"**상태:** {status_badge}", unsafe_allow_html=True)

            with col2:
                st.markdown("#### 진행 통계")
                st.markdown(f"**총 질문:** {len(data['questions'])}개")
                st.markdown(f"**완료한 장:** {len(data['completed_chapters'])}개 / 7개")
                st.markdown(f"**총 글자 수:** {data['total_char_count']:,}자")
                st.markdown(f"**마지막 활동:** {data['last_activity'][:16] if data['last_activity'] else 'N/A'}")

            # 진행 현황 바
            progress = len(data['completed_chapters']) / 7 * 100
            st.markdown(f"""
            <div style="background: #E0E0E0; border-radius: 10px; height: 20px; margin: 1rem 0;">
                <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            width: {progress}%; height: 100%; border-radius: 10px;
                            display: flex; align-items: center; justify-content: center;
                            color: white; font-size: 0.75rem; font-weight: bold;">
                    {progress:.0f}%
                </div>
            </div>
            """, unsafe_allow_html=True)

            # 상세 보기 - 완료한 장 목록
            st.markdown("**완료한 단계:**")
            completed = sorted(list(data['completed_chapters']))
            if completed:
                st.markdown(", ".join(completed))
            else:
                st.caption("아직 완료한 단계가 없습니다.")

            # 질문 히스토리 (최근 5개)
            st.markdown("---")
            st.markdown("**최근 질문 히스토리:**")
            sorted_questions = sorted(data["questions"], key=lambda x: x.get("timestamp", ""), reverse=True)[:5]
            for q in sorted_questions:
                status_icon = "⏳" if q.get("status") == "pending" else "✅"
                msg_preview = q.get("message", "")[:60] + "..." if len(q.get("message", "")) > 60 else q.get("message", "")
                st.markdown(f"- {status_icon} [{q.get('step_name', '')}] {msg_preview}")


def render_question_management():
    """질문 관리 - 상태별 필터, 일괄 답변, 빠른 답변 템플릿"""
    st.markdown("## 질문 관리")

    messages = load_all_messages_json()

    if not messages:
        st.info("아직 질문이 없습니다.")
        return

    # 탭으로 구분
    tab1, tab2, tab3 = st.tabs(["답변 대기", "전체 질문", "일괄 답변"])

    with tab1:
        render_pending_questions(messages)

    with tab2:
        render_all_questions(messages)

    with tab3:
        render_batch_reply(messages)


def render_pending_questions(messages):
    """답변 대기 중인 질문"""
    pending = [m for m in messages if m.get("status") == "pending"]

    if not pending:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
                    padding: 2rem; border-radius: 16px; text-align: center;">
            <p style="font-size: 2rem; margin: 0;">🎉</p>
            <p style="font-size: 1.2rem; margin: 0.5rem 0; color: #2E7D32; font-weight: bold;">
                모든 질문에 답변 완료!
            </p>
            <p style="color: #666; margin: 0;">답변 대기 중인 질문이 없습니다.</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # 최신순 정렬
    pending.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

    # 긴급도별 분류
    urgent = [m for m in pending if "많이 급해요" in m.get("message", "")]

    if urgent:
        st.markdown(f"""
        <div style="background: #FFEBEE; padding: 0.8rem 1rem; border-radius: 10px;
                    margin-bottom: 1rem; border-left: 4px solid #F44336;">
            <b style="color: #C62828;">⚠️ 긴급 질문 {len(urgent)}개</b>가 있습니다!
        </div>
        """, unsafe_allow_html=True)

    st.markdown(f"**답변 대기 중: {len(pending)}개**")

    for msg in pending:
        render_question_card(msg, show_reply_form=True)


def render_all_questions(messages):
    """전체 질문 목록"""
    # 필터 UI
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        status_filter = st.selectbox(
            "상태",
            ["전체", "답변 대기", "답변 완료", "보류"],
            key="all_q_status"
        )

    with col2:
        step_filter = st.selectbox(
            "단계",
            ["전체"] + list(STEP_NAMES.values()),
            key="all_q_step"
        )

    with col3:
        student_names = list(set(m.get("student_name", "익명") for m in messages))
        student_filter = st.selectbox(
            "수강생",
            ["전체"] + sorted(student_names),
            key="all_q_student"
        )

    with col4:
        sort_order = st.selectbox(
            "정렬",
            ["최신순", "오래된순"],
            key="all_q_sort"
        )

    # 필터 적용
    filtered = messages.copy()

    if status_filter != "전체":
        status_map = {"답변 대기": "pending", "답변 완료": "answered", "보류": "on_hold"}
        filtered = [m for m in filtered if m.get("status") == status_map.get(status_filter)]

    if step_filter != "전체":
        filtered = [m for m in filtered if m.get("step_name") == step_filter]

    if student_filter != "전체":
        filtered = [m for m in filtered if m.get("student_name") == student_filter]

    # 정렬
    filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=(sort_order == "최신순"))

    st.markdown(f"**총 {len(filtered)}개 질문**")
    st.markdown("---")

    for msg in filtered:
        render_question_card(msg, show_reply_form=False, compact=True)


def render_question_card(msg, show_reply_form=False, compact=False):
    """질문 카드 렌더링"""
    is_urgent = "많이 급해요" in msg.get("message", "")
    border_color = "#F44336" if is_urgent else "#FF9800" if msg.get("status") == "pending" else "#4CAF50"

    # 메시지에서 긴급도 태그 분리
    message_content = msg.get("message", "")
    urgency_tag = ""
    if message_content.startswith("["):
        bracket_end = message_content.find("]")
        if bracket_end > 0:
            urgency_tag = message_content[1:bracket_end]
            message_content = message_content[bracket_end + 2:]

    status_emoji = {"pending": "⏳", "answered": "✅", "on_hold": "⏸️"}.get(msg.get("status"), "❓")

    if compact:
        # 간략한 표시
        with st.expander(
            f"{status_emoji} {msg.get('student_name', '익명')} | {msg.get('step_name', '')} | {msg.get('timestamp', '')[:10]}"
        ):
            st.markdown(f"**질문:** {message_content}")
            if msg.get("admin_reply"):
                st.markdown(f"**답변:** {msg.get('admin_reply')}")
                st.caption(f"답변 시간: {msg.get('reply_timestamp', '')[:16]}")

            # 상태 변경 버튼
            col1, col2, col3 = st.columns(3)
            with col1:
                if msg.get("status") != "answered" and st.button("✅ 답변완료", key=f"complete_{msg.get('id')}"):
                    update_message_status(msg.get("id"), "answered", msg.get("admin_reply", "확인했습니다."))
                    st.rerun()
            with col2:
                if msg.get("status") != "pending" and st.button("⏳ 대기중", key=f"pending_{msg.get('id')}"):
                    update_message_status(msg.get("id"), "pending")
                    st.rerun()
            with col3:
                if msg.get("status") != "on_hold" and st.button("⏸️ 보류", key=f"hold_{msg.get('id')}"):
                    update_message_status(msg.get("id"), "on_hold")
                    st.rerun()
    else:
        # 상세 표시 (답변 폼 포함)
        with st.expander(
            f"{'🔴' if is_urgent else '🟡'} [{msg.get('step_name', '?')}] {msg.get('student_name', '익명')} - {msg.get('timestamp', '')[:16]}",
            expanded=True
        ):
            col1, col2 = st.columns([3, 2])

            with col1:
                # 학생 정보
                st.markdown(f"""
                <div style="background: #F5F5F5; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
                    <p style="margin: 0 0 0.5rem 0;"><b>수강생:</b> {msg.get('student_name', '익명')}</p>
                    <p style="margin: 0 0 0.5rem 0;"><b>책 제목:</b> {msg.get('book_title', '미정')}</p>
                    <p style="margin: 0 0 0.5rem 0;"><b>주제:</b> {msg.get('book_topic', '미정')}</p>
                    <p style="margin: 0;"><b>단계:</b> {msg.get('step_name', '알 수 없음')}</p>
                </div>
                """, unsafe_allow_html=True)

                # 질문 내용
                st.markdown(f"""
                <div style="background: #E3F2FD; padding: 1rem; border-radius: 10px;
                            border-left: 4px solid {border_color};">
                    <p style="margin: 0 0 0.5rem 0; color: #666; font-size: 0.85rem;">
                        질문 내용 {f'[{urgency_tag}]' if urgency_tag else ''}
                    </p>
                    <p style="margin: 0; font-size: 1rem; line-height: 1.6;">{message_content}</p>
                </div>
                """, unsafe_allow_html=True)

                st.caption(f"접수 시간: {msg.get('timestamp', '')[:19]}")

            with col2:
                if show_reply_form:
                    st.markdown("**답변 작성**")

                    # 빠른 답변 템플릿 선택
                    template_choice = st.selectbox(
                        "빠른 답변 템플릿",
                        ["직접 작성"] + list(QUICK_REPLY_TEMPLATES.keys()),
                        key=f"template_{msg.get('id')}"
                    )

                    default_reply = ""
                    if template_choice != "직접 작성":
                        default_reply = QUICK_REPLY_TEMPLATES.get(template_choice, "")

                    with st.form(f"reply_form_{msg.get('id')}"):
                        reply = st.text_area(
                            "답변 내용",
                            value=default_reply,
                            height=150,
                            placeholder="학생에게 보낼 답변을 작성하세요.",
                            key=f"reply_{msg.get('id')}"
                        )

                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.form_submit_button("답변 완료", type="primary", use_container_width=True):
                                if reply.strip():
                                    if len(reply.strip()) < 10:
                                        st.warning("조금 더 자세히 답변해주세요.")
                                    elif update_message_status(msg.get("id"), "answered", reply.strip()):
                                        st.success("답변이 저장되었습니다!")
                                        st.rerun()
                                    else:
                                        st.error("저장에 실패했습니다.")
                                else:
                                    st.warning("답변 내용을 입력해주세요.")

                        with col_b:
                            if st.form_submit_button("보류", use_container_width=True):
                                if update_message_status(msg.get("id"), "on_hold"):
                                    st.info("보류 처리되었습니다.")
                                    st.rerun()


def render_batch_reply(messages):
    """일괄 답변 기능"""
    st.markdown("### 일괄 답변")
    st.caption("여러 질문에 동일한 답변을 한 번에 보낼 수 있습니다.")

    pending = [m for m in messages if m.get("status") == "pending"]

    if not pending:
        st.info("답변 대기 중인 질문이 없습니다.")
        return

    # 질문 선택
    st.markdown("**답변할 질문 선택:**")

    selected_ids = []
    for msg in pending:
        msg_preview = msg.get("message", "")[:60] + "..." if len(msg.get("message", "")) > 60 else msg.get("message", "")
        if st.checkbox(
            f"[{msg.get('student_name', '익명')}] {msg_preview}",
            key=f"batch_select_{msg.get('id')}"
        ):
            selected_ids.append(msg.get("id"))

    if selected_ids:
        st.markdown(f"**{len(selected_ids)}개 선택됨**")

        # 템플릿 선택
        template_choice = st.selectbox(
            "빠른 답변 템플릿",
            ["직접 작성"] + list(QUICK_REPLY_TEMPLATES.keys()),
            key="batch_template"
        )

        default_reply = ""
        if template_choice != "직접 작성":
            default_reply = QUICK_REPLY_TEMPLATES.get(template_choice, "")

        batch_reply = st.text_area(
            "일괄 답변 내용",
            value=default_reply,
            height=150,
            placeholder="선택한 모든 질문에 보낼 답변을 작성하세요."
        )

        if st.button("일괄 답변 전송", type="primary"):
            if batch_reply.strip() and len(batch_reply.strip()) >= 10:
                success_count = 0
                for msg_id in selected_ids:
                    if update_message_status(msg_id, "answered", batch_reply.strip()):
                        success_count += 1

                st.success(f"{success_count}개 질문에 답변을 완료했습니다!")
                st.rerun()
            else:
                st.warning("답변 내용을 10자 이상 입력해주세요.")


def render_notification_settings():
    """알림 설정"""
    st.markdown("## 알림 설정")

    # 현재 설정 불러오기 (session_state에서)
    if "notification_settings" not in st.session_state:
        st.session_state.notification_settings = {
            "email_enabled": False,
            "email_address": "",
            "kakao_enabled": False,
            "daily_report": False,
            "daily_report_time": "09:00",
            "urgent_alert": True,
        }

    settings = st.session_state.notification_settings

    st.markdown("### 새 질문 알림")
    st.caption("새로운 질문이 접수되면 알림을 받을 수 있습니다.")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div style="background: #E3F2FD; padding: 1rem; border-radius: 12px; margin-bottom: 1rem;">
            <h4 style="margin: 0 0 0.5rem 0;">📧 이메일 알림</h4>
            <p style="margin: 0; font-size: 0.85rem; color: #666;">새 질문이 오면 이메일로 알려드립니다.</p>
        </div>
        """, unsafe_allow_html=True)

        email_enabled = st.toggle("이메일 알림 활성화", value=settings["email_enabled"], key="email_toggle")

        if email_enabled:
            email_address = st.text_input(
                "알림 받을 이메일",
                value=settings["email_address"],
                placeholder="your-email@example.com"
            )
            settings["email_enabled"] = True
            settings["email_address"] = email_address
        else:
            settings["email_enabled"] = False

    with col2:
        st.markdown("""
        <div style="background: #FFF3E0; padding: 1rem; border-radius: 12px; margin-bottom: 1rem;">
            <h4 style="margin: 0 0 0.5rem 0;">💬 카카오톡 알림</h4>
            <p style="margin: 0; font-size: 0.85rem; color: #666;">카카오톡으로 실시간 알림을 받습니다.</p>
        </div>
        """, unsafe_allow_html=True)

        kakao_enabled = st.toggle("카카오톡 알림 활성화", value=settings["kakao_enabled"], key="kakao_toggle")

        if kakao_enabled:
            st.info("카카오톡 알림은 카카오 알림톡 API 연동이 필요합니다. secrets.toml에 API 키를 설정해주세요.")
            settings["kakao_enabled"] = True
        else:
            settings["kakao_enabled"] = False

    st.markdown("---")
    st.markdown("### 일일 요약 리포트")
    st.caption("매일 정해진 시간에 요약 리포트를 받을 수 있습니다.")

    daily_enabled = st.toggle("일일 요약 리포트 활성화", value=settings["daily_report"], key="daily_toggle")

    if daily_enabled:
        report_time = st.time_input("리포트 수신 시간", value=datetime.strptime(settings["daily_report_time"], "%H:%M").time())
        settings["daily_report"] = True
        settings["daily_report_time"] = report_time.strftime("%H:%M")

        st.markdown("""
        **리포트에 포함되는 내용:**
        - 어제 접수된 질문 수
        - 답변 대기 중인 질문 수
        - 신규 수강생 수
        - 주간 통계 요약
        """)
    else:
        settings["daily_report"] = False

    st.markdown("---")
    st.markdown("### 긴급 알림")

    urgent_enabled = st.toggle(
        "긴급 질문 즉시 알림",
        value=settings["urgent_alert"],
        help="'많이 급해요'로 표시된 질문이 오면 즉시 알림을 보냅니다.",
        key="urgent_toggle"
    )
    settings["urgent_alert"] = urgent_enabled

    # 설정 저장
    st.session_state.notification_settings = settings

    if st.button("설정 저장", type="primary"):
        st.success("알림 설정이 저장되었습니다!")
        st.info("실제 알림 기능은 서버 환경에서 백그라운드 작업으로 구현해야 합니다.")


def render_data_analysis():
    """데이터 분석 - 기간별 통계, FAQ 분석"""
    st.markdown("## 데이터 분석")

    messages = load_all_messages_json()

    if not messages:
        st.info("분석할 데이터가 없습니다.")
        return

    # 탭으로 구분
    tab1, tab2, tab3 = st.tabs(["기간별 통계", "자주 묻는 질문", "단계별 분석"])

    with tab1:
        render_period_stats(messages)

    with tab2:
        render_faq_analysis(messages)

    with tab3:
        render_step_analysis(messages)


def render_period_stats(messages):
    """기간별 통계"""
    st.markdown("### 기간별 질문 통계")

    # 기간 선택
    period = st.selectbox("기간 선택", ["최근 7일", "최근 30일", "최근 90일", "전체"])

    # 기간에 따른 필터링
    now = datetime.now()
    if period == "최근 7일":
        cutoff = now - timedelta(days=7)
    elif period == "최근 30일":
        cutoff = now - timedelta(days=30)
    elif period == "최근 90일":
        cutoff = now - timedelta(days=90)
    else:
        cutoff = datetime.min

    filtered = []
    for m in messages:
        try:
            msg_dt = datetime.fromisoformat(m.get("timestamp", ""))
            if msg_dt >= cutoff:
                filtered.append(m)
        except Exception:
            continue

    if not filtered:
        st.info("선택한 기간에 데이터가 없습니다.")
        return

    # 일별 통계 집계
    daily_stats = defaultdict(lambda: {"questions": 0, "answered": 0})

    for m in filtered:
        try:
            date_key = m.get("timestamp", "")[:10]
            daily_stats[date_key]["questions"] += 1
            if m.get("status") == "answered":
                daily_stats[date_key]["answered"] += 1
        except Exception:
            continue

    # 차트 데이터 준비
    dates = sorted(daily_stats.keys())
    questions_data = [daily_stats[d]["questions"] for d in dates]
    answered_data = [daily_stats[d]["answered"] for d in dates]

    # 간단한 막대 차트 (Streamlit 기본 차트)
    import pandas as pd

    chart_data = pd.DataFrame({
        "날짜": dates,
        "질문 수": questions_data,
        "답변 완료": answered_data,
    })
    chart_data = chart_data.set_index("날짜")

    st.bar_chart(chart_data)

    # 요약 통계
    total_questions = sum(questions_data)
    total_answered = sum(answered_data)
    answer_rate = (total_answered / total_questions * 100) if total_questions > 0 else 0

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("총 질문 수", f"{total_questions}개")
    with col2:
        st.metric("답변 완료", f"{total_answered}개")
    with col3:
        st.metric("답변율", f"{answer_rate:.1f}%")


def render_faq_analysis(messages):
    """자주 묻는 질문 분석"""
    st.markdown("### 자주 묻는 질문 분석")
    st.caption("질문에서 자주 등장하는 키워드를 분석합니다.")

    # 키워드 추출 (간단한 단어 빈도 분석)
    keywords = []
    important_words = ["제목", "목차", "글쓰기", "출판", "수정", "어려워", "모르겠", "도움", "방법", "예시", "확인", "진행", "다음", "완료"]

    for m in messages:
        content = m.get("message", "").lower()
        for word in important_words:
            if word in content:
                keywords.append(word)

    if not keywords:
        st.info("분석할 키워드가 충분하지 않습니다.")
        return

    # 키워드 빈도 계산
    keyword_counts = Counter(keywords)
    top_keywords = keyword_counts.most_common(10)

    st.markdown("**자주 등장하는 키워드:**")

    for keyword, count in top_keywords:
        percentage = count / len(messages) * 100
        st.markdown(f"""
        <div style="display: flex; align-items: center; margin-bottom: 0.5rem;">
            <span style="width: 80px; font-weight: bold;">{keyword}</span>
            <div style="flex: 1; background: #E0E0E0; border-radius: 5px; height: 20px; margin: 0 1rem;">
                <div style="background: #667eea; width: {min(percentage * 2, 100)}%; height: 100%; border-radius: 5px;"></div>
            </div>
            <span style="width: 60px; text-align: right;">{count}회</span>
        </div>
        """, unsafe_allow_html=True)

    # 단계별 질문 키워드
    st.markdown("---")
    st.markdown("**단계별 주요 질문 내용:**")

    step_questions = defaultdict(list)
    for m in messages:
        step = m.get("step_name", "기타")
        step_questions[step].append(m.get("message", ""))

    for step, questions in sorted(step_questions.items()):
        with st.expander(f"{step} ({len(questions)}개 질문)"):
            for q in questions[:5]:
                st.markdown(f"- {q[:100]}...")


def render_step_analysis(messages):
    """단계별 분석"""
    st.markdown("### 단계별 통계")

    # 단계별 집계
    step_stats = defaultdict(lambda: {"total": 0, "pending": 0, "answered": 0})

    for m in messages:
        step = m.get("step_name", "기타")
        step_stats[step]["total"] += 1
        if m.get("status") == "pending":
            step_stats[step]["pending"] += 1
        elif m.get("status") == "answered":
            step_stats[step]["answered"] += 1

    # 테이블 형태로 표시
    import pandas as pd

    data = []
    for step, stats in sorted(step_stats.items()):
        answer_rate = (stats["answered"] / stats["total"] * 100) if stats["total"] > 0 else 0
        data.append({
            "단계": step,
            "총 질문": stats["total"],
            "답변 완료": stats["answered"],
            "대기 중": stats["pending"],
            "답변율": f"{answer_rate:.1f}%"
        })

    df = pd.DataFrame(data)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # 단계별 질문 수 차트
    st.markdown("**단계별 질문 분포:**")

    chart_data = pd.DataFrame({
        "단계": [d["단계"] for d in data],
        "질문 수": [d["총 질문"] for d in data],
    })
    chart_data = chart_data.set_index("단계")
    st.bar_chart(chart_data)

    # 인사이트
    if data:
        most_questions_step = max(data, key=lambda x: x["총 질문"])
        most_pending_step = max(data, key=lambda x: x["대기 중"])

        st.markdown("---")
        st.markdown("**분석 인사이트:**")
        st.markdown(f"- 가장 많은 질문이 발생하는 단계: **{most_questions_step['단계']}** ({most_questions_step['총 질문']}개)")
        if most_pending_step["대기 중"] > 0:
            st.markdown(f"- 답변이 가장 많이 필요한 단계: **{most_pending_step['단계']}** ({most_pending_step['대기 중']}개 대기)")


def render_data_export():
    """데이터 내보내기"""
    st.markdown("## 데이터 내보내기")

    try:
        messages = load_all_messages_json()
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return

    if not messages:
        st.info("내보낼 데이터가 없습니다.")
        return

    st.markdown(f"""
    <div style="background: #F5F5F5; padding: 1rem; border-radius: 12px; margin-bottom: 1.5rem;">
        <p style="margin: 0;"><b>내보낼 데이터:</b> 총 {len(messages)}개 질문</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        <div style="background: #E3F2FD; padding: 1rem; border-radius: 12px; margin-bottom: 0.5rem;">
            <h4 style="margin: 0 0 0.5rem 0;">JSON 형식</h4>
            <p style="margin: 0; font-size: 0.85rem; color: #666;">프로그래밍, 데이터 백업용</p>
        </div>
        """, unsafe_allow_html=True)

        json_data = json.dumps(messages, ensure_ascii=False, indent=2)
        st.download_button(
            label="JSON 다운로드",
            data=json_data,
            file_name=f"질문목록_{datetime.now().strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
            use_container_width=True,
            type="primary"
        )

    with col2:
        st.markdown("""
        <div style="background: #E8F5E9; padding: 1rem; border-radius: 12px; margin-bottom: 0.5rem;">
            <h4 style="margin: 0 0 0.5rem 0;">CSV 형식</h4>
            <p style="margin: 0; font-size: 0.85rem; color: #666;">엑셀, 구글 시트에서 열기</p>
        </div>
        """, unsafe_allow_html=True)

        import csv
        import io

        output = io.StringIO()
        fieldnames = ['id', 'student_name', 'timestamp', 'message', 'step_name',
                      'status', 'book_title', 'book_topic', 'admin_reply', 'reply_timestamp']

        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(messages)

        st.download_button(
            label="CSV 다운로드",
            data=output.getvalue(),
            file_name=f"질문목록_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary"
        )


def render_settings():
    """설정 페이지"""
    st.markdown("## 설정")

    st.markdown("### 관리자 연락처 정보")
    st.info("""
    관리자 연락처 정보는 `.streamlit/secrets.toml` 파일에서 설정합니다.

    ```toml
    ADMIN_KAKAO_LINK = "https://open.kakao.com/o/your-link"
    ADMIN_EMAIL = "your-email@example.com"
    ADMIN_PHONE = "010-1234-5678"
    ADMIN_SHOW_PHONE = true
    ADMIN_PASSWORD = "your-admin-password"
    ```
    """)

    st.markdown("### 빠른 답변 템플릿 관리")
    st.caption("현재 등록된 빠른 답변 템플릿입니다.")

    for name, content in QUICK_REPLY_TEMPLATES.items():
        with st.expander(f"템플릿: {name}"):
            st.text_area("내용", value=content, height=100, disabled=True, key=f"template_view_{name}")

    st.info("템플릿을 추가/수정하려면 코드의 QUICK_REPLY_TEMPLATES를 수정하세요.")

    st.markdown("---")
    st.markdown("### 데이터 관리")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("🗑️ 답변 완료된 질문 아카이브", use_container_width=True):
            st.warning("이 기능은 답변 완료된 질문을 별도 보관함으로 이동합니다. (미구현)")

    with col2:
        if st.button("🔄 데이터 새로고침", use_container_width=True):
            st.rerun()


def main():
    """메인 함수"""
    # 데이터 디렉토리 확인
    ensure_data_directory()

    # 인증 확인
    if not check_admin_auth():
        return

    # 사이드바 네비게이션
    with st.sidebar:
        st.markdown("""
        <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white; padding: 1rem; border-radius: 12px; margin-bottom: 1rem; text-align: center;">
            <h3 style="margin: 0; color: white;">관리자 대시보드</h3>
        </div>
        """, unsafe_allow_html=True)

        menu = st.radio(
            "메뉴 선택",
            [
                "🏠 대시보드 홈",
                "👥 수강생 관리",
                "💬 질문 관리",
                "🔔 알림 설정",
                "📊 데이터 분석",
                "📥 데이터 내보내기",
                "⚙️ 설정"
            ],
            label_visibility="collapsed"
        )

        st.markdown("---")

        # 빠른 통계
        pending_count = get_pending_messages_count()
        if pending_count > 0:
            st.markdown(f"""
            <div style="background: #FFEBEE; padding: 0.75rem; border-radius: 10px;
                        border-left: 4px solid #F44336; margin-bottom: 1rem;">
                <p style="margin: 0; font-weight: bold; color: #C62828;">
                    🔔 {pending_count}개 답변 대기
                </p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="background: #E8F5E9; padding: 0.75rem; border-radius: 10px;
                        border-left: 4px solid #4CAF50; margin-bottom: 1rem;">
                <p style="margin: 0; font-weight: bold; color: #2E7D32;">
                    ✅ 모든 질문 답변 완료
                </p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        if st.button("🚪 로그아웃", use_container_width=True):
            st.session_state.admin_authenticated = False
            st.rerun()

    # 메인 콘텐츠
    if menu == "🏠 대시보드 홈":
        render_dashboard_home()
    elif menu == "👥 수강생 관리":
        render_student_management()
    elif menu == "💬 질문 관리":
        render_question_management()
    elif menu == "🔔 알림 설정":
        render_notification_settings()
    elif menu == "📊 데이터 분석":
        render_data_analysis()
    elif menu == "📥 데이터 내보내기":
        render_data_export()
    elif menu == "⚙️ 설정":
        render_settings()


if __name__ == "__main__":
    main()

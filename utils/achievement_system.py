"""
성취 시스템 모듈
================
진행률 표시, 마일스톤, 뱃지, 동기부여 메시지 관리
"""
import streamlit as st
from datetime import datetime, timedelta
import random
import json

# ============================================
# 뱃지 시스템 정의
# ============================================
BADGES = {
    "first_chapter": {
        "id": "first_chapter",
        "emoji": "🌱",
        "name": "첫 발걸음",
        "description": "첫 번째 장을 완료하셨습니다.",
        "condition": lambda completed: completed >= 1,
        "tier": 1
    },
    "five_chapters": {
        "id": "five_chapters",
        "emoji": "📝",
        "name": "꾸준한 집필",
        "description": "5장을 완료하셨습니다.",
        "condition": lambda completed: completed >= 5,
        "tier": 2
    },
    "ten_chapters": {
        "id": "ten_chapters",
        "emoji": "✨",
        "name": "10장 달성",
        "description": "10장을 완료하셨습니다.",
        "condition": lambda completed: completed >= 10,
        "tier": 3
    },
    "twenty_chapters": {
        "id": "twenty_chapters",
        "emoji": "🔥",
        "name": "절반 돌파",
        "description": "20장 완료, 절반을 돌파하셨습니다.",
        "condition": lambda completed: completed >= 20,
        "tier": 4
    },
    "thirty_chapters": {
        "id": "thirty_chapters",
        "emoji": "🚀",
        "name": "완성 목전",
        "description": "30장 완료, 거의 다 오셨습니다.",
        "condition": lambda completed: completed >= 30,
        "tier": 5
    },
    "forty_chapters": {
        "id": "forty_chapters",
        "emoji": "👑",
        "name": "책 완성",
        "description": "40장 완료, 축하드립니다!",
        "condition": lambda completed: completed >= 40,
        "tier": 6
    },
    "speed_writer": {
        "id": "speed_writer",
        "emoji": "⚡",
        "name": "집중 집필",
        "description": "하루에 5장 이상 작성하셨습니다.",
        "condition": lambda completed: False,  # 별도 체크
        "tier": 3
    },
    "streak_3": {
        "id": "streak_3",
        "emoji": "🔗",
        "name": "3일 연속",
        "description": "3일 연속으로 집필하셨습니다.",
        "condition": lambda streak: streak >= 3,
        "tier": 2
    },
    "streak_7": {
        "id": "streak_7",
        "emoji": "🏆",
        "name": "일주일 챔피언",
        "description": "7일 연속으로 집필하셨습니다.",
        "condition": lambda streak: streak >= 7,
        "tier": 4
    },
    "word_master_10k": {
        "id": "word_master_10k",
        "emoji": "📚",
        "name": "1만자 달성",
        "description": "총 10,000자를 작성하셨습니다.",
        "condition": lambda chars: chars >= 10000,
        "tier": 2
    },
    "word_master_30k": {
        "id": "word_master_30k",
        "emoji": "📖",
        "name": "3만자 달성",
        "description": "총 30,000자를 작성하셨습니다.",
        "condition": lambda chars: chars >= 30000,
        "tier": 4
    },
    "word_master_60k": {
        "id": "word_master_60k",
        "emoji": "📕",
        "name": "6만자 달성",
        "description": "목표 60,000자를 달성하셨습니다.",
        "condition": lambda chars: chars >= 60000,
        "tier": 6
    },
    "daily_goal": {
        "id": "daily_goal",
        "emoji": "🎯",
        "name": "일일 목표 달성",
        "description": "오늘의 목표를 달성하셨습니다.",
        "condition": lambda achieved: achieved,
        "tier": 2
    },
}

# ============================================
# 마일스톤 메시지 정의
# ============================================
MILESTONE_MESSAGES = {
    5: {
        "title": "5장 완료",
        "message": "훌륭합니다! 벌써 5장을 완료하셨습니다. 🎉",
        "emoji": "🌟",
        "color": "#4CAF50"
    },
    10: {
        "title": "10장 완료 ✨",
        "message": "10장을 돌파하셨습니다! 순조롭게 진행되고 있습니다. ✨",
        "emoji": "✨",
        "color": "#2196F3"
    },
    15: {
        "title": "15장 완료",
        "message": "대단합니다! 15장 완료, 절반이 가까워지고 있습니다. 💪",
        "emoji": "💪",
        "color": "#9C27B0"
    },
    20: {
        "title": "🔥 절반 돌파 🔥",
        "message": "축하드립니다! 절반을 돌파하셨습니다. 정말 대단한 성과입니다! 🎉",
        "emoji": "🔥",
        "color": "#FF5722",
        "special": True
    },
    25: {
        "title": "25장 완료",
        "message": "훌륭합니다! 절반을 넘어섰습니다. 이제 완성이 눈앞입니다. ⭐",
        "emoji": "⭐",
        "color": "#FFC107"
    },
    30: {
        "title": "🚀 30장 완료 🚀",
        "message": "30장 완료! 거의 다 오셨습니다. 조금만 더 힘내세요! 🚀✨",
        "emoji": "🚀",
        "color": "#E91E63",
        "special": True
    },
    35: {
        "title": "35장 완료",
        "message": "놀라운 성과입니다! 5장만 더 쓰시면 완성입니다. 파이팅! 🌈",
        "emoji": "🌈",
        "color": "#00BCD4"
    },
    40: {
        "title": "👑 책 완성 👑",
        "message": "축하드립니다! 드디어 책을 완성하셨습니다. 이제 당신은 작가입니다! 🎊🎉👑",
        "emoji": "👑",
        "color": "#FFD700",
        "special": True
    },
}

# ============================================
# 동기부여 메시지
# ============================================
MOTIVATION_MESSAGES = {
    "start": [
        "오늘도 좋은 집필 시간 되시길 바랍니다. 💪",
        "한 글자 한 글자가 책이 됩니다. 시작해 볼까요? ✨",
        "오늘의 집필 준비가 되셨나요? 함께 시작합니다. 🚀",
        "의미 있는 하루가 될 것입니다. 같이 써봅시다. 🌟",
    ],
    "progress_low": [  # 0-25%
        "좋습니다! 시작이 반입니다. 🌱",
        "한 걸음씩 나아가시면 됩니다. 천천히요. 🐢",
        "이렇게 꾸준히 쓰다 보면 금방입니다. 💫",
        "잘 진행되고 있습니다. 계속 가봅시다. ✨",
    ],
    "progress_mid": [  # 25-50%
        "많이 진행되었습니다. 대단합니다! 🌟",
        "점점 작가로 성장하고 계십니다. ✍️",
        "이 속도면 곧 완성하시겠네요. 😊",
        "절반에 가까워지고 있습니다. 파이팅! 💪",
    ],
    "progress_high": [  # 50-75%
        "절반을 넘기셨습니다! 🎉",
        "이제 완성이 눈앞입니다. 힘내세요! 🏃",
        "대단합니다! 진정한 작가가 되어 가고 있습니다. ⭐",
        "책이 점점 완성되어 가고 있습니다. 📚",
    ],
    "progress_almost": [  # 75-99%
        "거의 다 오셨습니다! 조금만 더요! 🚀",
        "완성이 보입니다! 마지막 힘을 내세요! 💪",
        "곧 책이 완성됩니다! 🎊",
        "대단합니다! 정말 얼마 남지 않았습니다! ✨",
    ],
    "completed": [
        "축하드립니다! 책을 완성하셨습니다! 👑",
        "이제 당신은 작가입니다! 🎉",
        "대단합니다! 목표를 이루셨습니다! 🌟",
        "훌륭합니다! 책 한 권 완성! 📕",
    ],
    "daily_goal_achieved": [
        "오늘 목표 달성! 대단합니다! 🎯",
        "목표를 달성하셨습니다! 훌륭합니다! ⭐",
        "오늘도 성공! 내일도 파이팅! 💪",
        "축하드립니다! 오늘의 목표를 완수하셨습니다! 🦸",
    ],
    "streak": [
        "연속 {days}일째 집필 중입니다! 대단합니다! 🔥",
        "{days}일 연속 작성 중입니다! 훌륭합니다! ⭐",
        "{days}일이나 연속으로 집필하고 계십니다! 💪",
        "{days}일째 꾸준히 쓰고 계십니다! 파이팅! 🚀",
    ],
}


def init_achievement_state():
    """성취 시스템 상태 초기화"""
    defaults = {
        "earned_badges": [],  # 획득한 뱃지 ID 리스트
        "shown_milestones": [],  # 이미 표시한 마일스톤
        "daily_goal": 5,  # 오늘의 목표 (기본 5장)
        "daily_completed": 0,  # 오늘 완료한 장 수
        "daily_goal_achieved": False,  # 오늘 목표 달성 여부
        "streak_days": 0,  # 연속 작성 일수
        "last_write_date": None,  # 마지막 작성 날짜
        "daily_chapters_written": 0,  # 오늘 작성한 장 수
        "session_start_chapters": 0,  # 세션 시작 시 완료 장 수
        "new_badge_to_show": None,  # 새로 획득한 뱃지 (팝업용)
        "new_milestone_to_show": None,  # 새로운 마일스톤 (팝업용)
    }
    for key, value in defaults.items():
        if f"achievement_{key}" not in st.session_state:
            st.session_state[f"achievement_{key}"] = value


def get_progress_percent():
    """진행률 퍼센트 계산"""
    parsed_toc = st.session_state.get("parsed_toc", [])
    drafts = st.session_state.get("drafts", {})

    if not parsed_toc:
        return 0

    return (len(drafts) / len(parsed_toc)) * 100


def get_completed_chapters():
    """완료된 장 수"""
    return len(st.session_state.get("drafts", {}))


def get_total_chars():
    """총 작성 글자 수"""
    drafts = st.session_state.get("drafts", {})
    return sum(
        len(d.replace(" ", "").replace("\n", ""))
        for d in drafts.values()
    )


def check_and_award_badges():
    """뱃지 조건 확인 및 수여"""
    init_achievement_state()

    completed = get_completed_chapters()
    total_chars = get_total_chars()
    streak = st.session_state.get("achievement_streak_days", 0)
    daily_achieved = st.session_state.get("achievement_daily_goal_achieved", False)

    earned = st.session_state.get("achievement_earned_badges", [])
    new_badges = []

    # 장 수 기반 뱃지
    chapter_badges = ["first_chapter", "five_chapters", "ten_chapters",
                      "twenty_chapters", "thirty_chapters", "forty_chapters"]
    for badge_id in chapter_badges:
        badge = BADGES[badge_id]
        if badge_id not in earned and badge["condition"](completed):
            earned.append(badge_id)
            new_badges.append(badge)

    # 글자 수 기반 뱃지
    char_badges = ["word_master_10k", "word_master_30k", "word_master_60k"]
    for badge_id in char_badges:
        badge = BADGES[badge_id]
        if badge_id not in earned and badge["condition"](total_chars):
            earned.append(badge_id)
            new_badges.append(badge)

    # 연속 작성 뱃지
    streak_badges = ["streak_3", "streak_7"]
    for badge_id in streak_badges:
        badge = BADGES[badge_id]
        if badge_id not in earned and badge["condition"](streak):
            earned.append(badge_id)
            new_badges.append(badge)

    # 일일 목표 달성 뱃지 (매일 리셋)
    if daily_achieved and "daily_goal" not in earned:
        badge = BADGES["daily_goal"]
        new_badges.append(badge)
        # daily_goal 뱃지는 매일 새로 얻을 수 있으므로 earned에 추가하지 않음

    st.session_state["achievement_earned_badges"] = earned

    # 새 뱃지가 있으면 팝업 표시를 위해 저장
    if new_badges:
        st.session_state["achievement_new_badge_to_show"] = new_badges[0]

    return new_badges


def check_milestone():
    """마일스톤 체크"""
    init_achievement_state()

    completed = get_completed_chapters()
    shown = st.session_state.get("achievement_shown_milestones", [])

    # 마일스톤 체크 (5, 10, 15, 20, 25, 30, 35, 40)
    for milestone_num, milestone_data in MILESTONE_MESSAGES.items():
        milestone_key = f"milestone_{milestone_num}"
        if completed >= milestone_num and milestone_key not in shown:
            shown.append(milestone_key)
            st.session_state["achievement_shown_milestones"] = shown
            st.session_state["achievement_new_milestone_to_show"] = {
                "num": milestone_num,
                **milestone_data
            }
            return milestone_data

    return None


def update_streak():
    """연속 작성 일수 업데이트"""
    init_achievement_state()

    today = datetime.now().date().isoformat()
    last_date = st.session_state.get("achievement_last_write_date")

    if last_date is None:
        # 첫 작성
        st.session_state["achievement_streak_days"] = 1
        st.session_state["achievement_last_write_date"] = today
    elif last_date == today:
        # 오늘 이미 작성함
        pass
    else:
        last_date_obj = datetime.fromisoformat(last_date).date()
        today_obj = datetime.now().date()
        diff = (today_obj - last_date_obj).days

        if diff == 1:
            # 연속 작성
            st.session_state["achievement_streak_days"] += 1
        elif diff > 1:
            # 연속 끊김
            st.session_state["achievement_streak_days"] = 1

        st.session_state["achievement_last_write_date"] = today


def update_daily_progress():
    """일일 진행 상황 업데이트"""
    init_achievement_state()

    today = datetime.now().date().isoformat()
    last_date = st.session_state.get("achievement_last_write_date")

    if last_date != today:
        # 새로운 날 - 일일 카운터 리셋
        st.session_state["achievement_daily_completed"] = 0
        st.session_state["achievement_daily_goal_achieved"] = False

    # 현재 완료 수와 세션 시작 시 완료 수 비교
    current_completed = get_completed_chapters()
    session_start = st.session_state.get("achievement_session_start_chapters", 0)

    if session_start == 0:
        st.session_state["achievement_session_start_chapters"] = current_completed
        session_start = current_completed

    daily_written = current_completed - session_start + st.session_state.get("achievement_daily_completed", 0)
    daily_goal = st.session_state.get("achievement_daily_goal", 5)

    if daily_written >= daily_goal:
        st.session_state["achievement_daily_goal_achieved"] = True


def get_random_motivation(category="start"):
    """랜덤 동기부여 메시지 반환"""
    messages = MOTIVATION_MESSAGES.get(category, MOTIVATION_MESSAGES["start"])
    message = random.choice(messages)

    if "{days}" in message:
        streak = st.session_state.get("achievement_streak_days", 0)
        message = message.format(days=streak)

    return message


def get_motivation_by_progress():
    """진행률에 따른 동기부여 메시지"""
    percent = get_progress_percent()

    if percent >= 100:
        return get_random_motivation("completed")
    elif percent >= 75:
        return get_random_motivation("progress_almost")
    elif percent >= 50:
        return get_random_motivation("progress_high")
    elif percent >= 25:
        return get_random_motivation("progress_mid")
    else:
        return get_random_motivation("progress_low")


def render_progress_header():
    """상단 진행률 헤더 렌더링"""
    init_achievement_state()

    parsed_toc = st.session_state.get("parsed_toc", [])
    drafts = st.session_state.get("drafts", {})

    if not parsed_toc:
        return

    total = len(parsed_toc)
    completed = len(drafts)
    percent = (completed / total) * 100 if total > 0 else 0
    remaining = total - completed

    # 예상 완료 시간 (장당 약 2분)
    est_minutes = remaining * 2
    if est_minutes < 60:
        est_time = f"약 {int(est_minutes)}분"
    else:
        hours = int(est_minutes // 60)
        mins = int(est_minutes % 60)
        est_time = f"약 {hours}시간 {mins}분"

    # 동기부여 메시지
    motivation = get_motivation_by_progress()

    # 총 글자 수
    total_chars = get_total_chars()

    # 연속 일수
    streak = st.session_state.get("achievement_streak_days", 0)
    streak_text = f"🔥 {streak}일 연속!" if streak > 1 else ""

    st.markdown(f"""
    <div class="achievement-progress-header">
        <div class="progress-main-stats">
            <div class="progress-circle-container">
                <div class="progress-circle" style="--percent: {percent};">
                    <span class="progress-percent">{percent:.0f}%</span>
                </div>
            </div>
            <div class="progress-details">
                <div class="progress-chapters">
                    <span class="big-number">{completed}</span>
                    <span class="separator">/</span>
                    <span class="total-number">{total}</span>
                    <span class="label">장 완료</span>
                </div>
                <div class="progress-chars">
                    📝 {total_chars:,}자 작성
                </div>
                <div class="progress-remaining">
                    ⏱️ 남은 시간: {est_time} ({remaining}장 남음)
                </div>
                {f'<div class="streak-badge">{streak_text}</div>' if streak_text else ''}
            </div>
        </div>
        <div class="motivation-message">
            {motivation}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Streamlit 프로그레스 바
    st.progress(percent / 100)


def render_badge_popup():
    """새 뱃지 획득 팝업"""
    new_badge = st.session_state.get("achievement_new_badge_to_show")

    if new_badge:
        st.markdown(f"""
        <div class="badge-popup-overlay" id="badge-popup">
            <div class="badge-popup">
                <div class="badge-popup-emoji">{new_badge['emoji']}</div>
                <div class="badge-popup-title">새 뱃지 획득!</div>
                <div class="badge-popup-name">{new_badge['name']}</div>
                <div class="badge-popup-desc">{new_badge['description']}</div>
            </div>
        </div>
        <script>
            setTimeout(function() {{
                var popup = document.getElementById('badge-popup');
                if (popup) popup.style.display = 'none';
            }}, 4000);
        </script>
        """, unsafe_allow_html=True)

        # 팝업 표시 후 초기화
        st.session_state["achievement_new_badge_to_show"] = None
        st.balloons()


def render_milestone_popup():
    """마일스톤 축하 팝업"""
    milestone = st.session_state.get("achievement_new_milestone_to_show")

    if milestone:
        is_special = milestone.get("special", False)

        st.markdown(f"""
        <div class="milestone-popup-overlay" id="milestone-popup">
            <div class="milestone-popup {'milestone-special' if is_special else ''}">
                <div class="milestone-emoji">{milestone['emoji']}</div>
                <div class="milestone-title">{milestone['title']}</div>
                <div class="milestone-message">{milestone['message']}</div>
            </div>
        </div>
        <script>
            setTimeout(function() {{
                var popup = document.getElementById('milestone-popup');
                if (popup) popup.style.display = 'none';
            }}, 5000);
        </script>
        """, unsafe_allow_html=True)

        # 팝업 표시 후 초기화
        st.session_state["achievement_new_milestone_to_show"] = None

        if is_special:
            st.balloons()
            st.snow()


def render_badges_display():
    """획득한 뱃지 목록 표시"""
    init_achievement_state()

    earned = st.session_state.get("achievement_earned_badges", [])

    if not earned:
        st.markdown("""
        <div class="badges-container empty">
            <p>아직 획득한 뱃지가 없습니다.</p>
            <p>집필을 진행하시면서 뱃지를 모아보세요! 🎯</p>
        </div>
        """, unsafe_allow_html=True)
        return

    # 뱃지를 티어 순으로 정렬
    earned_badges = [BADGES[bid] for bid in earned if bid in BADGES]
    earned_badges.sort(key=lambda x: x["tier"], reverse=True)

    badges_html = ""
    for badge in earned_badges:
        badges_html += f"""
        <div class="badge-item tier-{badge['tier']}">
            <span class="badge-emoji">{badge['emoji']}</span>
            <span class="badge-name">{badge['name']}</span>
        </div>
        """

    st.markdown(f"""
    <div class="badges-section">
        <h4>🏆 내가 모은 뱃지</h4>
        <div class="badges-container">
            {badges_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_daily_goal_section():
    """오늘의 목표 섹션"""
    init_achievement_state()

    daily_goal = st.session_state.get("achievement_daily_goal", 5)
    daily_completed = st.session_state.get("achievement_daily_completed", 0)
    daily_achieved = st.session_state.get("achievement_daily_goal_achieved", False)
    streak = st.session_state.get("achievement_streak_days", 0)

    # 현재 세션에서 작성한 장 수 계산
    current_completed = get_completed_chapters()
    session_start = st.session_state.get("achievement_session_start_chapters", 0)
    today_written = max(0, current_completed - session_start)

    goal_progress = min(100, (today_written / daily_goal) * 100) if daily_goal > 0 else 0

    status_class = "achieved" if daily_achieved or today_written >= daily_goal else ""

    st.markdown(f"""
    <div class="daily-goal-section {status_class}">
        <div class="daily-goal-header">
            <span class="daily-goal-icon">🎯</span>
            <span class="daily-goal-title">오늘의 목표</span>
            {f'<span class="streak-indicator">🔥 {streak}일 연속</span>' if streak > 1 else ''}
        </div>
        <div class="daily-goal-progress">
            <div class="daily-goal-bar">
                <div class="daily-goal-fill" style="width: {goal_progress}%;"></div>
            </div>
            <div class="daily-goal-text">
                {today_written} / {daily_goal} 장
                {'✅ 달성!' if daily_achieved or today_written >= daily_goal else ''}
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 목표 설정 (사이드바용)
    with st.expander("🎯 목표 설정하기", expanded=False):
        new_goal = st.slider(
            "오늘 목표 장 수",
            min_value=1,
            max_value=20,
            value=daily_goal,
            key="daily_goal_slider"
        )
        if new_goal != daily_goal:
            st.session_state["achievement_daily_goal"] = new_goal
            st.rerun()


def on_chapter_complete():
    """장 완료 시 호출되는 함수"""
    init_achievement_state()

    # 연속 작성 업데이트
    update_streak()

    # 일일 진행 업데이트
    update_daily_progress()

    # 뱃지 체크
    check_and_award_badges()

    # 마일스톤 체크
    check_milestone()


def get_achievement_css():
    """성취 시스템 CSS 스타일 반환"""
    return """
    /* ============================================ */
    /* 성취 시스템 CSS 스타일                        */
    /* ============================================ */

    /* 진행률 헤더 */
    .achievement-progress-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        padding: 1.5rem 2rem;
        margin: 1rem 0 1.5rem 0;
        color: white;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
    }

    .progress-main-stats {
        display: flex;
        align-items: center;
        gap: 2rem;
        flex-wrap: wrap;
    }

    .progress-circle-container {
        flex-shrink: 0;
    }

    .progress-circle {
        width: 100px;
        height: 100px;
        border-radius: 50%;
        background: conic-gradient(
            #4CAF50 calc(var(--percent) * 1%),
            rgba(255,255,255,0.2) calc(var(--percent) * 1%)
        );
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
    }

    .progress-circle::before {
        content: '';
        position: absolute;
        width: 80px;
        height: 80px;
        border-radius: 50%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }

    .progress-percent {
        position: relative;
        z-index: 1;
        font-size: 1.5rem;
        font-weight: bold;
    }

    .progress-details {
        flex: 1;
    }

    .progress-chapters {
        font-size: 1.2rem;
        margin-bottom: 0.5rem;
    }

    .progress-chapters .big-number {
        font-size: 2.5rem;
        font-weight: bold;
    }

    .progress-chapters .separator {
        font-size: 1.5rem;
        margin: 0 0.3rem;
        opacity: 0.7;
    }

    .progress-chapters .total-number {
        font-size: 1.5rem;
        opacity: 0.9;
    }

    .progress-chapters .label {
        font-size: 1rem;
        margin-left: 0.5rem;
        opacity: 0.8;
    }

    .progress-chars, .progress-remaining {
        font-size: 1rem;
        opacity: 0.9;
        margin: 0.3rem 0;
    }

    .streak-badge {
        display: inline-block;
        background: #FF6B6B;
        padding: 0.3rem 0.8rem;
        border-radius: 15px;
        font-size: 0.9rem;
        font-weight: bold;
        margin-top: 0.5rem;
        animation: pulse-glow 2s infinite;
    }

    @keyframes pulse-glow {
        0%, 100% { box-shadow: 0 0 5px rgba(255, 107, 107, 0.5); }
        50% { box-shadow: 0 0 20px rgba(255, 107, 107, 0.8); }
    }

    .motivation-message {
        text-align: center;
        font-size: 1.3rem;
        margin-top: 1rem;
        padding-top: 1rem;
        border-top: 1px solid rgba(255,255,255,0.2);
        font-weight: 500;
    }

    /* 뱃지 팝업 */
    .badge-popup-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.7);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        animation: fadeIn 0.3s ease;
    }

    .badge-popup {
        background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
        border-radius: 30px;
        padding: 3rem;
        text-align: center;
        animation: popIn 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        box-shadow: 0 20px 60px rgba(0,0,0,0.3);
    }

    .badge-popup-emoji {
        font-size: 5rem;
        animation: bounce 0.6s infinite;
    }

    .badge-popup-title {
        font-size: 1.5rem;
        color: #333;
        margin-top: 1rem;
        font-weight: bold;
    }

    .badge-popup-name {
        font-size: 2rem;
        color: #1a1a1a;
        font-weight: bold;
        margin: 0.5rem 0;
    }

    .badge-popup-desc {
        font-size: 1.2rem;
        color: #555;
    }

    /* 마일스톤 팝업 */
    .milestone-popup-overlay {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 10000;
        animation: fadeIn 0.3s ease;
    }

    .milestone-popup {
        background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);
        border-radius: 30px;
        padding: 3rem 4rem;
        text-align: center;
        color: white;
        animation: popIn 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55);
        box-shadow: 0 20px 60px rgba(0,0,0,0.4);
    }

    .milestone-popup.milestone-special {
        background: linear-gradient(135deg, #FFD700 0%, #FF6B6B 50%, #4ECDC4 100%);
        animation: popIn 0.5s cubic-bezier(0.68, -0.55, 0.265, 1.55), rainbow-glow 2s infinite;
    }

    @keyframes rainbow-glow {
        0%, 100% { box-shadow: 0 0 30px rgba(255, 215, 0, 0.8); }
        33% { box-shadow: 0 0 30px rgba(255, 107, 107, 0.8); }
        66% { box-shadow: 0 0 30px rgba(78, 205, 196, 0.8); }
    }

    .milestone-emoji {
        font-size: 6rem;
        animation: celebrate 0.5s ease-in-out 3;
    }

    .milestone-title {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 1rem 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }

    .milestone-message {
        font-size: 1.5rem;
        opacity: 0.95;
    }

    /* 뱃지 표시 섹션 */
    .badges-section {
        background: linear-gradient(135deg, #FFF8E1 0%, #FFECB3 100%);
        border-radius: 20px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 3px solid #FFB300;
    }

    .badges-section h4 {
        margin: 0 0 1rem 0;
        color: #E65100;
        font-size: 1.3rem;
    }

    .badges-container {
        display: flex;
        flex-wrap: wrap;
        gap: 0.8rem;
    }

    .badges-container.empty {
        text-align: center;
        color: #666;
        padding: 1rem;
    }

    .badge-item {
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
        background: white;
        padding: 0.5rem 1rem;
        border-radius: 25px;
        font-size: 1rem;
        font-weight: 600;
        box-shadow: 0 3px 10px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }

    .badge-item:hover {
        transform: scale(1.05);
    }

    .badge-item.tier-1 { border: 2px solid #81C784; }
    .badge-item.tier-2 { border: 2px solid #64B5F6; }
    .badge-item.tier-3 { border: 2px solid #BA68C8; }
    .badge-item.tier-4 { border: 2px solid #FFB74D; }
    .badge-item.tier-5 { border: 2px solid #FF8A65; }
    .badge-item.tier-6 { border: 2px solid #FFD700; background: linear-gradient(135deg, #FFF8E1, #FFD700); }

    .badge-emoji {
        font-size: 1.3rem;
    }

    /* 오늘의 목표 섹션 */
    .daily-goal-section {
        background: linear-gradient(135deg, #E8F5E9 0%, #C8E6C9 100%);
        border-radius: 15px;
        padding: 1.2rem 1.5rem;
        margin: 1rem 0;
        border: 2px solid #81C784;
    }

    .daily-goal-section.achieved {
        background: linear-gradient(135deg, #C8E6C9 0%, #A5D6A7 100%);
        border-color: #4CAF50;
        animation: glow-green 2s infinite;
    }

    @keyframes glow-green {
        0%, 100% { box-shadow: 0 0 10px rgba(76, 175, 80, 0.3); }
        50% { box-shadow: 0 0 25px rgba(76, 175, 80, 0.5); }
    }

    .daily-goal-header {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        margin-bottom: 0.8rem;
    }

    .daily-goal-icon {
        font-size: 1.5rem;
    }

    .daily-goal-title {
        font-size: 1.2rem;
        font-weight: bold;
        color: #2E7D32;
    }

    .streak-indicator {
        margin-left: auto;
        background: #FF6B6B;
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 10px;
        font-size: 0.9rem;
        font-weight: bold;
    }

    .daily-goal-bar {
        background: rgba(255,255,255,0.7);
        border-radius: 10px;
        height: 20px;
        overflow: hidden;
        margin-bottom: 0.5rem;
    }

    .daily-goal-fill {
        background: linear-gradient(90deg, #4CAF50 0%, #8BC34A 100%);
        height: 100%;
        border-radius: 10px;
        transition: width 0.5s ease;
    }

    .daily-goal-text {
        text-align: center;
        font-size: 1.1rem;
        font-weight: 600;
        color: #1B5E20;
    }

    /* 애니메이션 */
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }

    @keyframes popIn {
        from {
            opacity: 0;
            transform: scale(0.5);
        }
        to {
            opacity: 1;
            transform: scale(1);
        }
    }

    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-15px); }
    }

    @keyframes celebrate {
        0%, 100% { transform: scale(1) rotate(0deg); }
        25% { transform: scale(1.2) rotate(-10deg); }
        50% { transform: scale(1.1) rotate(10deg); }
        75% { transform: scale(1.2) rotate(-5deg); }
    }

    /* 모바일 반응형 */
    @media (max-width: 768px) {
        .achievement-progress-header {
            padding: 1rem;
        }

        .progress-main-stats {
            flex-direction: column;
            text-align: center;
        }

        .progress-circle {
            width: 80px;
            height: 80px;
        }

        .progress-circle::before {
            width: 64px;
            height: 64px;
        }

        .progress-percent {
            font-size: 1.2rem;
        }

        .progress-chapters .big-number {
            font-size: 2rem;
        }

        .badge-popup, .milestone-popup {
            margin: 1rem;
            padding: 2rem;
        }

        .badge-popup-emoji, .milestone-emoji {
            font-size: 4rem;
        }
    }
    """

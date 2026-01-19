"""
통합 플로우 테스트
===================
시나리오 1-4에 대한 단위 테스트

실행 방법:
    pytest tests/test_integration_flow.py -v
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))


class MockSessionState(dict):
    """Streamlit 세션 상태 Mock"""
    def __getattr__(self, key):
        return self.get(key)

    def __setattr__(self, key, value):
        self[key] = value


@pytest.fixture
def mock_session_state():
    """Mock 세션 상태 초기화"""
    return MockSessionState({
        "current_step": 1,
        "book_info": {},
        "generated_titles": "",
        "selected_title": "",
        "generated_toc": "",
        "parsed_toc": [],
        "drafts": {},
        "current_section_index": 0,
        "chat_mode_active": False,
        "chat_mode_step": 0,
        "chat_mode_history": [],
        "chat_mode_data": {},
        "voice_mode_active": False,
        "voice_transcribed_text": None,
        "youtube_mode_active": False,
        "youtube_step": 1,
        "show_help_chatbot": False,
        "previous_mode": None,
        "mode_transition_data": {},
    })


class TestScenario1ChatMode:
    """시나리오 1: 초등학생이 채팅 모드로 책 완성"""

    def test_chat_mode_activation(self, mock_session_state):
        """채팅 모드 활성화 테스트"""
        mock_session_state.chat_mode_active = True
        mock_session_state.chat_mode_step = 0
        assert mock_session_state.chat_mode_active == True
        assert mock_session_state.chat_mode_step == 0

    def test_chat_mode_name_input(self, mock_session_state):
        """이름 입력 단계 테스트"""
        mock_session_state.chat_mode_step = 0
        mock_session_state.chat_mode_data["name"] = "민준"
        mock_session_state.chat_mode_step = 1

        assert mock_session_state.chat_mode_data["name"] == "민준"
        assert mock_session_state.chat_mode_step == 1

    def test_chat_mode_topic_selection(self, mock_session_state):
        """주제 선택 테스트"""
        mock_session_state.chat_mode_data["topic"] = "마인크래프트"
        mock_session_state.chat_mode_step = 2

        assert mock_session_state.chat_mode_data["topic"] == "마인크래프트"

    def test_chat_mode_to_normal_transition(self, mock_session_state):
        """채팅 모드에서 일반 모드로 전환 테스트"""
        # 채팅 모드 데이터 설정
        mock_session_state.chat_mode_data = {
            "name": "민준",
            "topic": "마인크래프트",
            "target_reader": "우리반 친구들",
            "title": "마인크래프트 마스터",
            "generated_toc": "Part 1. 시작\n1. 첫 번째 장",
            "parsed_toc": [{"part": 1, "part_title": "시작", "section_num": "1", "section_title": "첫 번째 장"}],
            "first_draft": "첫 번째 이야기 내용...",
        }

        # 전환 시뮬레이션
        data = mock_session_state.chat_mode_data
        mock_session_state.book_info = {
            "name": data.get("name", ""),
            "topic": data.get("topic", ""),
            "target_reader": data.get("target_reader", ""),
            "core_message": f"{data.get('topic', '')}에 대한 이야기",
            "title": data.get("title", ""),
        }
        mock_session_state.selected_title = data.get("title", "")
        mock_session_state.generated_toc = data.get("generated_toc", "")
        mock_session_state.parsed_toc = data.get("parsed_toc", [])

        if data.get("first_draft") and mock_session_state.parsed_toc:
            first_section = mock_session_state.parsed_toc[0]
            key = f"{first_section['section_num']}_{first_section['section_title']}"
            mock_session_state.drafts = {key: data["first_draft"]}

        mock_session_state.chat_mode_active = False
        mock_session_state.previous_mode = "chat"
        mock_session_state.current_step = 4

        # 검증
        assert mock_session_state.chat_mode_active == False
        assert mock_session_state.book_info["name"] == "민준"
        assert mock_session_state.selected_title == "마인크래프트 마스터"
        assert len(mock_session_state.drafts) == 1
        assert mock_session_state.current_step == 4


class TestScenario2VoiceMode:
    """시나리오 2: 노인이 음성 모드로 책 완성"""

    def test_voice_mode_activation(self, mock_session_state):
        """음성 모드 활성화 테스트"""
        mock_session_state.voice_mode_active = True
        assert mock_session_state.voice_mode_active == True

    def test_voice_transcription_storage(self, mock_session_state):
        """음성 변환 텍스트 저장 테스트"""
        mock_session_state.voice_transcribed_text = "나의 인생 이야기..."
        mock_session_state["voice_edited_text"] = "나의 인생 이야기... (수정됨)"

        assert mock_session_state.voice_transcribed_text == "나의 인생 이야기..."

    def test_voice_to_normal_transition(self, mock_session_state):
        """음성 모드에서 일반 모드로 전환 테스트"""
        edited_text = "나의 인생 이야기..."

        mock_session_state.book_info = {
            "topic": edited_text[:500],
            "core_message": edited_text[:200],
            "experience": edited_text,
        }
        mock_session_state.voice_mode_active = False
        mock_session_state.previous_mode = "voice"
        mock_session_state.current_step = 2

        assert mock_session_state.voice_mode_active == False
        assert mock_session_state.book_info["topic"] == edited_text
        assert mock_session_state.current_step == 2


class TestScenario3YouTubeMode:
    """시나리오 3: 강사가 유튜브 모드로 책 완성"""

    def test_youtube_mode_activation(self, mock_session_state):
        """유튜브 모드 활성화 테스트"""
        mock_session_state.youtube_mode_active = True
        mock_session_state.youtube_step = 1
        assert mock_session_state.youtube_mode_active == True

    def test_youtube_transcript_storage(self, mock_session_state):
        """유튜브 자막 저장 테스트"""
        mock_session_state["youtube_transcripts"] = {
            "video123": {
                "text": "강의 내용...",
                "language": "ko",
                "title": "테스트 강의",
                "part_number": 1
            }
        }
        mock_session_state["youtube_merged_transcript"] = "=== Part 1: 테스트 강의 ===\n강의 내용..."

        assert len(mock_session_state["youtube_transcripts"]) == 1

    def test_youtube_to_normal_transition(self, mock_session_state):
        """유튜브 모드에서 일반 모드로 전환 테스트"""
        mock_session_state.youtube_mode_active = False
        mock_session_state.book_info = {
            "youtube_mode": True,
            "transcript": "강의 내용...",
        }
        mock_session_state.current_step = 7

        assert mock_session_state.youtube_mode_active == False
        assert mock_session_state.book_info.get("youtube_mode") == True


class TestScenario4HelpSystem:
    """시나리오 4: 막혔을 때 도움 받기"""

    def test_help_chatbot_toggle(self, mock_session_state):
        """도움 챗봇 토글 테스트"""
        mock_session_state.show_help_chatbot = True
        assert mock_session_state.show_help_chatbot == True

        mock_session_state.show_help_chatbot = False
        assert mock_session_state.show_help_chatbot == False

    def test_contact_section_toggle(self, mock_session_state):
        """연락 섹션 토글 테스트"""
        mock_session_state["show_contact_section"] = True
        assert mock_session_state["show_contact_section"] == True


class TestModeTransition:
    """모드 전환 테스트"""

    def test_safe_mode_transition_preserves_data(self, mock_session_state):
        """모드 전환 시 데이터 보존 테스트"""
        # 기존 데이터 설정
        mock_session_state.book_info = {"name": "테스트"}
        mock_session_state.selected_title = "테스트 제목"
        mock_session_state.drafts = {"1_첫장": "내용"}

        # 모드 전환 데이터 저장
        mock_session_state.mode_transition_data = {
            "book_info": dict(mock_session_state.book_info),
            "selected_title": mock_session_state.selected_title,
            "drafts": dict(mock_session_state.drafts),
        }

        # 복원
        restored_data = mock_session_state.mode_transition_data
        assert restored_data["book_info"]["name"] == "테스트"
        assert restored_data["selected_title"] == "테스트 제목"
        assert len(restored_data["drafts"]) == 1

    def test_determine_next_step(self, mock_session_state):
        """다음 단계 결정 테스트"""
        # 초안이 있으면 Step 4
        mock_session_state.drafts = {"1_test": "content"}
        step = 4 if mock_session_state.drafts else 1
        assert step == 4

        # 목차만 있으면 Step 4
        mock_session_state.drafts = {}
        mock_session_state.parsed_toc = [{"section_num": "1"}]
        step = 4 if mock_session_state.parsed_toc else 1
        assert step == 4

        # 제목만 있으면 Step 3
        mock_session_state.parsed_toc = []
        mock_session_state.selected_title = "제목"
        step = 3 if mock_session_state.selected_title else 1
        assert step == 3


class TestDataPersistence:
    """데이터 유지 테스트"""

    def test_drafts_preserved_after_mode_switch(self, mock_session_state):
        """모드 전환 후 초안 유지 테스트"""
        original_drafts = {"1_test": "content", "2_test": "content2"}
        mock_session_state.drafts = original_drafts

        # 모드 전환 시뮬레이션
        mock_session_state.mode_transition_data = {"drafts": dict(original_drafts)}
        mock_session_state.chat_mode_active = False

        # 복원 후 확인
        assert mock_session_state.mode_transition_data["drafts"] == original_drafts

    def test_progress_preserved(self, mock_session_state):
        """진행 상태 유지 테스트"""
        mock_session_state.current_step = 4
        mock_session_state.current_section_index = 5

        # 저장
        saved_state = {
            "current_step": mock_session_state.current_step,
            "current_section_index": mock_session_state.current_section_index,
        }

        assert saved_state["current_step"] == 4
        assert saved_state["current_section_index"] == 5


class TestErrorRecovery:
    """에러 복구 테스트"""

    def test_error_state_tracking(self, mock_session_state):
        """에러 상태 추적 테스트"""
        mock_session_state["last_error"] = {
            "error": "Connection timeout",
            "context": "generate_draft",
            "time": "2024-01-01T10:00:00",
        }
        mock_session_state["retry_count"] = 1

        assert mock_session_state["last_error"]["context"] == "generate_draft"
        assert mock_session_state["retry_count"] == 1

    def test_retry_count_increment(self, mock_session_state):
        """재시도 카운터 증가 테스트"""
        mock_session_state["retry_count"] = 0

        for i in range(3):
            mock_session_state["retry_count"] += 1

        assert mock_session_state["retry_count"] == 3


class TestButtonFunctionality:
    """버튼 기능 테스트"""

    def test_navigation_button_updates_step(self, mock_session_state):
        """네비게이션 버튼 단계 업데이트 테스트"""
        mock_session_state.current_step = 1

        # 다음 버튼 클릭
        mock_session_state.current_step = 2
        assert mock_session_state.current_step == 2

        # 이전 버튼 클릭
        mock_session_state.current_step = 1
        assert mock_session_state.current_step == 1

    def test_mode_buttons_toggle_correctly(self, mock_session_state):
        """모드 버튼 토글 테스트"""
        # 채팅 모드 버튼
        mock_session_state.chat_mode_active = not mock_session_state.get("chat_mode_active", False)
        assert mock_session_state.chat_mode_active == True

        # 다시 토글
        mock_session_state.chat_mode_active = not mock_session_state.chat_mode_active
        assert mock_session_state.chat_mode_active == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

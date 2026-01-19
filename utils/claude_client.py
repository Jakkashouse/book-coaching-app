"""Claude API 클라이언트 모듈 - 모델 혼합 사용 + 강화된 에러 핸들링"""
import streamlit as st
from anthropic import Anthropic
import time
from functools import wraps


# 모델 설정 (용도별 최적화)
MODELS = {
    "opus": "claude-opus-4-20250514",      # 최고 품질 (제목, 목차, 탈고)
    "sonnet": "claude-sonnet-4-20250514",  # 고품질 (대화, 피드백)
    "haiku": "claude-3-5-haiku-20241022",  # 비용 절감 (초안 생성)
}

# 에러 메시지 (친근한 한국어)
ERROR_MESSAGES = {
    "api_key": """
**API 키가 설정되지 않았어요!**

선생님께 "API 키 설정이 필요해요"라고 말씀해 주세요!
(기술 정보: Streamlit Secrets에 ANTHROPIC_API_KEY를 추가해야 합니다)
""",
    "network": """
**인터넷 연결이 끊긴 것 같아요!**

이렇게 해봐:
1. 와이파이나 인터넷 연결 확인하기
2. 잠깐 기다렸다가 다시 시도하기
""",
    "rate_limit": """
**너무 많은 요청을 보냈어요!**

1분만 쉬었다가 다시 해볼까요?
(다른 사람들도 AI를 많이 사용하고 있어요)
""",
    "timeout": """
**응답이 너무 오래 걸려요!**

AI가 바쁜가 봐요. 30초 후에 다시 시도해볼까요?
""",
    "server": """
**AI 서버에 문제가 생겼어요!**

이건 우리 잘못이 아니에요! 잠깐 기다렸다가 다시 해봐요.
""",
    "invalid_request": """
**요청에 문제가 있어요!**

입력 내용을 확인해보고 다시 시도해주세요.
""",
    "content_policy": """
**입력 내용을 확인해주세요!**

AI가 처리하기 어려운 내용이 있을 수 있어요.
다른 방식으로 표현해보는 건 어떨까요?
""",
    "unknown": """
**앗! 뭔가 문제가 생겼어요!**

걱정하지 마세요! 이렇게 해봐:
1. 30초 기다렸다가 다시 시도하기
2. 페이지를 새로고침해보기
3. 문제가 계속되면 선생님께 말씀해주세요!
"""
}

# 재시도 설정
MAX_RETRIES = 3
RETRY_DELAY = 2  # 초


def classify_error(error: Exception) -> str:
    """에러 유형을 분류하여 적절한 메시지 키 반환"""
    error_str = str(error).lower()

    # 네트워크 관련 에러
    if any(keyword in error_str for keyword in ['connection', 'network', 'unreachable', 'dns', 'socket']):
        return "network"

    # 타임아웃
    if any(keyword in error_str for keyword in ['timeout', 'timed out', 'time out']):
        return "timeout"

    # Rate limit
    if any(keyword in error_str for keyword in ['rate limit', 'rate_limit', '429', 'too many requests']):
        return "rate_limit"

    # 서버 에러
    if any(keyword in error_str for keyword in ['500', '502', '503', '504', 'server error', 'internal error']):
        return "server"

    # 잘못된 요청
    if any(keyword in error_str for keyword in ['400', 'bad request', 'invalid']):
        return "invalid_request"

    # 콘텐츠 정책
    if any(keyword in error_str for keyword in ['content policy', 'blocked', 'moderation']):
        return "content_policy"

    # API 키 관련
    if any(keyword in error_str for keyword in ['401', 'unauthorized', 'authentication', 'api key', 'forbidden', '403']):
        return "api_key"

    return "unknown"


def with_retry(max_retries: int = MAX_RETRIES, delay: float = RETRY_DELAY):
    """API 호출 재시도 데코레이터"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    error_type = classify_error(e)

                    # 재시도가 의미 없는 에러는 바로 반환
                    if error_type in ["api_key", "invalid_request", "content_policy"]:
                        raise e

                    # 마지막 시도가 아니면 대기 후 재시도
                    if attempt < max_retries - 1:
                        wait_time = delay * (attempt + 1)  # 점진적 대기
                        time.sleep(wait_time)
                        continue
                    else:
                        raise e

            raise last_error
        return wrapper
    return decorator


def get_client():
    """Anthropic 클라이언트 인스턴스 반환"""
    try:
        api_key = st.secrets.get("ANTHROPIC_API_KEY")
        if not api_key or api_key == "여기에_API_키_입력":
            st.error(ERROR_MESSAGES["api_key"])
            return None
        return Anthropic(api_key=api_key)
    except Exception as e:
        st.error(ERROR_MESSAGES["api_key"])
        return None


def show_error_with_retry(error_type: str, show_retry_button: bool = True, key: str = None):
    """에러 메시지와 재시도 버튼 표시"""
    st.error(ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown"]))

    if show_retry_button and key:
        if st.button("🔄 다시 시도하기", key=f"retry_{key}"):
            st.rerun()


@with_retry()
def generate_response(prompt: str, system_prompt: str = None, max_tokens: int = 4096, model_type: str = "sonnet") -> str:
    """
    Claude API를 통해 응답 생성

    Args:
        prompt: 사용자 프롬프트
        system_prompt: 시스템 프롬프트 (선택)
        max_tokens: 최대 토큰 수
        model_type: 모델 타입 ("opus", "sonnet", "haiku")

    Returns:
        생성된 응답 텍스트
    """
    # 입력 검증 - 타입 체크 추가
    if not prompt or not isinstance(prompt, str) or not prompt.strip():
        st.warning("입력 내용이 비어있어요. 무엇을 도와드릴까요?")
        return None

    # 너무 긴 입력 처리
    MAX_INPUT_LENGTH = 100000  # 약 100K 문자
    if len(prompt) > MAX_INPUT_LENGTH:
        st.warning(f"입력이 너무 길어요! {MAX_INPUT_LENGTH:,}자 이내로 줄여주세요. (현재: {len(prompt):,}자)")
        prompt = prompt[:MAX_INPUT_LENGTH]

    client = get_client()
    # 클라이언트 None 체크 추가
    if client is None:
        return None

    messages = [{"role": "user", "content": prompt}]

    try:
        kwargs = {
            "model": MODELS.get(model_type, MODELS["sonnet"]),
            "max_tokens": max_tokens,
            "messages": messages,
        }

        if system_prompt and isinstance(system_prompt, str):
            kwargs["system"] = system_prompt

        response = client.messages.create(**kwargs)

        # 응답 검증 강화
        if not response or not response.content:
            st.warning("AI가 빈 응답을 보냈어요. 다시 시도해주세요.")
            return None

        if len(response.content) == 0:
            st.warning("AI가 빈 응답을 보냈어요. 다시 시도해주세요.")
            return None

        return response.content[0].text

    except Exception as e:
        error_type = classify_error(e)
        st.error(ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown"]))

        # 디버깅용 상세 정보 (개발자용) - 에러 메시지 길이 제한
        with st.expander("기술 정보 (선생님께 보여주세요)", expanded=False):
            st.code(f"에러 유형: {error_type}\n에러 내용: {str(e)[:500]}")

        return None


# ============================================================
# 🔴 OPUS 사용 (최고 품질) - 제목, 목차, 탈고, 기획서
# ============================================================

def generate_titles(book_info: dict) -> str:
    """제목 10개 생성 [OPUS]"""
    # 입력 검증
    if not book_info:
        st.warning("책 정보가 없어요. 1단계에서 정보를 입력해주세요.")
        return None

    required_fields = ["topic", "target_reader", "core_message"]
    missing_fields = [f for f in required_fields if not book_info.get(f)]
    if missing_fields:
        st.warning(f"다음 정보가 필요해요: {', '.join(missing_fields)}")
        return None

    try:
        from prompts.templates import get_title_generation_prompt
        prompt = get_title_generation_prompt(book_info)
        system = "당신은 20년 경력의 베스트셀러 편집자입니다. 독자의 마음을 사로잡는 제목을 만드는 전문가입니다."
        return generate_response(prompt, system, model_type="opus")
    except ImportError as e:
        st.error("템플릿 파일을 찾을 수 없어요. 선생님께 말씀해주세요!")
        return None
    except Exception as e:
        error_type = classify_error(e)
        st.error(ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown"]))
        return None


def generate_toc(book_info: dict) -> str:
    """목차 40꼭지 생성 [OPUS]"""
    # 입력 검증
    if not book_info:
        st.warning("책 정보가 없어요. 1단계에서 정보를 입력해주세요.")
        return None

    try:
        from prompts.templates import get_toc_generation_prompt
        prompt = get_toc_generation_prompt(book_info)
        system = "당신은 50권 이상 편집한 베테랑 출판 편집자입니다. 논리적이고 매력적인 책 구조를 설계하는 전문가입니다."
        return generate_response(prompt, system, model_type="opus")
    except ImportError as e:
        st.error("템플릿 파일을 찾을 수 없어요. 선생님께 말씀해주세요!")
        return None
    except Exception as e:
        error_type = classify_error(e)
        st.error(ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown"]))
        return None


def refine_text(text: str) -> str:
    """문장 다듬기/탈고 [OPUS]"""
    # 입력 검증
    if not text or not text.strip():
        st.warning("다듬을 텍스트가 비어있어요.")
        return None

    if len(text) < 10:
        st.warning("텍스트가 너무 짧아요. 조금 더 작성해주세요.")
        return None

    try:
        from prompts.templates import get_refine_prompt
        prompt = get_refine_prompt(text)
        system = "당신은 교열 전문 편집자입니다. 글을 더 자연스럽고 읽기 쉽게 다듬습니다."
        return generate_response(prompt, system, model_type="opus")
    except ImportError as e:
        st.error("템플릿 파일을 찾을 수 없어요. 선생님께 말씀해주세요!")
        return None
    except Exception as e:
        error_type = classify_error(e)
        st.error(ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown"]))
        return None


def edit_draft_with_instruction(draft: str, instruction: str) -> str:
    """사용자 지시에 따라 초안 수정 [OPUS]"""
    # 입력 검증
    if not draft or not draft.strip():
        st.warning("수정할 초안이 비어있어요.")
        return None

    if not instruction or not instruction.strip():
        st.warning("수정 지시사항을 입력해주세요.")
        return None

    if len(instruction) > 5000:
        st.warning("수정 지시사항이 너무 길어요. 5000자 이내로 줄여주세요.")
        instruction = instruction[:5000]

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
    return generate_response(prompt, system, model_type="opus")


def generate_proposal(book_info: dict, author_info: dict) -> str:
    """출간기획서 생성 [OPUS]"""
    # 입력 검증
    if not book_info:
        st.warning("책 정보가 없어요. 1단계에서 정보를 입력해주세요.")
        return None

    if not author_info:
        st.warning("저자 정보가 없어요. 저자 정보를 먼저 입력해주세요.")
        return None

    try:
        from prompts.templates import get_proposal_generation_prompt
        prompt = get_proposal_generation_prompt(book_info, author_info)
        system = "당신은 대형 출판사 기획 편집자입니다. 답장률 85%의 기획서를 작성합니다."
        return generate_response(prompt, system, model_type="opus")
    except ImportError as e:
        st.error("템플릿 파일을 찾을 수 없어요. 선생님께 말씀해주세요!")
        return None
    except Exception as e:
        error_type = classify_error(e)
        st.error(ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown"]))
        return None


def generate_landing_page(book_info: dict, webinar_info: dict) -> str:
    """랜딩페이지 카피 생성 [OPUS]"""
    # 입력 검증
    if not book_info:
        st.warning("책 정보가 없어요. 1단계에서 정보를 입력해주세요.")
        return None

    if not webinar_info:
        st.warning("웨비나 정보가 없어요. 웨비나 정보를 먼저 입력해주세요.")
        return None

    try:
        from prompts.templates import get_landing_page_prompt
        prompt = get_landing_page_prompt(book_info, webinar_info)
        system = "당신은 전환율 30% 이상의 랜딩페이지 전문 카피라이터입니다."
        return generate_response(prompt, system, model_type="opus")
    except ImportError as e:
        st.error("템플릿 파일을 찾을 수 없어요. 선생님께 말씀해주세요!")
        return None
    except Exception as e:
        error_type = classify_error(e)
        st.error(ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown"]))
        return None


# ============================================================
# 🟢 HAIKU 사용 (비용 절감) - 초안 생성
# ============================================================

def generate_draft(book_info: dict, section_info: dict) -> str:
    """꼭지별 초안 생성 2000자 [HAIKU - 비용 절감]"""
    # 입력 검증
    if not book_info:
        st.warning("책 정보가 없어요.")
        return None

    if not section_info:
        st.warning("섹션 정보가 없어요.")
        return None

    try:
        from prompts.templates import get_draft_generation_prompt
        prompt = get_draft_generation_prompt(book_info, section_info)
        system = "당신은 베스트셀러 작가의 고스트라이터입니다. 독자가 술술 읽히는 글을 씁니다."
        return generate_response(prompt, system, model_type="haiku")
    except ImportError as e:
        st.error("템플릿 파일을 찾을 수 없어요. 선생님께 말씀해주세요!")
        return None
    except Exception as e:
        error_type = classify_error(e)
        st.error(ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown"]))
        return None


def add_storytelling(experience: str) -> str:
    """스토리텔링 추가 [HAIKU - 비용 절감]"""
    # 입력 검증
    if not experience or not experience.strip():
        st.warning("스토리텔링할 경험을 입력해주세요.")
        return None

    if len(experience) < 20:
        st.warning("경험 내용이 너무 짧아요. 조금 더 자세히 적어주세요.")
        return None

    try:
        from prompts.templates import get_storytelling_prompt
        prompt = get_storytelling_prompt(experience)
        system = "당신은 스토리텔링 전문 작가입니다. 밋밋한 경험을 감동적인 이야기로 바꿉니다."
        return generate_response(prompt, system, model_type="haiku")
    except ImportError as e:
        st.error("템플릿 파일을 찾을 수 없어요. 선생님께 말씀해주세요!")
        return None
    except Exception as e:
        error_type = classify_error(e)
        st.error(ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown"]))
        return None


# ============================================================
# 🟡 SONNET 사용 (균형) - 대화, 피드백
# ============================================================

def get_feedback(content: str, feedback_type: str) -> str:
    """피드백 생성 (제목/목차/원고) [SONNET]"""
    # 입력 검증
    if not content or not content.strip():
        st.warning("피드백할 내용이 비어있어요.")
        return None

    valid_types = ["title", "toc", "draft", "제목", "목차", "원고"]
    if feedback_type not in valid_types:
        st.warning(f"알 수 없는 피드백 유형이에요: {feedback_type}")
        return None

    try:
        from prompts.templates import get_feedback_prompt
        prompt = get_feedback_prompt(content, feedback_type)
        system = "당신은 20년 경력의 출판 편집자입니다. 건설적이고 구체적인 피드백을 제공합니다."
        return generate_response(prompt, system, model_type="sonnet")
    except ImportError as e:
        st.error("템플릿 파일을 찾을 수 없어요. 선생님께 말씀해주세요!")
        return None
    except Exception as e:
        error_type = classify_error(e)
        st.error(ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown"]))
        return None


def chat_with_coach(messages: list, book_info: dict = None, elementary_friendly: bool = False) -> str:
    """책쓰기 코치와 대화 [SONNET]

    Args:
        messages: 대화 메시지 리스트
        book_info: 책 정보 딕셔너리
        elementary_friendly: True면 초등학생도 이해할 수 있게 쉽게 답변
    """
    # 입력 검증
    if not messages:
        if not elementary_friendly:
            st.warning("대화 메시지가 비어있어요.")
        return None

    # 메시지 길이 검증
    total_length = sum(len(str(m.get('content', ''))) for m in messages)
    MAX_CONVERSATION_LENGTH = 50000
    if total_length > MAX_CONVERSATION_LENGTH:
        # 오래된 메시지 제거
        while total_length > MAX_CONVERSATION_LENGTH and len(messages) > 2:
            removed = messages.pop(0)
            total_length -= len(str(removed.get('content', '')))

    client = get_client()
    # 클라이언트 None 체크 추가
    if client is None:
        return None

    if elementary_friendly:
        # 초등학생 친화적 시스템 프롬프트
        system = """당신은 친절한 책쓰기 도우미예요.
초등학생도 이해할 수 있게 쉽게 설명해주세요.

답변 규칙:
1. 어려운 단어 대신 쉬운 단어 사용하기
2. 예시를 많이 들어주기
3. 격려 메시지 꼭 포함하기 (예: "잘 하고 있어요!", "할 수 있어요!")
4. 이모지를 적절히 사용해서 친근하게
5. 2-4문장으로 간결하게 답변하기
6. "~해요", "~예요" 같은 친근한 말투 사용하기

금지 사항:
- 어려운 전문 용어 사용하지 않기
- 너무 긴 설명 하지 않기
- 비판적이거나 부정적인 표현 하지 않기"""
    else:
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
            model=MODELS["sonnet"],
            max_tokens=1024 if elementary_friendly else 2048,
            system=system,
            messages=messages,
        )

        if not response or not response.content:
            if not elementary_friendly:
                st.warning("AI가 응답하지 않았어요. 다시 시도해주세요.")
            return None

        return response.content[0].text

    except Exception as e:
        error_type = classify_error(e)
        if not elementary_friendly:
            st.error(ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown"]))
        return None


# ============================================================
# 유튜브 모드 전용 함수들
# ============================================================

def analyze_youtube_transcript(transcript: str, video_title: str = "") -> str:
    """유튜브 자막 분석 및 핵심 내용 추출 [SONNET]"""
    # 입력 검증
    if not transcript or not transcript.strip():
        st.warning("분석할 자막이 비어있어요.")
        return None

    if len(transcript) < 100:
        st.warning("자막이 너무 짧아요. 더 긴 영상을 선택해주세요.")
        return None

    # 자막이 너무 길면 잘라내기
    MAX_TRANSCRIPT_LENGTH = 15000
    if len(transcript) > MAX_TRANSCRIPT_LENGTH:
        transcript = transcript[:MAX_TRANSCRIPT_LENGTH]

    prompt = f"""다음은 유튜브 영상의 자막입니다.

## 영상 제목: {video_title}

## 자막 내용:
{transcript[:8000]}

## 분석 요청:
1. **핵심 주제**: 이 영상이 다루는 핵심 주제 (1-2문장)
2. **주요 내용**: 영상에서 다루는 주요 포인트 5-7개 (불릿 포인트)
3. **타겟 독자**: 이 내용을 책으로 만들면 누가 읽으면 좋을지
4. **핵심 메시지**: 한 문장으로 요약된 핵심 메시지
5. **책 제목 제안**: 이 내용으로 책을 만들 때 어울리는 제목 3개

마크다운 형식으로 깔끔하게 정리해주세요."""

    system = "당신은 콘텐츠 분석 전문가입니다. 영상 내용을 책으로 만들기 위한 인사이트를 제공합니다."
    return generate_response(prompt, system, max_tokens=2048, model_type="sonnet")


def generate_titles_from_transcript(transcript: str, video_info: dict) -> str:
    """유튜브 자막 기반 제목 생성 [OPUS]"""
    # 입력 검증
    if not transcript or not transcript.strip():
        st.warning("자막이 비어있어요.")
        return None

    if not video_info:
        st.warning("영상 정보가 없어요.")
        return None

    try:
        from prompts.templates import TITLE_FORMULAS
    except ImportError:
        TITLE_FORMULAS = ""

    prompt = f"""유튜브 영상 정보:
- 제목: {video_info.get('title', '')}
- 채널: {video_info.get('channel', '')}

자막 내용 요약:
{transcript[:6000]}

{TITLE_FORMULAS}

위 제목 공식 10가지를 각각 적용해서 이 영상 내용으로 책 제목 10개를 만들어주세요.

각 제목에 대해:
1. 적용한 공식 번호와 이름
2. 제목
3. 이 제목의 장점 (한 줄)
4. 부제목 제안 (선택)

형식으로 출력해주세요. 마크다운 형식으로 깔끔하게 정리해주세요."""

    system = "당신은 20년 경력의 베스트셀러 편집자입니다. 유튜브 콘텐츠를 매력적인 책 제목으로 변환하는 전문가입니다."
    return generate_response(prompt, system, model_type="opus")


def generate_toc_from_transcript(transcript: str, book_info: dict, video_count: int = 1) -> str:
    """유튜브 자막 기반 목차 생성 [OPUS]"""
    # 입력 검증
    if not transcript or not transcript.strip():
        st.warning("자막이 비어있어요.")
        return None

    if not book_info:
        st.warning("책 정보가 없어요.")
        return None

    if video_count > 1:
        structure_guide = f"""
## 구조 안내:
- 총 {video_count}개 영상의 내용이 포함되어 있습니다
- 각 영상을 하나의 Part로 구성하되, 논리적으로 재배열해도 됩니다
- 5부 40꼭지 구조로 통합하세요
"""
    else:
        structure_guide = """
## 구조 안내:
- 5부 40꼭지 구조로 만들어주세요
- 각 Part는 8개 꼭지
"""

    prompt = f"""내 책 정보:
- 제목: {book_info.get('title', '')}
- 타겟 독자: {book_info.get('target_reader', '')}
- 핵심 메시지: {book_info.get('core_message', '')}

## 유튜브 영상 자막 내용:
{transcript[:10000]}

{structure_guide}

## 5부 구조 설명:
- Part 1. WHY (왜?): 문제 인식 & 동기 부여 - 독자가 "이 책 꼭 읽어야겠다"고 느끼게
- Part 2. WHAT (무엇?): 핵심 개념 & 원리 - 기본 개념을 완벽히 이해하게
- Part 3. HOW (어떻게?): 구체적 방법론 - "나도 할 수 있겠다"는 자신감
- Part 4. DO (실행): 실전 적용 & 사례 - 실제로 따라하며 결과물
- Part 5. FUTURE (미래): 비전 & 다음 단계 - 책을 덮어도 행동하게

## 요구사항:
1. 각 Part는 8개 꼭지
2. 총 40개 꼭지
3. 각 꼭지는 문장형 제목 (호기심 유발)
4. 영상 내용을 충실히 반영
5. 논리적 흐름 유지
6. 독자가 읽고 싶어지는 제목

## 출력 형식:
```
Part 1. [Part 제목] - WHY (왜?)
  1-1. [꼭지 제목]
  1-2. [꼭지 제목]
  ...

Part 2. [Part 제목] - WHAT (무엇?)
  2-1. [꼭지 제목]
  ...
```"""

    system = "당신은 50권 이상 편집한 베테랑 출판 편집자입니다. 유튜브 콘텐츠를 체계적인 책 구조로 변환하는 전문가입니다."
    return generate_response(prompt, system, model_type="opus")


def generate_draft_from_transcript(book_info: dict, section_info: dict, transcript_chunk: str) -> str:
    """유튜브 자막 기반 초안 생성 [HAIKU - 비용 절감]"""
    # 입력 검증
    if not book_info:
        st.warning("책 정보가 없어요.")
        return None

    if not section_info:
        st.warning("섹션 정보가 없어요.")
        return None

    if not transcript_chunk:
        st.warning("자막 내용이 없어요.")
        return None

    # 꼭지 제목에서 키워드 추출하여 관련 자막 부분 찾기
    section_title = section_info.get('section_title', '')
    relevant_chunk = find_relevant_transcript_chunk(transcript_chunk, section_title)

    prompt = f"""내 책 정보:
- 제목: {book_info.get('title', '')}
- 타겟 독자: {book_info.get('target_reader', '')}
- 이 책의 톤: {book_info.get('tone', '친근한')}

지금 쓸 꼭지:
- Part {section_info.get('part_number', '')}: {section_info.get('part_title', '')}
- 꼭지 번호: {section_info.get('section_number', '')}
- 꼭지 제목: {section_info.get('section_title', '')}

## 참고할 유튜브 자막 내용:
{relevant_chunk[:4000]}

## 요구사항:
1. 분량: 2000자 (공백 포함)
2. 자막 내용을 바탕으로 하되, 책다운 문체로 재구성
3. **구어체 → 문어체 변환 규칙**:
   - "~거든요" → "~기 때문입니다"
   - "~잖아요" → "~입니다"
   - "그래가지고" → "그래서"
   - "진짜", "막" → 삭제 또는 적절한 표현으로
   - "~해보니까" → "~해본 결과"
   - "어 그러니까" 등 말 더듬기 → 삭제
4. 구조:
   - 도입 (호기심 유발, 약 300자)
   - 본론 (핵심 내용 3가지, 각 약 400자)
   - 사례/데이터 (설득력, 약 400자)
   - 마무리 (행동 유도, 약 300자)
5. 문장은 짧게 (한 문장 40자 이내)
6. 한 문단은 3-4문장
7. 중간중간 소제목 사용
8. 독자에게 말하듯 (~하세요, ~입니다)

바로 글을 작성해주세요."""

    system = "당신은 베스트셀러 작가의 고스트라이터입니다. 유튜브 콘텐츠를 책다운 글로 변환하는 전문가입니다. 구어체를 자연스러운 문어체로 바꾸는 데 능숙합니다."
    return generate_response(prompt, system, model_type="haiku")


def find_relevant_transcript_chunk(transcript: str, section_title: str, chunk_size: int = 4000) -> str:
    """
    섹션 제목과 관련된 자막 부분을 찾아 반환

    Args:
        transcript: 전체 자막
        section_title: 꼭지 제목
        chunk_size: 반환할 청크 크기

    Returns:
        관련 자막 부분
    """
    if not transcript or not section_title:
        return transcript[:chunk_size] if transcript else ""

    # 제목에서 핵심 키워드 추출 (2글자 이상 단어)
    import re
    keywords = [word for word in re.findall(r'[가-힣a-zA-Z]{2,}', section_title)]

    if not keywords:
        return transcript[:chunk_size]

    # 각 키워드가 등장하는 위치 찾기
    positions = []
    for keyword in keywords[:3]:  # 상위 3개 키워드만 사용
        for match in re.finditer(re.escape(keyword), transcript, re.IGNORECASE):
            positions.append(match.start())

    if not positions:
        # 키워드를 찾지 못하면 전체 자막을 균등하게 분할
        return transcript[:chunk_size]

    # 가장 많은 키워드가 밀집된 구간 찾기
    avg_position = sum(positions) // len(positions)

    # 해당 위치 중심으로 청크 추출
    start = max(0, avg_position - chunk_size // 2)
    end = min(len(transcript), start + chunk_size)

    # 문장 단위로 자르기 (마침표 기준)
    chunk = transcript[start:end]

    # 시작 부분 정리 (문장 중간에서 시작하지 않도록)
    if start > 0:
        first_period = chunk.find('. ')
        if first_period != -1 and first_period < 100:
            chunk = chunk[first_period + 2:]

    return chunk

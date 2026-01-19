"""유튜브 영상 처리 모듈 - 강화된 에러 핸들링"""
import re
from typing import Optional, Dict, List, Tuple
import time


# 에러 메시지 (친근한 한국어)
ERROR_MESSAGES = {
    "invalid_url": """
**유튜브 URL이 아닌 것 같아요!**

youtube.com 또는 youtu.be 링크를 입력해주세요.
예시: https://www.youtube.com/watch?v=xxxxx
""",
    "empty_url": """
**URL을 입력해주세요!**

유튜브 영상 링크를 붙여넣어 주세요.
""",
    "network": """
**인터넷 연결이 끊어진 것 같아요!**

이렇게 해봐:
1. 와이파이나 인터넷 연결 확인하기
2. 잠깐 기다렸다가 다시 시도하기
""",
    "timeout": """
**응답이 너무 오래 걸려요!**

영상 정보를 가져오는 데 시간이 오래 걸려요.
잠깐 기다렸다가 다시 시도해볼까요?
""",
    "private": """
**비공개 영상이에요!**

공개 영상만 처리할 수 있어요.
다른 영상을 선택해주세요.
""",
    "unavailable": """
**이 영상을 사용할 수 없어요!**

삭제되었거나 지역 제한이 있는 영상일 수 있어요.
다른 영상을 선택해주세요.
""",
    "age_restricted": """
**연령 제한 영상이에요!**

연령 제한 영상은 처리할 수 없어요.
다른 영상을 선택해주세요.
""",
    "no_transcript": """
**자막이 없는 영상이에요!**

자막이 있는 영상을 선택하거나,
음성 변환(STT) 기능을 사용해보세요.
""",
    "library_missing": """
**필요한 라이브러리가 설치되지 않았어요!**

선생님께 "라이브러리 설치가 필요해요"라고 말씀해주세요.
""",
    "unknown": """
**앗! 뭔가 문제가 생겼어요!**

잠깐 기다렸다가 다시 시도해볼까요?
문제가 계속되면 선생님께 말씀해주세요!
"""
}

# 재시도 설정
MAX_RETRIES = 2
RETRY_DELAY = 1


def classify_youtube_error(error: Exception) -> str:
    """유튜브 관련 에러 유형 분류"""
    error_str = str(error).lower()

    if any(keyword in error_str for keyword in ['connection', 'network', 'unreachable', 'dns', 'socket']):
        return "network"

    if any(keyword in error_str for keyword in ['timeout', 'timed out']):
        return "timeout"

    if any(keyword in error_str for keyword in ['private', 'sign in']):
        return "private"

    if any(keyword in error_str for keyword in ['unavailable', 'removed', 'deleted', 'not found', '404']):
        return "unavailable"

    if any(keyword in error_str for keyword in ['age', 'restricted', 'confirm your age']):
        return "age_restricted"

    if any(keyword in error_str for keyword in ['no transcript', 'transcript', 'caption', 'subtitle']):
        return "no_transcript"

    if any(keyword in error_str for keyword in ['import', 'module', 'no module']):
        return "library_missing"

    return "unknown"


def extract_video_id(url: str) -> Optional[str]:
    """
    유튜브 URL에서 비디오 ID 추출

    지원 형식:
    - https://www.youtube.com/watch?v=xxxxx
    - https://youtu.be/xxxxx
    - https://www.youtube.com/embed/xxxxx
    - https://www.youtube.com/shorts/xxxxx
    - https://m.youtube.com/watch?v=xxxxx (모바일)
    - URL 파라미터 (&list=, &t= 등) 포함된 경우도 처리
    """
    # 입력 검증
    if not url:
        return None

    if not isinstance(url, str):
        return None

    # URL 정규화 (공백 제거)
    url = url.strip()

    if not url:
        return None

    patterns = [
        # 표준 watch URL (www, m 포함, 추가 파라미터 허용)
        r'(?:https?://)?(?:www\.|m\.)?youtube\.com/watch\?(?:.*&)?v=([a-zA-Z0-9_-]{11})',
        # 단축 URL
        r'(?:https?://)?youtu\.be/([a-zA-Z0-9_-]{11})',
        # 임베드 URL
        r'(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        # Shorts URL
        r'(?:https?://)?(?:www\.|m\.)?youtube\.com/shorts/([a-zA-Z0-9_-]{11})',
        # YouTube Music
        r'(?:https?://)?music\.youtube\.com/watch\?(?:.*&)?v=([a-zA-Z0-9_-]{11})',
        # 라이브 URL
        r'(?:https?://)?(?:www\.)?youtube\.com/live/([a-zA-Z0-9_-]{11})',
    ]

    for pattern in patterns:
        try:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        except Exception:
            continue

    return None


def validate_youtube_url(url: str) -> Tuple[bool, str]:
    """
    유튜브 URL 유효성 검사

    Returns:
        Tuple of (is_valid, message/video_id)
    """
    # 입력 검증
    if not url:
        return False, ERROR_MESSAGES["empty_url"]

    if not isinstance(url, str):
        return False, ERROR_MESSAGES["invalid_url"]

    url = url.strip()

    if not url:
        return False, ERROR_MESSAGES["empty_url"]

    # 기본 URL 형식 확인
    try:
        url_lower = url.lower()
        if not any(domain in url_lower for domain in ['youtube.com', 'youtu.be', 'music.youtube.com']):
            return False, ERROR_MESSAGES["invalid_url"]
    except Exception:
        return False, ERROR_MESSAGES["invalid_url"]

    video_id = extract_video_id(url)
    if not video_id:
        return False, "유효한 비디오 ID를 찾을 수 없습니다. URL 형식을 확인해주세요."

    return True, video_id


def get_video_info(url: str, timeout: int = 30) -> Optional[Dict]:
    """
    yt-dlp를 사용하여 유튜브 영상 정보 가져오기

    Args:
        url: 유튜브 URL
        timeout: 타임아웃 (초, 기본 30초)

    Returns:
        Dict with keys: title, description, thumbnail, duration, view_count, channel, upload_date
        또는 {'error': '에러메시지'} 형태로 에러 반환
    """
    # URL 유효성 검사
    is_valid, result = validate_youtube_url(url)
    if not is_valid:
        return {'error': result}

    last_error = None

    for attempt in range(MAX_RETRIES):
        try:
            from yt_dlp import YoutubeDL
            from yt_dlp.utils import DownloadError, ExtractorError

            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'socket_timeout': timeout,
                'retries': 3,  # 재시도 횟수
                'ignoreerrors': False,
            }

            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                if info:
                    # 시간 포맷팅
                    try:
                        duration_seconds = info.get('duration', 0) or 0
                        hours = duration_seconds // 3600
                        minutes = (duration_seconds % 3600) // 60
                        seconds = duration_seconds % 60

                        if hours > 0:
                            duration_str = f"{hours}시간 {minutes}분 {seconds}초"
                        elif minutes > 0:
                            duration_str = f"{minutes}분 {seconds}초"
                        else:
                            duration_str = f"{seconds}초"
                    except Exception:
                        duration_str = "알 수 없음"
                        duration_seconds = 0

                    # 썸네일 URL 최적화 (고화질 우선)
                    thumbnail = info.get('thumbnail', '')
                    try:
                        thumbnails = info.get('thumbnails', [])
                        if thumbnails:
                            # 고화질 썸네일 선택 (maxresdefault 우선)
                            for thumb in reversed(thumbnails):
                                if thumb.get('url'):
                                    thumbnail = thumb['url']
                                    break
                    except Exception:
                        pass  # 썸네일 처리 실패는 무시

                    return {
                        'video_id': info.get('id', ''),
                        'title': info.get('title', '제목 없음'),
                        'description': info.get('description', '')[:500] if info.get('description') else '',
                        'thumbnail': thumbnail,
                        'duration': duration_seconds,
                        'duration_str': duration_str,
                        'view_count': info.get('view_count', 0) or 0,
                        'view_count_str': format_view_count(info.get('view_count', 0) or 0),
                        'channel': info.get('channel', info.get('uploader', '알 수 없음')),
                        'upload_date': format_upload_date(info.get('upload_date', '')),
                        'url': url,
                        'has_captions': bool(info.get('subtitles') or info.get('automatic_captions')),
                    }

        except ImportError:
            return {'error': ERROR_MESSAGES["library_missing"]}

        except Exception as e:
            last_error = e
            error_type = classify_youtube_error(e)

            # 재시도가 의미 없는 에러는 바로 반환
            if error_type in ["private", "unavailable", "age_restricted", "library_missing"]:
                return {'error': ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown"])}

            # 마지막 시도가 아니면 대기 후 재시도
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue

    # 모든 재시도 실패
    if last_error:
        error_type = classify_youtube_error(last_error)
        error_detail = f"\n\n기술 정보: {str(last_error)[:200]}"
        return {'error': ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown"]) + error_detail}

    return {'error': ERROR_MESSAGES["unknown"]}


def format_upload_date(date_str: str) -> str:
    """업로드 날짜 포맷팅 (YYYYMMDD -> YYYY.MM.DD)"""
    if not date_str:
        return "날짜 정보 없음"

    if not isinstance(date_str, str):
        return "날짜 정보 없음"

    if len(date_str) != 8:
        return date_str

    try:
        return f"{date_str[:4]}.{date_str[4:6]}.{date_str[6:8]}"
    except Exception:
        return date_str


def format_view_count(count: int) -> str:
    """조회수 포맷팅"""
    try:
        if not isinstance(count, (int, float)):
            count = int(count) if count else 0

        if count >= 100000000:
            return f"{count / 100000000:.1f}억회"
        elif count >= 10000:
            return f"{count / 10000:.1f}만회"
        elif count >= 1000:
            return f"{count / 1000:.1f}천회"
        else:
            return f"{count}회"
    except Exception:
        return "조회수 정보 없음"


def get_transcript(video_id: str, languages: List[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    유튜브 자막 추출

    Args:
        video_id: 유튜브 비디오 ID
        languages: 선호 언어 리스트 (기본: ['ko', 'ko-KR', 'en', 'en-US'])

    Returns:
        Tuple of (transcript_text, language_used) or (None, error_message)
    """
    # 입력 검증
    if not video_id:
        return None, "비디오 ID가 없어요."

    if not isinstance(video_id, str):
        return None, "잘못된 비디오 ID 형식이에요."

    video_id = video_id.strip()
    if not video_id:
        return None, "비디오 ID가 비어있어요."

    if languages is None:
        # 한국어 우선, 영어 대체
        languages = ['ko', 'ko-KR', 'ko-kr', 'en', 'en-US', 'en-GB']

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import (
            TranscriptsDisabled,
            NoTranscriptFound,
            VideoUnavailable,
        )

        try:
            # 먼저 지정된 언어로 시도
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            transcript = None
            used_language = None
            is_auto_generated = False

            # 1. 수동 자막 먼저 시도 (한국어 우선)
            for lang in languages:
                try:
                    transcript = transcript_list.find_manually_created_transcript([lang])
                    used_language = get_language_name(lang)
                    break
                except Exception:
                    continue

            # 2. 수동 자막이 없으면 자동 생성 자막 시도
            if transcript is None:
                for lang in languages:
                    try:
                        transcript = transcript_list.find_generated_transcript([lang])
                        used_language = f"{get_language_name(lang)} (자동 생성)"
                        is_auto_generated = True
                        break
                    except Exception:
                        continue

            # 3. 아무것도 없으면 사용 가능한 다른 언어 자막 중 선택
            if transcript is None:
                try:
                    available = list(transcript_list)
                    if available:
                        # 수동 자막 우선 선택
                        manual_transcripts = [t for t in available if not t.is_generated]
                        if manual_transcripts:
                            transcript = manual_transcripts[0]
                            used_language = f"{transcript.language} (수동)"
                        else:
                            transcript = available[0]
                            used_language = f"{transcript.language} (자동 생성)"
                            is_auto_generated = True
                except Exception:
                    pass

            if transcript:
                try:
                    transcript_data = transcript.fetch()

                    # 자막 텍스트 조합 (중복 제거 및 정리)
                    full_text = ""
                    prev_text = ""
                    for entry in transcript_data:
                        text = entry.get('text', '').strip()
                        # 중복 제거 및 빈 텍스트 스킵
                        if text and text != prev_text:
                            # 자동 생성 자막의 경우 [음악], [박수] 등 태그 제거
                            if is_auto_generated:
                                text = clean_auto_caption(text)
                            if text:
                                full_text += text + " "
                                prev_text = text

                    cleaned_text = full_text.strip()

                    if not cleaned_text:
                        return None, "자막이 있지만 내용이 비어있습니다."

                    return cleaned_text, used_language

                except Exception as e:
                    return None, f"자막 데이터를 가져오는 중 오류가 발생했어요: {str(e)[:100]}"
            else:
                return None, "NO_TRANSCRIPT:사용 가능한 자막이 없습니다. 음성 변환(STT)을 통해 텍스트를 추출할 수 있습니다."

        except TranscriptsDisabled:
            return None, "NO_TRANSCRIPT:이 영상은 자막이 비활성화되어 있습니다. 음성 변환(STT)을 통해 텍스트를 추출할 수 있습니다."
        except NoTranscriptFound:
            return None, "NO_TRANSCRIPT:이 영상에서 자막을 찾을 수 없습니다. 음성 변환(STT)을 통해 텍스트를 추출할 수 있습니다."
        except VideoUnavailable:
            return None, ERROR_MESSAGES["unavailable"]

    except ImportError:
        return None, ERROR_MESSAGES["library_missing"]
    except Exception as e:
        error_type = classify_youtube_error(e)
        return None, ERROR_MESSAGES.get(error_type, f"자막 추출 중 오류 발생: {str(e)[:100]}")


def get_language_name(lang_code: str) -> str:
    """언어 코드를 한글 이름으로 변환"""
    lang_names = {
        'ko': '한국어',
        'ko-KR': '한국어',
        'ko-kr': '한국어',
        'en': '영어',
        'en-US': '영어',
        'en-GB': '영어',
        'ja': '일본어',
        'zh': '중국어',
        'zh-CN': '중국어(간체)',
        'zh-TW': '중국어(번체)',
    }
    return lang_names.get(lang_code, lang_code)


def clean_auto_caption(text: str) -> str:
    """자동 생성 자막에서 불필요한 태그 제거"""
    if not text:
        return ""

    try:
        import re
        # [음악], [박수], [웃음] 등의 태그 제거
        text = re.sub(r'\[.*?\]', '', text)
        # (음악), (박수) 등의 태그 제거
        text = re.sub(r'\(.*?\)', '', text)
        # 연속 공백 제거
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    except Exception:
        return text


def get_transcript_with_timestamps(video_id: str, languages: List[str] = None) -> Tuple[Optional[List[Dict]], Optional[str]]:
    """
    타임스탬프가 포함된 자막 추출

    Returns:
        Tuple of (transcript_list, language_used) or (None, error_message)
        transcript_list: [{'start': float, 'duration': float, 'text': str}, ...]
    """
    # 입력 검증
    if not video_id:
        return None, "비디오 ID가 없어요."

    if languages is None:
        languages = ['ko', 'en']

    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        transcript = None
        used_language = None

        # 수동 자막 먼저 시도
        for lang in languages:
            try:
                transcript = transcript_list.find_manually_created_transcript([lang])
                used_language = lang
                break
            except Exception:
                continue

        # 자동 생성 자막 시도
        if transcript is None:
            for lang in languages:
                try:
                    transcript = transcript_list.find_generated_transcript([lang])
                    used_language = f"{lang} (자동 생성)"
                    break
                except Exception:
                    continue

        if transcript:
            transcript_data = transcript.fetch()
            return transcript_data, used_language
        else:
            return None, "사용 가능한 자막이 없습니다."

    except ImportError:
        return None, ERROR_MESSAGES["library_missing"]
    except Exception as e:
        error_type = classify_youtube_error(e)
        return None, ERROR_MESSAGES.get(error_type, f"자막 추출 중 오류 발생: {str(e)[:100]}")


def format_timestamp(seconds: float) -> str:
    """초를 MM:SS 또는 HH:MM:SS 형식으로 변환"""
    try:
        if not isinstance(seconds, (int, float)):
            seconds = float(seconds) if seconds else 0

        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
    except Exception:
        return "00:00"


def chunk_transcript(transcript: str, max_chars: int = 4000) -> List[str]:
    """
    긴 자막을 청크로 분할 (API 토큰 제한 대응)

    Args:
        transcript: 전체 자막 텍스트
        max_chars: 청크당 최대 문자 수

    Returns:
        청크 리스트
    """
    # 입력 검증
    if not transcript:
        return []

    if not isinstance(transcript, str):
        return []

    if len(transcript) <= max_chars:
        return [transcript]

    chunks = []

    try:
        sentences = transcript.replace('. ', '.|').replace('? ', '?|').replace('! ', '!|').split('|')

        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk) + len(sentence) <= max_chars:
                current_chunk += sentence + " "
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + " "

        if current_chunk:
            chunks.append(current_chunk.strip())

    except Exception:
        # 문장 분할 실패 시 단순 분할
        for i in range(0, len(transcript), max_chars):
            chunks.append(transcript[i:i + max_chars])

    return chunks


def process_multiple_videos(urls: List[str]) -> List[Dict]:
    """
    여러 유튜브 영상 일괄 처리

    Args:
        urls: 유튜브 URL 리스트

    Returns:
        처리 결과 리스트
    """
    results = []

    # 입력 검증
    if not urls:
        return []

    if not isinstance(urls, list):
        return []

    for i, url in enumerate(urls):
        try:
            # URL 검증
            if not url:
                continue

            if not isinstance(url, str):
                continue

            url = url.strip()
            if not url:
                continue

            video_id = extract_video_id(url)
            if not video_id:
                results.append({
                    'url': url,
                    'error': '유효하지 않은 유튜브 URL입니다.',
                    'part_number': i + 1,
                    'has_error': True,
                })
                continue

            # 영상 정보 가져오기
            video_info = get_video_info(url)
            if video_info and 'error' in video_info:
                results.append({
                    'url': url,
                    'error': video_info['error'],
                    'part_number': i + 1,
                    'has_error': True,
                })
                continue

            # 자막 가져오기
            transcript, lang = get_transcript(video_id)

            result = {
                'url': url,
                'video_id': video_id,
                'part_number': i + 1,
                'info': video_info,
                'transcript': transcript,
                'transcript_language': lang,
                'has_error': transcript is None,
                'error': lang if transcript is None else None,
            }

            results.append(result)

        except Exception as e:
            results.append({
                'url': url if isinstance(url, str) else str(url),
                'error': f"처리 중 오류 발생: {str(e)[:100]}",
                'part_number': i + 1,
                'has_error': True,
            })

    return results


def merge_transcripts_for_book(video_results: List[Dict]) -> str:
    """
    여러 영상의 자막을 책 구조로 통합

    Args:
        video_results: process_multiple_videos의 결과

    Returns:
        통합된 자막 텍스트 (Part 구조)
    """
    # 입력 검증
    if not video_results:
        return ""

    if not isinstance(video_results, list):
        return ""

    merged = ""

    for result in video_results:
        try:
            if not isinstance(result, dict):
                continue

            if result.get('has_error') or not result.get('transcript'):
                continue

            part_num = result.get('part_number', 1)
            title = result.get('info', {}).get('title', f'Part {part_num}') if result.get('info') else f'Part {part_num}'
            transcript = result.get('transcript', '')

            if not transcript:
                continue

            merged += f"\n\n=== Part {part_num}: {title} ===\n\n"
            merged += transcript
            merged += "\n"

        except Exception:
            continue

    return merged.strip()


def safe_get_video_info(url: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    안전하게 영상 정보를 가져오는 래퍼 함수

    Returns:
        Tuple of (video_info_dict, error_message)
    """
    try:
        result = get_video_info(url)

        if not result:
            return None, ERROR_MESSAGES["unknown"]

        if 'error' in result:
            return None, result['error']

        return result, None

    except Exception as e:
        error_type = classify_youtube_error(e)
        return None, ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown"])


def safe_get_transcript(video_id: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    안전하게 자막을 가져오는 래퍼 함수

    Returns:
        Tuple of (transcript_text, language, error_message)
    """
    try:
        transcript, lang_or_error = get_transcript(video_id)

        if transcript:
            return transcript, lang_or_error, None
        else:
            return None, None, lang_or_error

    except Exception as e:
        error_type = classify_youtube_error(e)
        return None, None, ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown"])

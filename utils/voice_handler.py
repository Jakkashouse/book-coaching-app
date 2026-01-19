"""음성 처리 모듈 - 음성 입력을 텍스트로 변환 + 강화된 에러 핸들링"""
import streamlit as st
from openai import OpenAI
import tempfile
import os
from io import BytesIO
import time


# 지원하는 오디오 형식
SUPPORTED_AUDIO_FORMATS = ["mp3", "wav", "m4a", "ogg", "webm", "mp4"]
MAX_FILE_SIZE_MB = 25

# 에러 메시지 (전문적이고 정중한 한국어)
ERROR_MESSAGES = {
    "api_key": """
**음성 인식 기능을 사용할 수 없습니다.**

관리자에게 "OpenAI API 키 설정이 필요합니다"라고 문의해 주세요.
""",
    "network": """
**인터넷 연결 오류가 발생했습니다.**

다음 사항을 확인해 주세요:
1. 와이파이 또는 인터넷 연결 상태 확인
2. 잠시 후 다시 시도
""",
    "file_format": """
**지원하지 않는 파일 형식입니다.**

mp3, wav, m4a 등의 음성 파일을 선택해 주세요.
""",
    "file_size": """
**파일 용량이 초과되었습니다.**

25MB 이하의 파일을 사용해 주세요.
""",
    "empty_audio": """
**녹음된 내용이 너무 짧습니다.**

조금 더 길게 녹음해 주시겠습니까?
""",
    "no_speech": """
**음성이 감지되지 않았습니다.**

조금 더 크게, 또박또박 말씀해 주세요.
""",
    "timeout": """
**응답 시간이 초과되었습니다.**

파일 용량이 큰 경우 처리 시간이 길어질 수 있습니다.
잠시 후 다시 시도해 주세요.
""",
    "rate_limit": """
**요청 횟수가 초과되었습니다.**

1분 후에 다시 시도해 주세요.
""",
    "permission": """
**마이크 접근 권한이 필요합니다.**

브라우저에서 마이크 사용을 허용해 주세요:
1. 주소창 옆의 자물쇠/카메라 아이콘 클릭
2. '마이크'를 '허용'으로 변경
3. 페이지 새로고침
""",
    "unknown": """
**일시적인 오류가 발생했습니다.**

다시 한번 시도해 주시겠습니까?
문제가 지속되면 관리자에게 문의해 주세요.
"""
}

# 재시도 설정
MAX_RETRIES = 2
RETRY_DELAY = 1  # 초


def classify_audio_error(error: Exception) -> str:
    """오디오 관련 에러 유형 분류"""
    error_str = str(error).lower()

    if any(keyword in error_str for keyword in ['connection', 'network', 'unreachable', 'dns', 'socket']):
        return "network"

    if any(keyword in error_str for keyword in ['timeout', 'timed out']):
        return "timeout"

    if any(keyword in error_str for keyword in ['rate limit', 'rate_limit', '429', 'too many']):
        return "rate_limit"

    if any(keyword in error_str for keyword in ['invalid', 'format', 'decode', 'corrupt']):
        return "file_format"

    if any(keyword in error_str for keyword in ['too large', 'size', 'limit exceeded']):
        return "file_size"

    if any(keyword in error_str for keyword in ['401', 'unauthorized', 'api key', 'authentication']):
        return "api_key"

    if any(keyword in error_str for keyword in ['permission', 'denied', 'not allowed']):
        return "permission"

    return "unknown"


def get_openai_client():
    """OpenAI 클라이언트 인스턴스 반환"""
    try:
        api_key = st.secrets.get("OPENAI_API_KEY")
        if not api_key or api_key == "여기에_OPENAI_API_키_입력":
            return None
        return OpenAI(api_key=api_key)
    except Exception as e:
        return None


def transcribe_audio(audio_data, file_extension="wav"):
    """
    음성 데이터를 텍스트로 변환 (Whisper API 사용)

    Args:
        audio_data: 오디오 바이너리 데이터 또는 BytesIO 객체
        file_extension: 파일 확장자

    Returns:
        변환된 텍스트 또는 None (실패 시)
    """
    client = get_openai_client()

    if client is None:
        st.error(ERROR_MESSAGES["api_key"])
        return None

    # 입력 검증
    try:
        # BytesIO 객체인 경우 처리
        if isinstance(audio_data, BytesIO):
            audio_bytes = audio_data.getvalue()
        else:
            audio_bytes = audio_data

        # 오디오 데이터 검증
        if not audio_bytes:
            st.warning(ERROR_MESSAGES["empty_audio"])
            return None

        if len(audio_bytes) < 1000:
            st.warning(ERROR_MESSAGES["empty_audio"])
            return None

        # 파일 크기 검증
        file_size_mb = len(audio_bytes) / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            st.error(f"파일 용량이 초과되었습니다. {MAX_FILE_SIZE_MB}MB 이하의 파일을 사용해 주세요. (현재: {file_size_mb:.1f}MB)")
            return None

    except Exception as e:
        st.error(ERROR_MESSAGES["file_format"])
        return None

    tmp_file_path = None
    last_error = None

    # 재시도 로직
    for attempt in range(MAX_RETRIES):
        try:
            # 임시 파일로 저장 후 Whisper API 호출
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=f".{file_extension}"
            ) as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_file_path = tmp_file.name

            with open(tmp_file_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="ko"  # 한국어 설정
                )

            # 변환된 텍스트가 비어있는지 확인
            if not transcription.text or transcription.text.strip() == "":
                st.warning(ERROR_MESSAGES["no_speech"])
                return None

            return transcription.text

        except Exception as e:
            last_error = e
            error_type = classify_audio_error(e)

            # 재시도가 의미 없는 에러는 바로 반환
            if error_type in ["api_key", "file_format", "file_size", "permission"]:
                st.error(ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown"]))
                return None

            # 마지막 시도가 아니면 대기 후 재시도
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (attempt + 1))
                continue

        finally:
            # 임시 파일 삭제
            if tmp_file_path:
                try:
                    if os.path.exists(tmp_file_path):
                        os.remove(tmp_file_path)
                except Exception:
                    pass  # 임시 파일 삭제 실패는 무시

    # 모든 재시도 실패
    if last_error:
        error_type = classify_audio_error(last_error)
        st.error(ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown"]))

        # 디버깅용 상세 정보
        with st.expander("기술 정보 (관리자에게 전달해 주세요)", expanded=False):
            st.code(f"에러 유형: {error_type}\n에러 내용: {str(last_error)}")

    return None


def validate_audio_file(uploaded_file):
    """
    업로드된 오디오 파일 유효성 검사

    Args:
        uploaded_file: Streamlit UploadedFile 객체

    Returns:
        (is_valid, error_message)
    """
    if uploaded_file is None:
        return False, "파일을 선택해 주세요."

    try:
        # 파일 이름 검증
        file_name = uploaded_file.name
        if not file_name:
            return False, "파일 이름을 확인할 수 없습니다."

        file_name = file_name.lower()

        # 파일 확장자 확인
        file_ext = file_name.split('.')[-1] if '.' in file_name else ''

        if not file_ext:
            return False, "파일 확장자를 확인할 수 없습니다. 파일 이름에 확장자가 포함되어 있는지 확인해 주세요."

        if file_ext not in SUPPORTED_AUDIO_FORMATS:
            formats_str = ', '.join(SUPPORTED_AUDIO_FORMATS)
            return False, f"지원하지 않는 파일 형식입니다. 사용 가능한 형식: {formats_str}"

        # 파일 크기 확인
        file_size_mb = uploaded_file.size / (1024 * 1024)
        if file_size_mb > MAX_FILE_SIZE_MB:
            return False, f"파일 용량이 초과되었습니다. {MAX_FILE_SIZE_MB}MB 이하의 파일을 선택해 주세요. (현재: {file_size_mb:.1f}MB)"

        # 파일 크기가 너무 작은 경우 (빈 파일 체크)
        if uploaded_file.size < 1000:
            return False, "파일 용량이 너무 작습니다. 올바른 음성 파일인지 확인해 주세요."

        return True, ""

    except Exception as e:
        return False, f"파일 확인 중 오류가 발생했습니다: {str(e)}"


def get_file_extension(uploaded_file):
    """업로드된 파일의 확장자 반환"""
    if uploaded_file is None:
        return "wav"

    try:
        file_name = uploaded_file.name.lower()
        return file_name.split('.')[-1] if '.' in file_name else 'wav'
    except Exception:
        return 'wav'


def render_voice_mode_ui():
    """
    음성 모드 UI 렌더링

    Returns:
        transcribed_text: 변환된 텍스트 (없으면 None)
    """
    st.markdown("""
    <style>
    /* 음성 모드 스타일 */
    .voice-mode-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 16px;
        padding: 2rem;
        margin: 1rem 0;
        color: white;
    }
    .voice-header {
        font-size: 1.8rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 1rem;
    }
    .voice-description {
        text-align: center;
        opacity: 0.9;
        margin-bottom: 1.5rem;
    }
    .mic-button-container {
        text-align: center;
        margin: 1.5rem 0;
    }
    .recording-indicator {
        display: inline-block;
        width: 12px;
        height: 12px;
        background: #ff4444;
        border-radius: 50%;
        margin-right: 8px;
        animation: pulse-recording 1s infinite;
    }
    @keyframes pulse-recording {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.5; transform: scale(1.2); }
    }
    .transcription-box {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        margin-top: 1rem;
        color: #333;
        border: 2px solid #667eea;
    }
    .transcription-preview {
        font-size: 1.1rem;
        line-height: 1.8;
        min-height: 100px;
    }
    </style>
    """, unsafe_allow_html=True)

    transcribed_text = None

    # API 키 확인
    if get_openai_client() is None:
        st.error(ERROR_MESSAGES["api_key"])
        return None

    # 음성 입력 방식 선택 - 전문적인 스타일
    st.markdown("### 음성 입력 방식 선택")
    input_method = st.radio(
        "방식 선택",
        ["실시간 녹음", "파일 업로드"],
        horizontal=True,
        help="마이크로 직접 녹음하거나, 기존 녹음 파일을 업로드할 수 있습니다.",
        label_visibility="collapsed"
    )

    if input_method == "실시간 녹음":
        transcribed_text = render_microphone_input()
    else:
        transcribed_text = render_file_upload_input()

    return transcribed_text


def render_microphone_input():
    """
    마이크 녹음 UI

    Returns:
        transcribed_text: 변환된 텍스트 (없으면 None)
    """
    st.markdown("""
    <div class="help-box" style="background: #E3F2FD; border: 2px solid #1565C0; padding: 1.2rem; border-radius: 12px;">
    <b style="font-size: 1.2rem;">녹음 방법 안내</b>
    <ol style="margin: 0.8rem 0; font-size: 1.1rem; line-height: 1.8;">
    <li>아래 <b>마이크 버튼</b>을 클릭합니다</li>
    <li>브라우저에서 마이크 사용 허용을 요청하면 <b>"허용"</b>을 선택합니다</li>
    <li>원고에 담고 싶은 내용을 <b>또박또박 말씀해 주세요</b></li>
    <li>녹음이 끝나면 <b>정지 버튼</b>을 클릭합니다</li>
    <li>마지막으로 <b>"텍스트로 변환"</b> 버튼을 클릭합니다</li>
    </ol>
    </div>
    """, unsafe_allow_html=True)

    # 녹음 상태 관리
    if "is_recording" not in st.session_state:
        st.session_state.is_recording = False
    if "recorded_audio" not in st.session_state:
        st.session_state.recorded_audio = None

    # st.audio_input 사용 (Streamlit 1.27+)
    st.markdown("### 녹음하기")

    # 마이크 버튼 스타일 강화
    st.markdown("""
    <style>
    /* 마이크 버튼을 크게 만들기 */
    [data-testid="stAudioInput"] > div {
        min-height: 80px !important;
    }
    [data-testid="stAudioInput"] button {
        min-width: 70px !important;
        min-height: 70px !important;
        font-size: 2rem !important;
    }
    </style>
    """, unsafe_allow_html=True)

    try:
        audio_value = st.audio_input(
            "마이크 버튼을 클릭하여 녹음을 시작하세요",
            help="마이크 버튼을 클릭하면 녹음이 시작됩니다."
        )
    except Exception as e:
        st.error(ERROR_MESSAGES["permission"])
        with st.expander("기술 정보", expanded=False):
            st.code(str(e))
        return None

    if audio_value is not None:
        st.session_state.recorded_audio = audio_value

        # 녹음 완료 표시
        st.markdown("""
        <div style="background: #E8F5E9; padding: 1rem; border-radius: 10px; text-align: center; margin: 1rem 0;">
            <span style="font-size: 1.5rem; color: #2E7D32; font-weight: bold;">녹음이 완료되었습니다</span>
        </div>
        """, unsafe_allow_html=True)

        # 녹음된 오디오 미리듣기
        st.markdown("#### 녹음 내용 미리듣기")
        try:
            st.audio(audio_value, format="audio/wav")
        except Exception as e:
            st.warning("미리듣기를 재생할 수 없습니다. 텍스트 변환은 정상적으로 진행됩니다.")

        # 변환 버튼 - 더 크고 눈에 띄게
        st.markdown("")  # 여백
        if st.button("텍스트로 변환", type="primary", use_container_width=True, key="convert_mic_audio"):
            with st.spinner("AI가 음성을 분석하고 있습니다. 잠시만 기다려 주세요..."):
                try:
                    # 오디오 데이터 읽기
                    audio_bytes = audio_value.getvalue()
                    text = transcribe_audio(audio_bytes, "wav")

                    if text:
                        st.session_state.voice_transcribed_text = text
                        st.success("음성이 텍스트로 변환되었습니다.")
                        st.rerun()
                except Exception as e:
                    error_type = classify_audio_error(e)
                    st.error(ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown"]))
    else:
        # 녹음 전 안내
        st.info("상단의 마이크 버튼을 클릭하여 녹음을 시작해 주세요.")

    # 변환된 텍스트 반환
    return st.session_state.get("voice_transcribed_text")


def render_file_upload_input():
    """
    파일 업로드 UI

    Returns:
        transcribed_text: 변환된 텍스트 (없으면 None)
    """
    st.markdown("""
    <div class="help-box" style="background: #FFF8E1; border: 2px solid #F57C00; padding: 1.2rem; border-radius: 12px;">
    <b style="font-size: 1.2rem;">파일 업로드 안내</b><br><br>
    <b>지원 형식:</b> mp3, wav, m4a, ogg, webm, mp4<br>
    <b>최대 용량:</b> 25MB<br><br>
    <span style="color: #666;">예: 스마트폰 녹음 파일, 음성 메모 등</span>
    </div>
    """, unsafe_allow_html=True)

    try:
        uploaded_file = st.file_uploader(
            "음성 파일을 선택해 주세요",
            type=SUPPORTED_AUDIO_FORMATS,
            help="컴퓨터에서 음성 파일을 찾아 선택해 주세요."
        )
    except Exception as e:
        st.error("파일 업로드 중 오류가 발생했습니다. 페이지를 새로고침해 주세요.")
        return None

    if uploaded_file is not None:
        # 파일 유효성 검사
        is_valid, error_msg = validate_audio_file(uploaded_file)

        if not is_valid:
            st.error(error_msg)
            return None

        # 파일 정보 표시 - 전문적 스타일
        file_size_mb = uploaded_file.size / (1024 * 1024)
        st.markdown(f"""
        <div style="background: #E8F5E9; padding: 1rem; border-radius: 10px; margin: 1rem 0;">
            <span style="font-size: 1.2rem; color: #2E7D32;">
                <b>파일이 업로드되었습니다</b><br>
                파일명: {uploaded_file.name}<br>
                용량: {file_size_mb:.1f}MB
            </span>
        </div>
        """, unsafe_allow_html=True)

        # 오디오 미리듣기
        st.markdown("#### 업로드된 파일 미리듣기")
        try:
            st.audio(uploaded_file)
        except Exception as e:
            st.warning("미리듣기를 재생할 수 없습니다. 텍스트 변환은 정상적으로 진행됩니다.")

        # 변환 버튼
        st.markdown("")  # 여백
        if st.button("텍스트로 변환", type="primary", use_container_width=True, key="convert_uploaded_audio"):
            with st.spinner("AI가 음성을 분석하고 있습니다. 파일 용량에 따라 시간이 소요될 수 있습니다..."):
                try:
                    file_ext = get_file_extension(uploaded_file)
                    audio_bytes = uploaded_file.getvalue()
                    text = transcribe_audio(audio_bytes, file_ext)

                    if text:
                        st.session_state.voice_transcribed_text = text
                        st.success("음성이 텍스트로 변환되었습니다.")
                        st.rerun()
                except Exception as e:
                    error_type = classify_audio_error(e)
                    st.error(ERROR_MESSAGES.get(error_type, ERROR_MESSAGES["unknown"]))
    else:
        st.info("상단에서 음성 파일을 선택해 주세요.")

    return st.session_state.get("voice_transcribed_text")


def render_transcription_editor(transcribed_text):
    """
    변환된 텍스트 편집기 렌더링

    Args:
        transcribed_text: 변환된 텍스트

    Returns:
        edited_text: 편집된 텍스트
    """
    if not transcribed_text:
        return None

    st.markdown("### 변환된 텍스트")
    st.markdown("""
    <div class="help-box" style="background: #E8F5E9; border: 2px solid #4CAF50; padding: 1.2rem; border-radius: 12px;">
    <b style="font-size: 1.1rem;">AI가 음성을 텍스트로 변환했습니다.</b><br><br>
    아래 내용을 확인하시고, 수정이 필요한 부분이 있으면 직접 편집해 주세요.<br>
    확인이 완료되면 하단의 버튼을 클릭해 주세요.
    </div>
    """, unsafe_allow_html=True)

    # 변환 결과 통계 - 전문적 스타일
    try:
        char_count = len(transcribed_text.replace(" ", "").replace("\n", ""))
        word_count = len(transcribed_text.split())

        col1, col2 = st.columns(2)
        with col1:
            st.metric("글자 수", f"{char_count}자", help="공백 제외 글자 수")
        with col2:
            st.metric("단어 수", f"{word_count}개", help="공백 기준 단어 수")
    except Exception:
        pass  # 통계 계산 실패는 무시

    # 텍스트 미리보기 (읽기 전용)
    st.markdown("#### 텍스트 미리보기")
    try:
        preview_text = transcribed_text.replace('\n', '<br>')
        st.markdown(f"""
        <div style="background: #FAFAFA; padding: 1.2rem; border-radius: 10px; border: 1px solid #E0E0E0;
                    font-size: 1.1rem; line-height: 1.8; max-height: 200px; overflow-y: auto;">
        {preview_text}
        </div>
        """, unsafe_allow_html=True)
    except Exception:
        st.text(transcribed_text[:500] + "..." if len(transcribed_text) > 500 else transcribed_text)

    # 편집 가능한 텍스트 영역
    st.markdown("#### 텍스트 편집")
    try:
        edited_text = st.text_area(
            "내용 수정",
            value=transcribed_text,
            height=250,
            help="수정이 필요한 부분이 있으면 직접 편집할 수 있습니다.",
            label_visibility="collapsed"
        )

        # 수정 여부 확인
        if edited_text != transcribed_text:
            st.success("내용이 수정되었습니다. 하단 버튼을 클릭하여 다음 단계로 진행해 주세요.")

        return edited_text
    except Exception as e:
        st.error("텍스트 편집기를 불러오는 중 오류가 발생했습니다.")
        return transcribed_text


def clear_voice_session():
    """음성 모드 세션 상태 초기화"""
    keys_to_clear = [
        "voice_transcribed_text",
        "recorded_audio",
        "is_recording",
        "voice_mode_active"
    ]
    for key in keys_to_clear:
        try:
            if key in st.session_state:
                del st.session_state[key]
        except Exception:
            pass  # 세션 상태 삭제 실패는 무시

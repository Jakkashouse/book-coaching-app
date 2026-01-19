# 책쓰기 코칭 자동화 웹앱

완전 초보자도 6만자 책을 완성할 수 있도록 설계된 AI 기반 책쓰기 코칭 앱입니다.

## 주요 기능

### 1. 7단계 책쓰기 프로세스
1. **정보 입력** - 책의 기본 정보 입력
2. **제목 생성** - AI가 10가지 제목 공식 기반 제목 추천
3. **목차 생성** - 5부 구조(Why-What-How-Do-Future) 40개 꼭지 목차
4. **초안 작성** - 꼭지별 2000자 초안 작성
5. **출간기획서** - 출판사 제출용 기획서 생성
6. **랜딩페이지** - 책/웨비나 홍보 페이지 카피 생성
7. **다운로드** - 완성된 원고 다운로드

### 2. 다양한 입력 모드
- **일반 모드**: 폼 기반 단계별 진행
- **채팅 모드**: 대화형으로 책 정보 수집 (초등학생 친화적)
- **음성 모드**: 음성으로 내용 입력 (Whisper API)
- **유튜브 모드**: 유튜브 강의 자막 기반 책 생성

### 3. 지원 기능
- 실시간 진행률 표시
- 자동 저장 및 복구
- 업적 시스템 (뱃지, 마일스톤)
- 도움 챗봇 (FAQ)
- 선생님께 질문하기

## 설치 방법

### 1. 저장소 클론
```bash
git clone [repository-url]
cd book_coaching_app
```

### 2. 가상 환경 설정 (권장)
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. API 키 설정
`.streamlit/secrets.toml.example`을 `.streamlit/secrets.toml`로 복사하고 API 키 입력:

```toml
ANTHROPIC_API_KEY = "sk-ant-api03-your-api-key-here"
OPENAI_API_KEY = "sk-your-openai-api-key-here"  # 음성 모드용
```

### 5. 앱 실행
```bash
streamlit run app.py
```

## 폴더 구조

```
book_coaching_app/
├── app.py                    # 메인 앱
├── requirements.txt          # 의존성
├── README.md                 # 문서
├── .gitignore               # Git 무시 파일
│
├── .streamlit/              # Streamlit 설정
│   ├── config.toml          # 테마 설정
│   └── secrets.toml.example # API 키 예시
│
├── prompts/                 # AI 프롬프트
│   ├── __init__.py
│   └── templates.py         # 프롬프트 템플릿
│
├── utils/                   # 유틸리티 모듈
│   ├── __init__.py
│   ├── claude_client.py     # Claude API 클라이언트
│   ├── voice_handler.py     # 음성 처리
│   ├── youtube_handler.py   # 유튜브 자막 처리
│   ├── contact_handler.py   # 연락/질문 기능
│   ├── help_chatbot.py      # 도움 챗봇
│   ├── achievement_system.py # 업적 시스템
│   ├── achievement_css.py   # 업적 CSS
│   ├── autosave_handler.py  # 자동 저장
│   ├── error_handler.py     # 에러 처리
│   └── mode_transition.py   # 모드 전환
│
├── pages/                   # 추가 페이지
│   └── admin_dashboard.py   # 관리자 대시보드
│
├── tests/                   # 테스트
│   ├── __init__.py
│   └── test_integration_flow.py
│
└── data/                    # 데이터 (gitignore)
    ├── autosave/           # 자동 저장
    └── messages.json       # 질문/답변
```

## 관리자 대시보드

관리자 대시보드 접속: `http://localhost:8501/admin_dashboard`

기능:
- 학생 질문 확인 및 답변
- 학생별 진행 현황 모니터링
- 데이터 내보내기 (JSON/CSV)

기본 비밀번호: `admin123` (반드시 변경하세요!)

## 환경 변수

`.streamlit/secrets.toml`에서 설정:

```toml
# API 키 (필수)
ANTHROPIC_API_KEY = "sk-ant-..."
OPENAI_API_KEY = "sk-..."  # 음성 모드용

# 관리자 설정
ADMIN_KAKAO_LINK = "https://open.kakao.com/o/..."
ADMIN_EMAIL = "coach@example.com"
ADMIN_PHONE = "010-1234-5678"
ADMIN_SHOW_PHONE = true
ADMIN_PASSWORD = "your-secure-password"
```

## 테스트 실행

```bash
pytest tests/ -v
```

## 배포 (Streamlit Cloud)

1. GitHub에 저장소 푸시
2. [Streamlit Cloud](https://share.streamlit.io/) 접속
3. 저장소 연결 및 배포
4. Settings > Secrets에서 API 키 설정

## 기술 스택

- **프론트엔드**: Streamlit
- **AI**: Claude (Anthropic), Whisper (OpenAI)
- **유튜브**: youtube-transcript-api, yt-dlp
- **테스트**: pytest

## 라이선스

이 프로젝트는 비공개입니다.

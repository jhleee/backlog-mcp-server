# Git-Chat-Log

Git을 백엔드로 활용하여 회의록 및 백로그를 관리하는 개발자 중심 도구입니다. MCP (Model Context Protocol)와 LangChain을 통해 LLM과 연동하여 자연어로 문서 관리 작업을 자동화할 수 있습니다.

## 🚀 주요 기능

### 📋 백로그 관리
- **생성/수정/삭제**: 백로그 아이템의 전체 생명주기 관리
- **상태 추적**: todo, in_progress, review, done, blocked, cancelled
- **우선순위 관리**: 1-5 레벨 우선순위 시스템
- **담당자 할당**: 작업 담당자 지정 및 추적
- **태그 시스템**: 유연한 분류 체계
- **마감일 관리**: 기한 설정 및 초과 알림

### 📝 회의록 관리
- **구조화된 회의록**: 참가자, 안건, 노트 등 체계적 관리
- **자동 파일명 생성**: 날짜 기반 자동 명명
- **Git 버전 관리**: 모든 변경사항 추적

### 🔍 고급 검색 기능
- **풀텍스트 검색**: 제목과 설명에서 키워드 검색
- **다중 필터링**: 상태, 담당자, 우선순위, 태그 등
- **날짜 범위 검색**: 생성일, 수정일, 마감일 기준
- **정렬 옵션**: 다양한 필드로 정렬 가능
- **페이지네이션**: 대량 데이터 효율적 처리
- **통계 정보**: 실시간 집계 데이터 제공
- **벡터 검색**: ChromaDB를 활용한 의미 기반 검색

### 🤖 AI 통합
- **MCP 서버**: FastAPI 기반 MCP 프로토콜 구현
- **LangChain 에이전트**: 자연어 명령 처리
- **자동 요약**: LLM을 통한 텍스트 요약
- **스마트 검색**: 의미 기반 백로그 검색

## 🛠️ 기술 스택

- **백엔드**: Python, FastAPI
- **Git 연동**: GitPython
- **LLM 연동**: LangChain, langchain-mcp-adapters
- **벡터DB**: ChromaDB
- **스케줄러**: APScheduler
- **MCP 지원**: fastapi-mcp

## 📦 설치

### 1. 저장소 클론
```bash
git clone https://github.com/yourusername/git-chat-log.git
cd git-chat-log
```

### 2. 가상환경 설정
```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정
`.env` 파일을 생성하고 다음 내용을 설정:
```env
# Git 설정
GIT_REPO_PATH=./git_repo
GIT_USER_NAME=Your Name
GIT_USER_EMAIL=your.email@example.com

# OpenAI API (선택사항)
OPENAI_API_KEY=your-api-key

# ChromaDB
CHROMA_PERSIST_PATH=./chroma_db
CHROMA_COLLECTION_NAME=backlogs

# 알림 설정 (선택사항)
SLACK_WEBHOOK_URL=your-slack-webhook
DISCORD_WEBHOOK_URL=your-discord-webhook
```

## 🚀 실행

### FastAPI-MCP 서버 실행
```bash
python fastapi_mcp_server.py
```

서버는 `http://localhost:8001`에서 실행됩니다.
- API 문서: http://localhost:8001/docs
- MCP SSE: http://localhost:8001/mcp/sse
- MCP HTTP: http://localhost:8001/mcp

## 📖 API 사용 예시

### 백로그 생성
```bash
curl -X POST http://localhost:8001/backlogs/create \
  -H "Content-Type: application/json" \
  -d '{
    "title": "새로운 기능 구현",
    "description": "사용자 인증 시스템 추가",
    "priority": 2,
    "assignee": "developer1",
    "tags": ["feature", "security"]
  }'
```

### 백로그 검색 (고급 쿼리)
```bash
# GET 방식
curl "http://localhost:8001/backlogs/query?status=todo&priority_min=1&priority_max=3&sort_by=priority"

# POST 방식 (더 복잡한 쿼리)
curl -X POST http://localhost:8001/backlogs/query \
  -H "Content-Type: application/json" \
  -d '{
    "full_text": "security",
    "status": ["todo", "in_progress"],
    "tags": ["security"],
    "sort_by": "updated_at",
    "sort_order": "desc",
    "include_stats": true
  }'
```

### 백로그 업데이트
```bash
curl -X PUT http://localhost:8001/backlogs/update \
  -H "Content-Type: application/json" \
  -d '{
    "item_id": "your-backlog-id",
    "title": "업데이트된 제목",
    "status": "in_progress",
    "priority": 1
  }'
```

### 백로그 상태만 변경
```bash
curl -X PUT http://localhost:8001/backlogs/status \
  -H "Content-Type: application/json" \
  -d '{
    "item_id": "your-backlog-id",
    "status": "done"
  }'
```

### 백로그 삭제
```bash
# 아카이브 후 삭제 (기본값)
curl -X DELETE http://localhost:8001/backlogs/your-backlog-id

# 영구 삭제
curl -X DELETE http://localhost:8001/backlogs/your-backlog-id?archive=false
```

## 🔍 쿼리 파라미터 옵션

### 텍스트 검색
- `full_text` - 제목과 설명에서 검색
- `title_contains` - 제목에서만 검색
- `description_contains` - 설명에서만 검색

### 필터링
- `status` - 상태 필터 (여러 개 가능)
- `assignee` - 담당자 필터
- `priority_min`, `priority_max` - 우선순위 범위
- `tags` - 태그 필터 (하나라도 일치)
- `tags_all` - 태그 필터 (모두 일치)

### 날짜 필터
- `created_after`, `created_before` - 생성일 범위
- `updated_after`, `updated_before` - 수정일 범위
- `due_after`, `due_before` - 마감일 범위
- `has_due_date` - 마감일 존재 여부

### 정렬 및 페이지네이션
- `sort_by` - 정렬 필드 (created_at, updated_at, priority, title, status)
- `sort_order` - 정렬 방향 (asc, desc)
- `limit` - 최대 결과 수 (1-100)
- `offset` - 건너뛸 결과 수

### 추가 옵션
- `include_stats` - 통계 정보 포함
- `include_archived` - 아카이브된 항목 포함

## 📁 프로젝트 구조

```
git-chat-log/
├── src/
│   ├── models/          # 데이터 모델
│   │   ├── backlog.py
│   │   └── meeting.py
│   ├── services/        # 비즈니스 로직
│   │   ├── git_service.py
│   │   ├── vector_service.py
│   │   ├── scheduler_service.py
│   │   └── notification_service.py
│   └── api/            # API 엔드포인트
│       └── mcp_tools.py
├── config/             # 설정 파일
│   └── settings.py
├── git_repo/          # Git 저장소 (자동 생성)
│   ├── meetings/      # 회의록
│   ├── backlogs/      # 백로그
│   └── archives/      # 아카이브
├── chroma_db/         # 벡터 데이터베이스
├── fastapi_mcp_server.py  # 메인 서버
├── requirements.txt   # 의존성
└── README.md         # 문서
```

## 🔧 개발 상태

### ✅ 완료된 기능
- Git 백엔드 시스템
- 백로그 CRUD 작업
- 회의록 관리
- 고급 검색 및 필터링
- MCP 프로토콜 구현
- ChromaDB 벡터 검색
- 일정 관리 시스템
- 알림 시스템 기초

### 🚧 개발 중
- Slack/Discord 봇 통합
- 웹 UI 인터페이스
- 더 많은 LLM 통합

## 📝 라이선스

MIT License

## 🤝 기여

기여를 환영합니다! Pull Request를 보내주세요.

## 📧 문의

이슈나 문의사항은 GitHub Issues를 통해 남겨주세요.
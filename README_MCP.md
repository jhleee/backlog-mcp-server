# Git-Chat-Log MCP Server

## 📋 개요

Git-Chat-Log MCP (Model Context Protocol) 서버는 Claude Desktop과 통합하여 Git 기반 회의록 및 백로그 관리를 자동화하는 도구입니다.

## 🚀 주요 기능

### 회의록 관리
- `create_meeting_note` - 회의록 생성 및 Git 커밋
- `list_meetings` - 모든 회의록 목록 조회

### 백로그 관리
- `create_backlog_item` - 백로그 아이템 생성
- `update_backlog_status` - 백로그 상태 업데이트 (todo/in_progress/review/done/blocked/cancelled)
- `list_backlogs` - 전체 백로그 목록 조회 (상태별 그룹화)
- `search_backlogs` - 자연어 검색 (벡터 DB 활용)

### 작업 모니터링
- `get_overdue_tasks` - 기한 초과 작업 조회
- `get_stale_tasks` - 오래된 작업 조회 (기본 7일)

## 🔧 설치 및 설정

### 1. 의존성 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정

`.env` 파일 생성:
```env
# Optional: For enhanced vector search
OPENAI_API_KEY=your_openai_api_key_here

# Optional: For notifications
SLACK_WEBHOOK_URL=your_slack_webhook_url
DISCORD_BOT_TOKEN=your_discord_bot_token
```

### 3. Claude Desktop 통합

#### Windows
1. `%APPDATA%\Claude\claude_desktop_config.json` 파일 열기
2. 다음 설정 추가:

```json
{
  "mcpServers": {
    "git-chat-log": {
      "command": "python",
      "args": ["E:\\workspace\\daily_project\\20250924_backlogai\\mcp_stdio_server.py"],
      "cwd": "E:\\workspace\\daily_project\\20250924_backlogai"
    }
  }
}
```

#### macOS
1. `~/Library/Application Support/Claude/claude_desktop_config.json` 파일 열기
2. 경로를 macOS에 맞게 수정하여 위 설정 추가

3. Claude Desktop 재시작

## 🧪 테스트

```bash
python test_mcp_server.py
```

## 📁 프로젝트 구조

```
git-chat-log/
├── mcp_stdio_server.py     # 메인 MCP 서버 (STDIO)
├── test_mcp_server.py       # 테스트 스크립트
├── src/
│   ├── models/              # 데이터 모델 (Meeting, Backlog)
│   ├── services/            # 서비스 (Git, Vector DB)
│   └── api/                 # API 엔드포인트
├── git_repo/                # Git 리포지토리 (자동 생성)
│   ├── meetings/            # 회의록 저장
│   └── backlogs/            # 백로그 저장
└── chroma_db/               # 벡터 DB 저장소 (자동 생성)
```

## 💬 사용 예시

Claude Desktop에서 다음과 같은 명령을 사용할 수 있습니다:

### 회의록 관련
- "Create a meeting note titled 'Sprint Planning' with Alice and Bob"
- "List all meetings"
- "Show meetings from this week"

### 백로그 관련
- "Create a backlog item for implementing user authentication"
- "Update task abc123 status to in_progress"
- "Show all backlog items"
- "Search for authentication-related tasks"

### 모니터링
- "Show me overdue tasks"
- "Find tasks that haven't been updated for 5 days"
- "What tasks are assigned to Alice?"

## 🔍 기술 스택

- **Python 3.9+**
- **FastAPI** - API 서버
- **GitPython** - Git 연동
- **ChromaDB** - 벡터 검색
- **MCP** - Model Context Protocol
- **LangChain** - LLM 통합 (선택적)

## 📝 라이센스

MIT

## 🤝 기여

Issues와 Pull Requests를 환영합니다!

## 📧 문의

문제가 있거나 도움이 필요한 경우 Issue를 생성해주세요.
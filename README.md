# Git-Chat-Log

Git을 백엔드로 활용하여 회의록 및 백로그를 관리하는 개발자 중심 도구

## 🚀 Features

- **Git 기반 데이터 저장**: 모든 데이터를 Git 리포지토리에 버전 관리
- **MCP (Model Context Protocol) 지원**: LLM과의 원활한 통합
- **LangChain 에이전트**: 자연어 명령으로 문서 관리 자동화
- **벡터DB 검색**: ChromaDB를 통한 시맨틱 검색
- **일정 관리**: APScheduler를 통한 자동 알림
- **챗봇 통합**: Slack/Discord 지원

## 📋 Prerequisites

- Python 3.9+
- Git
- OpenAI API Key 또는 Anthropic API Key

## 🛠️ Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/git-chat-log.git
cd git-chat-log
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Configure environment:
```bash
cp .env.example .env
# Edit .env with your API keys and settings
```

## 🚦 Quick Start

1. Start the MCP server:
```bash
python -m src.main
```

2. The server will be available at `http://localhost:8000`

## 📚 Project Structure

```
git-chat-log/
├── src/
│   ├── api/          # FastAPI endpoints
│   ├── models/       # Data models
│   ├── services/     # Business logic
│   └── utils/        # Utility functions
├── tests/            # Test files
├── docs/             # Documentation
├── config/           # Configuration files
└── requirements.txt  # Python dependencies
```

## 🧪 Testing

Run tests with pytest:
```bash
pytest tests/
```

## 📝 License

MIT

## 👥 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
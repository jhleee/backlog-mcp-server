# Git-Chat-Log 개발 TODO 리스트

## 🎯 프로젝트 개요
Git을 백엔드로 활용하여 회의록 및 백로그를 관리하는 개발자 중심 도구 개발

## 📋 개발 할 일 목록

### 1. 프로젝트 초기 설정
- [x] Python 프로젝트 구조 생성
- [x] 가상환경 설정
- [x] requirements.txt 작성 및 정리 (2025-09-25)
  - [x] FastAPI
  - [x] GitPython
  - [x] LangChain
  - [x] langchain-mcp-adapters
  - [x] ChromaDB
  - [x] APScheduler
  - [x] 불필요한 패키지 제거 (sqlalchemy, alembic, discord.py, slack-sdk, pytest, black, flake8, mypy, ipython, rich)
- [x] 기본 디렉토리 구조 생성 및 정리 (2025-09-25)
  - [x] `/src` - 소스 코드 (단일 디렉토리로 통합)
  - [x] `/tests` - 테스트 코드
  - [x] `/docs` - 문서
  - [x] `/config` - 설정 파일
  - [x] 중복 디렉토리 제거 (git_chat_log)

### 2. Git 백엔드 시스템 구현
#### 2.1 Git 리포지토리 관리
- [x] Git 리포지토리 초기화 기능
- [x] GitHub/GitLab 연동 설정
- [x] 인증 처리 (SSH/HTTPS)

#### 2.2 데이터 모델 구현
- [x] 회의록 데이터 모델 정의
  - [x] 파일 경로: `meetings/YYYY-MM-DD-title.md`
  - [x] 메타데이터 구조 설계
- [x] 백로그 데이터 모델 정의
  - [x] 파일 경로: `backlogs/item-id.md`
  - [x] 메타데이터 필드: status, assignee, due_date, last_updated

#### 2.3 Git 작업 함수 구현
- [x] 파일 생성 및 커밋 함수
- [x] 파일 업데이트 및 커밋 함수
- [x] 파일 읽기 함수
- [x] 변경 이력 조회 함수
- [x] 브랜치 관리 함수

### 3. MCP 서버 구축
#### 3.1 FastAPI 서버 설정
- [x] FastAPI 앱 초기화
- [x] CORS 설정
- [x] 에러 핸들링 미들웨어

#### 3.2 MCP 도구 구현
- [x] `create_meeting_note()` 도구
  - [x] 회의록 생성 로직
  - [x] Git 커밋 처리
- [x] `create_backlog_item()` 도구
  - [x] 백로그 생성 로직
  - [x] 고유 ID 생성
  - [x] Git 커밋 처리
- [x] `update_backlog_status()` 도구
  - [x] 백로그 상태 업데이트
  - [x] 변경 이력 기록
- [x] `search_backlogs_by_query()` 도구
  - [x] 벡터DB 검색 로직
- [x] `get_overdue_tasks()` 도구
  - [x] 기한 초과 태스크 필터링
- [x] `get_stale_tasks()` 도구
  - [x] 오래된 태스크 필터링
- [x] `summarize_text()` 도구
  - [x] LLM 요약 기능

#### 3.3 MCP 프로토콜 구현
- [x] MCP 스키마 정의
- [x] 도구 등록 시스템
- [x] 요청/응답 처리
- [x] FastAPI-MCP 라이브러리 통합
- [x] SSE 및 HTTP 트랜스포트 구현

### 4. 벡터DB 및 검색 시스템
#### 4.1 ChromaDB 설정
- [x] ChromaDB 초기화
- [x] 컬렉션 생성
- [x] 임베딩 모델 설정

#### 4.2 임베딩 및 인덱싱
- [x] 백로그 임베딩 함수
- [x] 임베딩 자동 업데이트 시스템
- [x] 벡터 인덱스 관리

#### 4.3 시맨틱 검색
- [x] 자연어 쿼리 처리
- [x] 유사도 기반 검색
- [x] 검색 결과 랭킹

### 5. 일정 관리 시스템
#### 5.1 스케줄러 설정
- [x] APScheduler 초기화
- [x] Job 스토어 설정
- [x] 실행 전략 구성

#### 5.2 일정 모니터링
- [x] 마감일 체크 Job
- [x] 오래된 태스크 체크 Job
- [x] 일정 알림 로직

#### 5.3 알림 시스템
- [x] Slack 연동
  - [x] Webhook 설정
  - [x] 메시지 템플릿
- [x] Discord 연동
  - [x] Bot 설정
  - [x] 채널 관리

### 6. LangChain 에이전트 구축
#### 6.1 에이전트 설정
- [x] LangChain 에이전트 초기화
- [x] LLM 모델 연결
- [x] 프롬프트 템플릿 작성

#### 6.2 MCP 어댑터 연동
- [x] langchain-mcp-adapters 설정
- [x] MCP 서버 연결
- [x] 도구 바인딩

#### 6.3 워크플로우 구현
- [x] 사용자 입력 파싱
- [x] 도구 선택 로직
- [x] 응답 생성 및 포매팅

### 7. 챗봇 인터페이스 (보류)
#### 7.1 Slack Bot
- [ ] ~~Slack App 생성~~ (현재 사용하지 않음)
- [ ] ~~이벤트 리스너~~
- [ ] ~~명령어 처리~~
- [ ] ~~응답 포매팅~~

#### 7.2 Discord Bot
- [ ] ~~Discord Bot 생성~~ (현재 사용하지 않음)
- [ ] ~~명령어 등록~~
- [ ] ~~메시지 핸들러~~
- [ ] ~~임베드 메시지~~

### 8. 테스트
#### 8.1 유닛 테스트
- [ ] Git 함수 테스트
- [ ] MCP 도구 테스트
- [ ] 벡터DB 테스트
- [ ] 스케줄러 테스트

#### 8.2 통합 테스트
- [ ] End-to-end 워크플로우 테스트
- [ ] 챗봇 시나리오 테스트
- [ ] 에러 핸들링 테스트

#### 8.3 성능 테스트
- [ ] 응답 시간 측정
- [ ] 동시 요청 처리
- [ ] 벡터DB 검색 성능

### 9. 배포 및 문서화
#### 9.1 배포 준비
- [x] Docker 컨테이너화
- [x] docker-compose.yml 작성
- [x] 환경 변수 설정
- [ ] CI/CD 파이프라인

#### 9.2 문서 작성
- [ ] API 문서 (OpenAPI)
- [ ] 사용자 가이드
- [ ] 개발자 가이드
- [ ] 설치 가이드

#### 9.3 모니터링
- [ ] 로깅 시스템
- [ ] 메트릭 수집
- [ ] 에러 트래킹
- [ ] 성능 모니터링

### 10. 개선 및 최적화
- [ ] 코드 리팩토링
- [ ] 성능 최적화
- [ ] 보안 강화
- [ ] 사용자 피드백 반영

## 🎯 성공 지표 측정
- [ ] MCP 도구 호출 빈도 측정 시스템
- [ ] 사용자 만족도 수집 기능
- [ ] 문서 생성/수정 시간 측정

## 📝 참고사항
- 각 항목 완료 시 체크박스 체크
- 우선순위에 따라 순서 조정 가능
- 세부 사항은 개발 진행하며 추가/수정
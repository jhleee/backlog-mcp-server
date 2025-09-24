# Python 3.11 slim 이미지 사용
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 시스템 패키지 업데이트 및 git 설치
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git \
    gcc \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# requirements.txt 복사 및 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 소스 코드 복사
COPY . .

# Git 사용자 설정 (컨테이너 내에서 git 작업을 위해)
RUN git config --global user.email "git-chat-log@example.com" && \
    git config --global user.name "Git Chat Log Service"

# 데이터 저장을 위한 볼륨 생성
VOLUME ["/app/data", "/app/meetings", "/app/backlogs"]

# FastAPI 기본 포트
EXPOSE 8000

# 환경변수 설정 (필요시 .env 파일로 오버라이드 가능)
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# FastAPI 서버 실행
CMD ["uvicorn", "fastapi_mcp_server:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
FROM python:3.11-slim

WORKDIR /app

# 시스템 패키지 업데이트 및 필요한 도구 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 의존성 파일 복사
COPY pyproject.toml ./

# pip 업그레이드 및 의존성 설치
RUN pip install --upgrade pip && \
    pip install python-dotenv redis requests httpx orjson celery pymongo

# 애플리케이션 코드 복사
COPY extractor/riot .

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1

# 기본 명령어 (docker-compose에서 오버라이드)
CMD ["python", "main.py"]


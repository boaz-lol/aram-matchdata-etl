import os
from celery import Celery
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

# Redis 연결 정보
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
redis_db = int(os.getenv("REDIS_DB", 0))
redis_password = os.getenv("REDIS_PASSWORD")

# Redis URL 구성
if redis_password:
    redis_url = f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
else:
    redis_url = f"redis://{redis_host}:{redis_port}/{redis_db}"

# Celery 앱 초기화
celery_app = Celery(
    "lp-patchnote",
    broker=redis_url,
    backend=redis_url,
    include=["tasks"],
)

# Celery 설정
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Seoul",
    enable_utc=True,
)

# 작업 스케줄 설정
celery_app.conf.beat_schedule = {
    "get-match-id-list": {
        "task": "tasks.get_match_id_list",
        "schedule": 120.0,  # 2분마다 실행
    },
    "get-match-info": {
        "task": "tasks.get_match_detail",
        "schedule": 120.0,  # 2분마다 실행
    },
}


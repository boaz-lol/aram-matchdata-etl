import os
import asyncio
import time
from typing import Tuple
import httpx
from celery_app import celery_app
from user.queue import UserIdQueue
from match.api import get_match_ids, get_match_detail_async, get_match_timeline_async
from db.mongodb import get_mongodb_client
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

load_dotenv()

# Riot API Rate Limit
MAX_REQUESTS_PER_2MIN = 2000
BATCH_SIZE = 100  # 1초당 최대 100개 동시 처리

# 기본 초기 user_id 목록 (큐가 비어있을 때 사용)
DEFAULT_INITIAL_USER_IDS = [
    "lgSZZkKWsSd0q6-ZIIXaBrSjWzHs7KKtSkKjuD6mYkHAEbSE12GRxwWA_io27Ov0xRU218FqL1WSaA",
    "nMwEA3weON9TMEKbjNlljKebJbQvDz-6RncjcNVufAaZ0O2qyWZTsoPTyPps2QwHRg9XANqnXenTpQ"
]


@celery_app.task(name="tasks.get_match_detail")
def get_match_info():
    """
    - match_id를 redis에서 가져와 match_info와 match_timeline을 가져온다.
    - match_info와 match_timeline을 하나의 document로 합쳐 mongodb에 저장한다.
    - match_info에 있는 user_id를 큐에 추가한다. (중복 제거 및 set에 넣을때 ttl 6시간)
    """

    return


@celery_app.task(name="tasks.get_match_id_list")
def get_match_id_list():
    return
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
BATCH_SIZE = 200  # 1초당 최대 200개 동시 처리

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
    from match.queue import MatchIdQueue

    match_queue = MatchIdQueue()
    user_queue = UserIdQueue()
    riot_api_key = os.getenv("RIOT_API_KEY")

    if not riot_api_key:
        logger.error("RIOT_API_KEY not found in environment variables")
        return {"status": "error", "message": "No API key"}

    max_matches = MAX_REQUESTS_PER_2MIN
    match_ids = []

    for _ in range(max_matches):
        match_id = match_queue.get_match_id()
        if not match_id:
            break
        match_ids.append(match_id)

    if not match_ids:
        logger.info("MatchIdQueue is empty")
        return {"status": "no_matches"}

    logger.info(f"Processing {len(match_ids)} match_ids")

    # 비동기 배치 처리 함수
    async def process_matches_batch(match_ids_batch):
        saved_count = 0
        participants_added = 0
        request_count = 0

        mongodb = get_mongodb_client()

        async with httpx.AsyncClient(timeout=30.0) as client:
            # BATCH_SIZE씩 처리
            for i in range(0, len(match_ids_batch), BATCH_SIZE):
                batch = match_ids_batch[i:i + BATCH_SIZE]

                logger.info(f"Processing batch {i//BATCH_SIZE + 1}: {len(batch)} matches")

                # detail과 timeline을 동시에 요청
                detail_tasks = [
                    get_match_detail_async(match_id, riot_api_key, client)
                    for match_id in batch
                ]
                timeline_tasks = [
                    get_match_timeline_async(match_id, riot_api_key, client)
                    for match_id in batch
                ]

                # 모든 요청을 동시에 실행
                results = await asyncio.gather(
                    *detail_tasks,
                    *timeline_tasks,
                    return_exceptions=True
                )

                # 결과 분리
                batch_size = len(batch)
                match_details = results[:batch_size]
                match_timelines = results[batch_size:]

                request_count += batch_size * 2

                # 각 match 처리
                for idx, match_id in enumerate(batch):
                    detail = match_details[idx]
                    timeline = match_timelines[idx]

                    # 에러 처리
                    if isinstance(detail, Exception):
                        logger.error(f"Error fetching detail for {match_id}: {detail}")
                        detail = None
                    if isinstance(timeline, Exception):
                        logger.error(f"Error fetching timeline for {match_id}: {timeline}")
                        timeline = None

                    # 둘 다 실패하면 스킵
                    if not detail and not timeline:
                        logger.warning(f"Skipping {match_id}: both API calls failed")
                        continue

                    try:
                        # 병합 document 생성
                        merged_doc = {}                        

                        if detail:
                            # 매치 참가자 user_id 추출
                            participants = detail.get("metadata", {}).get("participants", [])

                            TTL_6_HOURS = 6 * 60 * 60  # 21600 seconds

                            for participant_id in participants:
                                if participant_id:
                                    if user_queue.add_user_id(participant_id, ttl=TTL_6_HOURS):
                                        participants_added += 1

                            # 기본 detail 설정
                            merged_doc = {**detail}  # detail을 기본으로

                            # ARAM 필터링
                            game_mode = detail.get("info", {}).get("gameMode")
                            if game_mode != "ARAM":
                                logger.info(f"Skipping {match_id}: not ARAM (mode: {game_mode})")
                                continue

                        if timeline:
                            # timeline을 "timeline" 키 아래에 중첩
                            merged_doc["timeline"] = timeline

                        # MongoDB에 병합 document 저장
                        # 실제 몽고디비 사용시 아래 주석 제거 후 logger.info 주석 처리
                        if mongodb.save_match(merged_doc):
                            saved_count += 1
                            logger.info(f"Saved merged document for {match_id}")

                        # logger.info(f"Merged document: {merged_doc}")

                        

                    except Exception as e:
                        logger.error(f"Error processing {match_id}: {str(e)}", exc_info=True)
                        continue

                # 배치 간 1초 대기
                if i + BATCH_SIZE < len(match_ids_batch):
                    logger.info("Waiting 1 second before next batch...")
                    await asyncio.sleep(1.0)

        return saved_count, participants_added, request_count

    # 비동기 함수 실행
    try:
        saved, participants, requests = asyncio.run(
            process_matches_batch(match_ids)
        )

        logger.info(f"Completed: {saved} saved, {participants} participants added, {requests} API requests")

        return {
            "status": "success",
            "matches_processed": len(match_ids),
            "matches_saved": saved,
            "participants_added": participants,
            "api_requests": requests
        }

    except Exception as e:
        logger.error(f"Error in get_match_info: {str(e)}", exc_info=True)
        return {"status": "error", "message": str(e)}


@celery_app.task(name="tasks.get_match_id_list")
def get_match_id_list():
    """
    UserIdQueue에서 user_id를 가져와 match_id 목록 조회 후 MatchIdQueue에 추가
    """
    from match.queue import MatchIdQueue

    user_queue = UserIdQueue()
    match_queue = MatchIdQueue()
    riot_api_key = os.getenv("RIOT_API_KEY")

    if not riot_api_key:
        logger.error("RIOT_API_KEY not found in environment variables")
        return {"status": "error", "message": "No API key"}

    # UserIdQueue에서 user_id 가져오기
    user_id = user_queue.get_user_id()

    if not user_id:
        # 큐가 비어있으면 기본 user_id 추가
        logger.info("UserIdQueue is empty, adding default user_ids...")
        for default_id in DEFAULT_INITIAL_USER_IDS:
            if user_queue.add_user_id(default_id):
                logger.info(f"Added default user_id: {default_id}")

        # 다시 가져오기
        user_id = user_queue.get_user_id()
        if not user_id:
            logger.warning("No user_ids available after adding defaults")
            return {"status": "no_users"}

    try:
        logger.info(f"Fetching match_ids for user_id: {user_id}")
        match_ids = get_match_ids(user_id, riot_api_key, start=0, count=100)

        if not match_ids:
            logger.info(f"No match_ids found for user_id: {user_id}")
            return {
                "status": "success",
                "user_id": user_id,
                "match_ids_found": 0,
                "match_ids_added": 0
            }

        logger.info(f"Found {len(match_ids)} match_ids for user_id: {user_id}")

        # MatchIdQueue에 추가 (자동 중복 제거)
        added_count = 0
        for match_id in match_ids:
            if match_queue.add_match_id(match_id):
                added_count += 1

        logger.info(f"Added {added_count}/{len(match_ids)} new match_ids to queue")

        return {
            "status": "success",
            "user_id": user_id,
            "match_ids_found": len(match_ids),
            "match_ids_added": added_count
        }

    except Exception as e:
        logger.error(f"Error fetching match_ids for user_id {user_id}: {str(e)}", exc_info=True)
        return {
            "status": "error",
            "message": str(e),
            "user_id": user_id
        }
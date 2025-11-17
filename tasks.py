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

load_dotenv()

# Riot API Rate Limit
MAX_REQUESTS_PER_2MIN = 100
BATCH_SIZE = 20  # 1초당 최대 20개 동시 처리

# 기본 초기 user_id 목록 (큐가 비어있을 때 사용)
DEFAULT_INITIAL_USER_IDS = [
    "lgSZZkKWsSd0q6-ZIIXaBrSjWzHs7KKtSkKjuD6mYkHAEbSE12GRxwWA_io27Ov0xRU218FqL1WSaA",
    "nMwEA3weON9TMEKbjNlljKebJbQvDz-6RncjcNVufAaZ0O2qyWZTsoPTyPps2QwHRg9XANqnXenTpQ"
]


async def process_match_ids_async(
    match_ids: list,
    riot_api_key: str,
    mongodb,
    queue: UserIdQueue,
    initial_request_count: int = 0
) -> Tuple[int, int, int]:
    """
    match_ids를 20개씩 배치로 나눠서 비동기로 처리
    
    Args:
        match_ids: 처리할 match_id 리스트
        riot_api_key: Riot API 키
        mongodb: MongoDB 클라이언트
        queue: UserIdQueue 인스턴스
        initial_request_count: 이미 사용한 요청 수 (예: get_match_ids로 1개 사용)
    
    Returns:
        tuple: (saved_count, participants_added_count, total_request_count)
    """
    saved_count = 0
    participants_added_count = 0
    request_count = initial_request_count
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # match_ids를 20개씩 배치로 나누기
        for i in range(0, len(match_ids), BATCH_SIZE):
            # 2분당 100개 제한 체크
            if request_count >= MAX_REQUESTS_PER_2MIN:
                print(f"Rate limit reached: {request_count} requests. Stopping processing.")
                break
            
            batch = match_ids[i:i + BATCH_SIZE]
            batch_size = len(batch)
            
            # 남은 요청 수 확인 (100개 제한 고려)
            # match_id 1개당 detail + timeline 2개 요청이므로, batch_size * 2를 고려
            remaining_requests = MAX_REQUESTS_PER_2MIN - request_count
            max_match_ids_in_batch = remaining_requests // 2  # detail + timeline 각각 1개씩
            
            if max_match_ids_in_batch < batch_size:
                # 남은 요청 수만큼만 처리
                batch = batch[:max_match_ids_in_batch]
                batch_size = len(batch)
            
            if batch_size == 0:
                print(f"Rate limit reached. Cannot process more match_ids.")
                break
            
            print(f"Processing batch {i // BATCH_SIZE + 1}: {batch_size} match_ids (Total requests: {request_count}, will add {batch_size * 2} requests)")
            
            # 배치 내 모든 match_id에 대해 detail과 timeline을 동시에 요청
            detail_tasks = [
                get_match_detail_async(match_id, riot_api_key, client)
                for match_id in batch
            ]
            timeline_tasks = [
                get_match_timeline_async(match_id, riot_api_key, client)
                for match_id in batch
            ]
            
            # detail과 timeline을 동시에 요청
            results = await asyncio.gather(
                *detail_tasks,
                *timeline_tasks,
                return_exceptions=True
            )
            
            # 결과 분리: 앞의 batch_size개는 detail, 뒤의 batch_size개는 timeline
            match_details = results[:batch_size]
            match_timelines = results[batch_size:]
            
            request_count += batch_size * 2  # detail + timeline 각각 1개씩
            
            # 각 match_detail과 timeline 처리
            for idx, match_id in enumerate(batch):
                match_detail = match_details[idx]
                match_timeline = match_timelines[idx]
                
                # match_detail 처리
                if isinstance(match_detail, Exception):
                    print(f"Error processing match detail for {match_id}: {str(match_detail)}")
                    match_detail = None
                elif not match_detail:
                    print(f"Failed to get match detail for match_id: {match_id}")
                
                # match_timeline 처리
                if isinstance(match_timeline, Exception):
                    print(f"Error processing match timeline for {match_id}: {str(match_timeline)}")
                    match_timeline = None
                elif not match_timeline:
                    print(f"Failed to get match timeline for match_id: {match_id}")
                
                try:
                    # match_detail이 있으면 MongoDB에 저장
                    if match_detail:
                        infodata = match_detail.get("info", {})
                        if infodata.get("gameMode") == "ARAM":
                            if mongodb.save_match(match_detail):
                                saved_count += 1

                        # metadata.participants에서 user_id 추출하여 큐에 추가
                        metadata = match_detail.get("metadata", {})
                        participants = metadata.get("participants", [])

                        for participant_id in participants:
                            if participant_id:  # 빈 문자열 체크
                                if queue.add_user_id(participant_id):
                                    participants_added_count += 1
                                    print(f"새로운 user_id를 큐에 추가: {participant_id}")

                    # match_timeline이 있으면 match_detail 컬렉션에 저장
                    if match_timeline:
                        mongodb.save_match_timeline(match_id, match_timeline)
                    
                    print(f"Successfully processed match_id: {match_id}")
                except Exception as e:
                    print(f"Error processing match data for {match_id}: {str(e)}")
                    continue
            
            # 마지막 배치가 아니고, 아직 처리할 match_id가 남아있으면 1초 대기
            if i + BATCH_SIZE < len(match_ids) and request_count < MAX_REQUESTS_PER_2MIN:
                print(f"Waiting 1 second before next batch...")
                await asyncio.sleep(1.0)
    
    return saved_count, participants_added_count, request_count


@celery_app.task(name="tasks.process_user_queue")
def process_user_queue():
    """
    Redis 큐에서 user_id를 가져와서 match_ids를 조회하고 각 match_id로 전적 상세 정보를 가져오는 Celery 작업
    2분마다 Celery Beat에 의해 실행됨
    """
    queue = UserIdQueue()
    riot_api_key = os.getenv("RIOT_API_KEY")
    
    if not riot_api_key:
        print("Warning: RIOT_API_KEY not found in environment variables")
        return
    
    # 큐에서 user_id 가져오기
    user_id = queue.get_user_id()
    
    if not user_id:
        # 큐가 비어있으면 기본 user_id 추가
        print("Queue is empty, adding default user_ids...")
        added_count = 0
        for default_user_id in DEFAULT_INITIAL_USER_IDS:
            if queue.add_user_id(default_user_id):
                added_count += 1
                print(f"기본 user_id 추가됨: {default_user_id}")
        
        if added_count > 0:
            print(f"총 {added_count}개의 기본 user_id가 큐에 추가되었습니다. 다시 시도합니다.")
            # 추가한 user_id 중 하나를 가져오기
            user_id = queue.get_user_id()
        else:
            print("기본 user_id 추가 실패 또는 이미 존재함. 큐가 비어있습니다.")
            return
    
    print(f"Processing user_id: {user_id}")
    
    try:
        # match_id 리스트 조회
        match_ids = get_match_ids(user_id, riot_api_key)
        request_count = 1  # get_match_ids 호출로 1개 사용
        
        if not match_ids:
            print(f"No match IDs found for user_id: {user_id}")
            return
        
        print(f"Found {len(match_ids)} match IDs for user_id: {user_id}")
        
        # MongoDB 클라이언트 초기화
        mongodb = get_mongodb_client()
        
        # async 함수로 배치 처리 실행 mongodb,
        saved_count, participants_added_count, final_request_count = asyncio.run(
            process_match_ids_async(match_ids, riot_api_key,  mongodb, queue, initial_request_count=request_count)
        )
        
        request_count = final_request_count
        
        print(f"처리 완료: {saved_count}개 match 데이터 저장, {participants_added_count}개 user_id 큐에 추가 (총 {request_count}개 API 요청)")
        return {
            "user_id": user_id,
            "match_ids_count": len(match_ids),
            "saved_count": saved_count,
            "participants_added_count": participants_added_count,
            "request_count": request_count
        }
    except Exception as e:
        print(f"Error processing user_id {user_id}: {str(e)}")
        # 에러 발생 시 user_id를 다시 큐에 추가할지 결정
        # 현재는 에러 발생 시 재추가하지 않음
        raise


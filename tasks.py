import os
from celery_app import celery_app
from user.queue import UserIdQueue
from match.api import get_match_ids, get_match_detail
from dotenv import load_dotenv

load_dotenv()


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
        print("Queue is empty, no user_id to process")
        return
    
    print(f"Processing user_id: {user_id}")
    
    try:
        # match_id 리스트 조회
        match_ids = get_match_ids(user_id, riot_api_key)
        
        if not match_ids:
            print(f"No match IDs found for user_id: {user_id}")
            return
        
        print(f"Found {len(match_ids)} match IDs for user_id: {user_id}")
        
        # 각 match_id로 전적 상세 정보 가져오기
        match_details = []
        for match_id in match_ids:
            try:
                match_detail = get_match_detail(match_id, riot_api_key)
                if match_detail:
                    match_details.append(match_detail)
                    print(f"Successfully retrieved match detail for match_id: {match_id}")
                else:
                    print(f"Failed to get match detail for match_id: {match_id}")
            except Exception as e:
                print(f"Error getting match detail for match_id {match_id}: {str(e)}")
                # 개별 match_id 에러는 계속 진행
                continue
        
        print(f"Retrieved {len(match_details)} match details out of {len(match_ids)} match IDs")
        return {
            "user_id": user_id,
            "match_ids_count": len(match_ids),
            "match_details_count": len(match_details),
            "match_details": match_details
        }
    except Exception as e:
        print(f"Error processing user_id {user_id}: {str(e)}")
        # 에러 발생 시 user_id를 다시 큐에 추가할지 결정
        # 현재는 에러 발생 시 재추가하지 않음
        raise


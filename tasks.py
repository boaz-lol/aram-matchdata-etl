import os
from celery_app import celery_app
from user.queue import UserIdQueue
from match.api import get_match_ids, get_match_detail
from db.mongodb import get_mongodb_client
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
        
        # MongoDB 클라이언트 초기화
        mongodb = get_mongodb_client()
        
        # 각 match_id로 전적 상세 정보 가져오기
        saved_count = 0
        participants_added_count = 0
        
        for match_id in match_ids:
            try:
                match_detail = get_match_detail(match_id, riot_api_key)
                if match_detail:
                    # MongoDB에 저장
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
                    
                    print(f"Successfully processed match_id: {match_id}")
                else:
                    print(f"Failed to get match detail for match_id: {match_id}")
            except Exception as e:
                print(f"Error processing match_id {match_id}: {str(e)}")
                # 개별 match_id 에러는 계속 진행
                continue
        
        print(f"처리 완료: {saved_count}개 match 데이터 저장, {participants_added_count}개 user_id 큐에 추가")
        return {
            "user_id": user_id,
            "match_ids_count": len(match_ids),
            "saved_count": saved_count,
            "participants_added_count": participants_added_count
        }
    except Exception as e:
        print(f"Error processing user_id {user_id}: {str(e)}")
        # 에러 발생 시 user_id를 다시 큐에 추가할지 결정
        # 현재는 에러 발생 시 재추가하지 않음
        raise


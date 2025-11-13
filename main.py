import os
from dotenv import load_dotenv
from user.queue import UserIdQueue


def initialize_user_queue():
    """Redis 큐가 비어있을 때 초기 user_id를 추가하는 함수"""
    queue = UserIdQueue()
    
    # 큐와 SET 모두 확인 (데이터 불일치 체크)
    queue_size = queue.queue_size()
    set_size = queue.set_size()
    
    if queue_size > 0:
        print(f"UserIdQueue에 이미 {queue_size}개의 user_id가 있습니다. (SET: {set_size}개) 초기화를 건너뜁니다.")
        return
    
    # 큐는 비어있지만 SET에 데이터가 있으면 불일치 상태 (정리 필요)
    if set_size > 0:
        print(f"경고: 큐는 비어있지만 SET에 {set_size}개의 user_id가 있습니다. SET을 정리합니다.")
        queue.clear()
    
    # 환경 변수에서 초기 user_id 목록 가져오기
    initial_user_ids = os.getenv("INITIAL_USER_IDS", "")
    
    if not initial_user_ids:
        print("INITIAL_USER_IDS 환경 변수가 설정되지 않았습니다. 초기 user_id를 추가하지 않습니다.")
        return
    
    # 콤마로 구분된 user_id 파싱
    user_ids = [uid.strip() for uid in initial_user_ids.split(",") if uid.strip()]
    
    if not user_ids:
        print("INITIAL_USER_IDS에 유효한 user_id가 없습니다.")
        return
    
    # 각 user_id를 큐에 추가
    added_count = 0
    for user_id in user_ids:
        if queue.add_user_id(user_id):
            added_count += 1
            print(f"초기 user_id 추가됨: {user_id}")
        else:
            print(f"user_id가 이미 존재함 (건너뜀): {user_id}")
    
    print(f"총 {added_count}개의 초기 user_id가 큐에 추가되었습니다.")


def main():
    """큐에서 user_id를 가져오는 테스트용 스크립트"""
    # .env 파일에서 환경 변수 로드
    load_dotenv()
    
    # Redis 큐 초기화 (비어있을 때만)
    initialize_user_queue()
    
    queue = UserIdQueue()
    
    # 큐가 비어있는지 확인
    if queue.queue_size() == 0:
        print("UserIdQueue가 비어있습니다. 데이터 수집을 종료합니다.")
        return
    
    # 큐에서 user_id 가져오기
    user_id = queue.get_user_id()

if __name__ == "__main__":
    main()

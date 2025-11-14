import os
from dotenv import load_dotenv
from user.queue import UserIdQueue


def initialize_user_queue():
    """Redis 큐가 비어있을 때 초기 user_id를 추가하는 함수"""
    queue = UserIdQueue()
    
    # 큐와 SET 모두 확인 (데이터 불일치 체크)
    queue_size = queue.queue_size()
    set_size = queue.set_size()
    
    # 큐에 데이터가 있으면 모두 비우기
    if queue_size > 0 or set_size > 0:
        print(f"UserIdQueue에 {queue_size}개의 user_id가 있습니다. (SET: {set_size}개) 큐를 비웁니다.")
        queue.clear()
        print("큐가 비워졌습니다.")
    


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

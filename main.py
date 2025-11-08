import os
from dotenv import load_dotenv
from user.queue import UserIdQueue


def main():
    """큐에서 user_id를 가져오는 테스트용 스크립트"""
    # .env 파일에서 환경 변수 로드
    load_dotenv()
    
    queue = UserIdQueue()
    
    # 큐가 비어있는지 확인
    if queue.queue_size() == 0:
        print("UserIdQueue가 비어있습니다. 데이터 수집을 종료합니다.")
        return
    
    # 큐에서 user_id 가져오기
    user_id = queue.get_user_id()

if __name__ == "__main__":
    main()

import os
import redis
from dotenv import load_dotenv
from user.job import get_match_ids


def main():
    # .env 파일에서 환경 변수 로드
    load_dotenv()
    
    # RIOT_API_KEY 가져오기
    riot_api_key = os.getenv("RIOT_API_KEY")
    user_id = ""
    
    result = get_match_ids(user_id, riot_api_key)
    print(result)


if __name__ == "__main__":
    main()

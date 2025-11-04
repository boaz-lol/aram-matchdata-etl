import os
from dotenv import load_dotenv


def main():
    # .env 파일에서 환경 변수 로드
    load_dotenv()
    
    # RIOT_API_KEY 가져오기
    riot_api_key = os.getenv("RIOT_API_KEY")
    
    if riot_api_key:
        print(f"RIOT_API_KEY loaded successfully: {riot_api_key[:10]}...")
    else:
        print("RIOT_API_KEY not found in .env file")


if __name__ == "__main__":
    main()

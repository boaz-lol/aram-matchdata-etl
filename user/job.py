import requests
import orjson

def get_match_ids(user_id: str, api_key: str):
    # 포털과 동일한 방식: 헤더에 X-Riot-Token 사용
    # URL을 직접 구성하여 requests의 자동 인코딩 방지
    base_url = f"https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{user_id}/ids"
    url = f"{base_url}?start=0&count=100"
    
    headers = {
        "X-Riot-Token": api_key,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://developer.riotgames.com"
    }
    
    # 디버깅: 실제 요청 정보 출력
    print(f"Request URL: {url}")
    print(f"API Key: {api_key[:20]}...")
    print(f"User ID: {user_id}")
    print(f"Headers: {headers}")
    
    response = requests.get(url=url, headers=headers)
    
    # 에러 응답 확인
    if response.status_code != 200:
        error_detail = response.json() if response.content else response.text
        return {
            "status_code": response.status_code,
            "error": error_detail,
            "request_url": response.request.url,
            "request_headers": dict(response.request.headers)
        }
    
    return orjson.loads(response.content)
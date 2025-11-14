import requests
import httpx
import orjson
from typing import List, Dict, Any, Optional


def get_match_ids(user_id: str, api_key: str, start: int = 0, count: int = 100) -> List[str]:
    """
    user_id(puuid)로 match_id 리스트 가져오기
    
    Args:
        user_id: Riot API puuid
        api_key: Riot API 키
        start: 시작 인덱스 (기본값: 0)
        count: 가져올 개수 (기본값: 100)
        
    Returns:
        List[str]: match_id 리스트
    """
    # 포털과 동일한 방식: 헤더에 X-Riot-Token 사용
    # URL을 직접 구성하여 requests의 자동 인코딩 방지
    base_url = f"https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{user_id}/ids"
    url = f"{base_url}?start={start}&count={count}"
    
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
    print(f"Headers X-Riot-Token: {headers.get('X-Riot-Token', 'NOT FOUND')[:20]}...")
    
    response = requests.get(url=url, headers=headers)
    
    # 에러 응답 확인
    if response.status_code != 200:
        print("=" * 80)
        print("ERROR: get_match_ids failed")
        print("=" * 80)
        print(f"Request URL: {url}")
        print(f"Request Method: GET")
        print(f"Request Headers:")
        for key, value in headers.items():
            if key == "X-Riot-Token":
                print(f"  {key}: {value[:20]}... (length: {len(value)})")
            else:
                print(f"  {key}: {value}")
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        try:
            error_detail = response.json()
            print(f"Response Body (JSON): {error_detail}")
        except:
            error_detail = response.text
            print(f"Response Body (Text): {error_detail}")
        print(f"API Key Info: length={len(api_key)}, prefix={api_key[:20] if len(api_key) > 20 else api_key}...")
        print(f"User ID: {user_id}")
        print(f"Region: asia (https://asia.api.riotgames.com)")
        print(f"Possible Causes:")
        print(f"  1. User ID (puuid) may be from a different region (KR, NA, EUW, etc.)")
        print(f"  2. API key may not have permission for asia region")
        print(f"  3. User ID format may be invalid or corrupted")
        print(f"  4. API key may be expired or revoked")
        print("=" * 80)
        return []
    
    return orjson.loads(response.content)


def get_match_detail(match_id: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    match_id로 전적 상세 정보 가져오기
    
    Args:
        match_id: Riot API match_id
        api_key: Riot API 키
        
    Returns:
        Optional[Dict[str, Any]]: 전적 상세 정보, 에러 시 None
    """
    url = f"https://asia.api.riotgames.com/lol/match/v5/matches/{match_id}"
    
    headers = {
        "X-Riot-Token": api_key,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://developer.riotgames.com"
    }
    
    print(f"Requesting match detail for match_id: {match_id}")
    
    response = requests.get(url=url, headers=headers)
    
    # 에러 응답 확인
    if response.status_code != 200:
        print("=" * 80)
        print("ERROR: get_match_detail failed")
        print("=" * 80)
        print(f"Request URL: {url}")
        print(f"Request Method: GET")
        print(f"Request Headers:")
        for key, value in headers.items():
            if key == "X-Riot-Token":
                print(f"  {key}: {value[:20]}... (length: {len(value)})")
            else:
                print(f"  {key}: {value}")
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        try:
            error_detail = response.json()
            print(f"Response Body (JSON): {error_detail}")
        except:
            error_detail = response.text
            print(f"Response Body (Text): {error_detail}")
        print(f"Match ID: {match_id}")
        print(f"API Key Info: length={len(api_key)}, prefix={api_key[:20] if len(api_key) > 20 else api_key}...")
        print("=" * 80)
        return None
    
    return orjson.loads(response.content)


async def get_match_detail_async(match_id: str, api_key: str, client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
    """
    match_id로 전적 상세 정보를 비동기로 가져오기
    
    Args:
        match_id: Riot API match_id
        api_key: Riot API 키
        client: httpx.AsyncClient 인스턴스
        
    Returns:
        Optional[Dict[str, Any]]: 전적 상세 정보, 에러 시 None
    """
    url = f"https://asia.api.riotgames.com/lol/match/v5/matches/{match_id}"
    
    headers = {
        "X-Riot-Token": api_key,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://developer.riotgames.com"
    }
    
    try:
        response = await client.get(url=url, headers=headers)
        
        # 에러 응답 확인
        if response.status_code != 200:
            print("=" * 80)
            print("ERROR: get_match_detail_async failed")
            print("=" * 80)
            print(f"Request URL: {url}")
            print(f"Request Method: GET")
            print(f"Request Headers:")
            for key, value in headers.items():
                if key == "X-Riot-Token":
                    print(f"  {key}: {value[:20]}... (length: {len(value)})")
                else:
                    print(f"  {key}: {value}")
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            try:
                error_detail = response.json()
                print(f"Response Body (JSON): {error_detail}")
            except:
                error_detail = response.text
                print(f"Response Body (Text): {error_detail}")
            print(f"Match ID: {match_id}")
            print(f"API Key Info: length={len(api_key)}, prefix={api_key[:20] if len(api_key) > 20 else api_key}...")
            print("=" * 80)
            return None
        
        return orjson.loads(response.content)
    except Exception as e:
        import traceback
        print("=" * 80)
        print("ERROR: get_match_detail_async exception")
        print("=" * 80)
        print(f"Request URL: {url}")
        print(f"Match ID: {match_id}")
        print(f"Exception Type: {type(e).__name__}")
        print(f"Exception Message: {str(e)}")
        print(f"Traceback:")
        traceback.print_exc()
        print("=" * 80)
        return None


async def get_match_timeline_async(match_id: str, api_key: str, client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
    """
    match_id로 match timeline 정보를 비동기로 가져오기
    
    Args:
        match_id: Riot API match_id
        api_key: Riot API 키
        client: httpx.AsyncClient 인스턴스
        
    Returns:
        Optional[Dict[str, Any]]: match timeline 정보, 에러 시 None
    """
    url = f"https://asia.api.riotgames.com/lol/match/v5/matches/{match_id}/timeline"
    
    headers = {
        "X-Riot-Token": api_key,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://developer.riotgames.com"
    }
    
    try:
        response = await client.get(url=url, headers=headers)
        
        # 에러 응답 확인
        if response.status_code != 200:
            print("=" * 80)
            print("ERROR: get_match_timeline_async failed")
            print("=" * 80)
            print(f"Request URL: {url}")
            print(f"Request Method: GET")
            print(f"Request Headers:")
            for key, value in headers.items():
                if key == "X-Riot-Token":
                    print(f"  {key}: {value[:20]}... (length: {len(value)})")
                else:
                    print(f"  {key}: {value}")
            print(f"Response Status Code: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            try:
                error_detail = response.json()
                print(f"Response Body (JSON): {error_detail}")
            except:
                error_detail = response.text
                print(f"Response Body (Text): {error_detail}")
            print(f"Match ID: {match_id}")
            print(f"API Key Info: length={len(api_key)}, prefix={api_key[:20] if len(api_key) > 20 else api_key}...")
            print("=" * 80)
            return None
        
        return orjson.loads(response.content)
    except Exception as e:
        import traceback
        print("=" * 80)
        print("ERROR: get_match_timeline_async exception")
        print("=" * 80)
        print(f"Request URL: {url}")
        print(f"Match ID: {match_id}")
        print(f"Exception Type: {type(e).__name__}")
        print(f"Exception Message: {str(e)}")
        print(f"Traceback:")
        traceback.print_exc()
        print("=" * 80)
        return None


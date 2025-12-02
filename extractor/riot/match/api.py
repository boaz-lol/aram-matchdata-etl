import requests
import httpx
import orjson
from typing import List, Dict, Any, Optional


def get_match_ids(user_id: str, api_key: str, start: int = 0, count: int = 100) -> List[str]:
    """
    user_id(puuid)로 match_id 리스트 가져오기
    2000 requests every 10 seconds
    
    Args:
        user_id: Riot API puuid
        api_key: Riot API 키
        start: 시작 인덱스 (기본값: 0)
        count: 가져올 개수 (기본값: 100)
        
    Returns:
        List[str]: match_id 리스트
    """
    base_url = f"https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{user_id}/ids"
    url = f"{base_url}?start={start}&count={count}"
    
    headers = {
        "X-Riot-Token": api_key,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
        "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Charset": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://developer.riotgames.com"
    }

    response = requests.get(url=url, headers=headers)
    return orjson.loads(response.content)


def get_match_detail(match_id: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    match_id로 전적 상세 정보 가져오기
    2000 requests every 10 seconds
    
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
    
    response = requests.get(url=url, headers=headers)
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
        return orjson.loads(response.content)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None


async def get_match_timeline_async(match_id: str, api_key: str, client: httpx.AsyncClient) -> Optional[Dict[str, Any]]:
    """
    match_id로 match timeline 정보를 비동기로 가져오기
    2000 requests every 10 seconds
    
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
        return orjson.loads(response.content)
    except Exception as e:
        import traceback
        traceback.print_exc()
        return None


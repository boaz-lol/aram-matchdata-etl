import requests
import redis

def get_match_ids(api_key: str):
    user_id = redis.lpop('user_queue')

    if user_id:
        response = requests.get(
            url=f"https://asia.api.riotgames.com/lol/match/v5/matches/by-puuid/{user_id}/ids",
            params={
                "start": 0,
                "count": 100,
                "api_key": api_key
                }
            )
        match_id_list = list[str](response.json())
    
    redis.lpush('match_id_queue', match_id_list)


import os
import pymongo
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class MatchDataExtractor:
    def __init__(self, mongo_uri: str = None, db_name: str = 'aram-db'):
        self.mongo_uri = mongo_uri or os.getenv('MONGO_URI')

        if not self.mongo_uri:
            raise ValueError("MONGO_URI must be provided either as parameter or in .env file")

        self.client = pymongo.MongoClient(self.mongo_uri)
        self.db = self.client[db_name]
        self.matches_collection = self.db['matches']

    def extract_match_features(self, limit: int = None) -> pd.DataFrame:
        """
        MongoDB에서 데이터 불러와서 feature 생성
        """
        query = {
            'info.gameMode': 'ARAM',
            'info.gameDuration': {'$gte': 300}      # 5분 이상 게임만
        }

        projection = {
            'metadata.matchId': 1,
            'info.gameDuration': 1,
            'info.gameVersion': 1,
            'info.participants': 1
        }

        cursor = self.matches_collection.find(query, projection)
        if limit:
            cursor = cursor.limit(limit)

        all_player_data = []

        for match in cursor:
            match_id = match['metadata']['matchId']
            game_duration_min = match['info']['gameDuration'] / 60

            # 각 플레이어별 데이터 추출
            for participant in match['info']['participants']:
                player_features = self._extract_player_features(
                    participant,
                    game_duration_min,
                    match_id
                )
                all_player_data.append(player_features)

        return pd.DataFrame(all_player_data)


    def _extract_player_features(self, participant: Dict, game_duration: float, match_id: str) -> Dict:
        """
        플레이어 주요 지표 추출
        """
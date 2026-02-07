import os

import pymongo
import pandas as pd
from dotenv import load_dotenv
from feature_factory import FeatureFactory

load_dotenv()


class MatchDataExtractor:
    def __init__(self, mongo_uri: str = None, db_name: str = 'aram-db', use_mongodb: bool = True):
        """
        MongoDB에서 매치 데이터를 추출하는 클래스

        Args:
            mongo_uri: MongoDB 연결 URI (None이면 환경 변수 사용)
            db_name: 데이터베이스 이름
            use_mongodb: MongoDB 사용 여부
        """
        self.use_mongodb = use_mongodb

        if use_mongodb:
            self.mongo_uri = mongo_uri or os.getenv('MONGO_URI')

            if not self.mongo_uri:
                raise ValueError("MONGO_URI must be provided either as parameter or in .env file")

            self.client = pymongo.MongoClient(self.mongo_uri)
            self.db = self.client[db_name]
            self.matches_collection = self.db['match']

            # 연결 테스트
            try:
                self.client.server_info()
                print(f"MongoDB 연결 성공: {db_name}")
            except Exception as e:
                print(f"MongoDB 연결 실패: {e}")
                raise


    def extract_match_features(self, limit: int = None) -> pd.DataFrame:
        """
        MongoDB에서 데이터 불러와서 feature 생성

        Args:
            limit: 가져올 매치 개수 제한 (None이면 전체)

        Returns:
            플레이어별 특징을 담은 DataFrame
        """
        query = {
            'info.gameMode': 'ARAM',
            'info.gameDuration': {'$gte': 300}      # 5분 이상 게임만
        }

        projection = {
            'metadata.matchId': 1,
            'info.gameDuration': 1,
            'info.gameVersion': 1,
            'info.participants': 1,
            'info.teams': 1
        }

        cursor = self.matches_collection.find(query, projection)
        if limit:
            cursor = cursor.limit(limit)

        all_player_data = []

        for match in cursor:
            match_id = match['metadata']['matchId']
            game_duration_min = match['info']['gameDuration'] / 60

            # 팀별 사망 데이터
            team_deaths = {}
            for participant in match['info']['participants']:
                team_id = participant['teamId']
                if team_id not in team_deaths:
                    team_deaths[team_id] = 0
                team_deaths[team_id] += participant['deaths']

            # 각 플레이어별 데이터 추출
            for participant in match['info']['participants']:
                player_features = FeatureFactory.extract_player_features(
                    participant,
                    game_duration_min,
                    match_id,
                    team_deaths
                )
                all_player_data.append(player_features)

        return pd.DataFrame(all_player_data)
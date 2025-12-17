import os
from pyexpat import features

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

        # KDA
        kills = participant['kills']
        deaths = participant['deaths']
        assists = participant['assists']

        kda = (kills + assists) / max(deaths, 1)

        # 총 딜량
        total_damage = participant['totalDamageDealtToChampions']
        total_gold = participant['goldEarned']

        # 분당 지표
        dpm = total_damage / game_duration
        gpm = total_gold / game_duration

        # 참여율 및 효율성 지표
        kill_participation = participant['challenges'].get('killParticipation', 0)

        features = {
            'match_id': match_id,
            # 'map_id'
            'puuid': participant['puuid'],
            'champion': participant['championName'],
            'win': participant['win'],

            # 핵심 전투 지표
            'kda': kda,
            'kills': kills,
            'deaths': deaths,
            'assists': assists,

            # 피해량 지표
            'damage_per_min': dpm,          # DPM
            'damage_taken_per_min': participant['totalDamageTaken'] / game_duration,            # 받은 데미지 (탱킹)
            'damage_mitigated_per_min': participant['damageSelfMitigated'] / game_duration,         # 감소시킨 데미지 (방마저)
            'total_damage_share': participant['challenges'].get('teamDamagePercentage', 0),         # 데미지 비중

            # 골드 및 CS
            'gold_per_min': gpm,
            'cs_per_min': participant['totalMinionsKilled'] / game_duration,        # CS

            # 유틸리티 지표
            'cc_time': participant.get('timeCCingOthers', 0),       # CC
        'heal_shield_given': participant['totalHealsOnTeammates'] + participant['totalDamageShieldedOnTeammates'],          # 회복, 보호막

            # ARAM 특화 지표
            'kill_participation': kill_participation,           # 킬 관여율
            'longest_time_alive': participant['longestTimeSpentLiving'],            # 최장 생존 시간

            # 아이템 효율성
            'items_purchased': participant['itemsPurchased'],           # 아이템 산 개수 -> 얼마나 잘 컸는지
            'gold_efficiency': (dpm + participant['totalDamageTaken'] / game_duration) / gpm if gpm > 0 else 0,         # 게임 내내 얼마나 딜 잘했는지

            # 스킬 관련
            'skill_shots_hit': participant['challenges'].get('skillshotsHit', 0),           # 스킬샷 맞춘 비율
            'skill_shots_dodged': participant['challenges'].get('skillshotsDodged', 0),         # 스킬샷 못 맞춘 비율

            # 게임 메타 정보
            'game_duration': game_duration,
            'timestamp': datetime.now()
        }

        return features

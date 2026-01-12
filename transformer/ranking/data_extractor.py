import os
import json

import pymongo
import pandas as pd
import numpy as np
from typing import List, Dict, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def extract_player_features(participant: Dict, game_duration: float, match_id: str, team_deaths: Dict = None) -> Dict:
    """
    플레이어 주요 지표 추출

    Args:
        participant: 플레이어 데이터 딕셔너리
        game_duration: 게임 진행 시간 (분)
        match_id: 매치 ID
        team_deaths: 팀별 사망 횟수 딕셔너리

    Returns:
        플레이어 특징을 담은 딕셔너리
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
    challenges = participant.get('challenges', {})
    kill_participation = challenges.get('killParticipation', 0)

    # death_share 계산
    team_id = participant.get('teamId', 100)
    death_share = 0
    if team_deaths and team_id in team_deaths:
        death_share = deaths / max(team_deaths[team_id], 1)

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
        'total_damage_share': challenges.get('teamDamagePercentage', 0),         # 데미지 비중

        # 골드 및 CS
        'gold_per_min': gpm,
        'cs_per_min': participant['totalMinionsKilled'] / game_duration,        # CS

        # 유틸리티 지표
        'cc_time': participant.get('timeCCingOthers', 0),       # CC
        'heal_shield_given': participant['totalHealsOnTeammates'] + participant['totalDamageShieldedOnTeammates'],          # 회복, 보호막

        # ARAM 특화 지표
        'kill_participation': kill_participation,           # 킬 관여율
        'death_share': death_share,                         # 팀 내 데스 비중
        'longest_time_alive': participant['longestTimeSpentLiving'],            # 최장 생존 시간

        # 아이템 효율성
        'items_purchased': participant['itemsPurchased'],           # 아이템 산 개수 -> 얼마나 잘 컸는지
        'gold_efficiency': (dpm + participant['totalDamageTaken'] / game_duration) / gpm if gpm > 0 else 0,         # 게임 내내 얼마나 딜 잘했는지

        # 스킬 관련
        'skill_shots_hit': challenges.get('skillshotsHit', 0),           # 스킬샷 맞춘 비율
        'skill_shots_dodged': challenges.get('skillshotsDodged', 0),         # 스킬샷 못 맞춘 비율

        # 게임 메타 정보
        'game_duration': game_duration,
        'timestamp': datetime.now()
    }

    return features


def calculate_performance_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    라벨링(y) - 성능 점수 및 순위 계산

    Args:
        df: 플레이어 특징 DataFrame

    Returns:
        성능 점수(performance_score)와 순위(rank_in_match)가 추가된 DataFrame
    """
    def score_player(row):
        score = (
            row['kda'] * 0.25 +                         # kda (25%)
            row['damage_per_min'] / 1000 * 0.20 +       # dpm (20%), normal 1000
            row['kill_participation'] * 0.15 +          # 킬 관여율 (15%)
            row['gold_per_min'] / 500 * 0.10 +          # 골드 획득량 (10%), normal 500
            (1 - row['death_share']) * 0.15 +           # 팀 내 데스 비중. 생존률 (15%)
            row['gold_efficiency'] * 0.15               # 골드 효율 (15%)
        )

        # 승리 시 추가 점수
        if row['win']:
            score *= 1.1

        return score

    df['performance_score'] = df.apply(score_player, axis=1)

    df['rank_in_match'] = df.groupby('match_id')['performance_score'].rank(
        method='min',
        ascending=False
    )

    return df


def extract_match_features_from_json(json_file_path: str) -> pd.DataFrame:
    """
    JSON 파일에서 데이터 불러와서 feature 생성

    Args:
        json_file_path: JSON 파일 경로

    Returns:
        플레이어별 특징을 담은 DataFrame
    """
    with open(json_file_path, 'r', encoding='utf-8') as f:
        match = json.load(f)

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
    all_player_data = []
    for participant in match['info']['participants']:
        player_features = extract_player_features(
            participant,
            game_duration_min,
            match_id,
            team_deaths
        )
        all_player_data.append(player_features)

    return pd.DataFrame(all_player_data)


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
                player_features = extract_player_features(
                    participant,
                    game_duration_min,
                    match_id,
                    team_deaths
                )
                all_player_data.append(player_features)

        return pd.DataFrame(all_player_data)
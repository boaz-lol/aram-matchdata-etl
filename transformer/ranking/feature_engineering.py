from typing import Tuple

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.model_selection import train_test_split
import joblib

class FeatureEngineer:
    def __init__(self):
        self.scaler = RobustScaler()
        self.champion_encoder = {}
        self.feature_columns = None
        self.clip_values = {}

    def prepare_features(self, df: pd.DataFrame, is_train: bool = True) -> Tuple[np.ndarray, np.ndarray]:
        """
        ML 모델링을 위한 feature 준비
        """

        # 챔피언 원핫인코딩
        df = self.encode_champions(df, is_train=is_train)

        # 파생 feature 생성
        df = self.create_derived_features(df, is_train=is_train)

        # 학습에 쓸 feature 선택
        feature_cols = [
            'champion_id', 'kda', 'kills', 'deaths', 'assists',

            # 피해량
            'damage_per_min', 'damage_taken_per_min',
            'damage_mitigated_per_min', 'total_damage_share',

            # 골드 및 효율성
            'gold_per_min', 'cs_per_min', 'gold_efficiency',

            # 유틸리티
            'cc_time', 'heal_shield_given',

            # 참여도
            'kill_participation', 'death_share',
            'longest_time_alive',

            # 스킬
            'skill_shots_hit', 'skill_shots_dodged',

            # 파생 특징
            'aggression_index', 'survival_index',
            'team_contribution', 'combat_efficiency'
        ]

        self.feature_columns = feature_cols

        x = df[feature_cols].values
        y = df['performance_score'].values

        return x, y


    def create_derived_features(self, df: pd.DataFrame, is_train: bool = True) -> pd.DataFrame:
        """
        파생 feature 생성
        """

        # 공격성
        df['aggression_index'] = (
            df['kills'] + df['assists'] * 0.5
        ) / df['game_duration']

        # 생존력
        df['survival_index'] = df['longest_time_alive'] / (df['game_duration'] * 60)

        # 팀 기여도
        df['team_contribution'] = (
            df['kill_participation'] * 0.4 +
            df['total_damage_share'] * 0.4 +
            (1 - df['death_share']) * 0.2
        )

        # 교전력
        df['combat_efficiency'] = (
            df['damage_per_min'] / df['damage_taken_per_min'].replace(0, 1)
        )

        # 이상치 제거
        for col in ['kda', 'damage_per_min', 'gold_per_min']:
            if is_train:
                q1 = df[col].quantile(0.01)
                q99 = df[col].quantile(0.99)
                self.clip_values[col] = (q1, q99)
            else:
                q1, q99 = self.clip_values[col]

            df[col] = df[col].clip(q1, q99)

        return df

    def encode_champions(self, df: pd.DataFrame, is_train: bool = True) -> pd.DataFrame:
        """
        챔피언을 숫자로 인코딩
        """
        if is_train:
            unique_champions = df['champion'].unique()
            self.champion_encoder = {
                champ: idx for idx, champ in enumerate(unique_champions)
            }

        df['champion_id'] = df['champion'].map(self.champion_encoder)

        # 인식되지 않은 챔피언은 -1로 처리
        df['champion_id'].fillna(-1, inplace=True)

        return df

    def train_test_split_by_match(self, df, test_size: float = 0.2) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        매치 단위로 train/test 분할. leakage 방지용
        """
        unique_matches = df['match_id'].unique()
        train_matches, test_matches = train_test_split(
            unique_matches, test_size=test_size, random_state=42
        )

        train_df = df[df['match_id'].isin(train_matches)].copy()
        test_df = df[df['match_id'].isin(test_matches)].copy()

        return train_df, test_df

    def fit_transform(self, X: np.ndarray) -> np.ndarray:
        """
        학습 데이터 정규화
        """
        return self.scaler.fit_transform(X)

    def transform(self, X: np.ndarray) -> np.ndarray:
        """
        테스트 데이터 정규화
        """
        return self.scaler.transform(X)

    def save_preprocessors(self, path: str = './models/'):
        joblib.dump(self.scaler, f'{path}scaler.pkl')
        joblib.dump(self.champion_encoder, f'{path}champion_encoder.pkl')
        joblib.dump(self.feature_columns, f'{path}feature_columns.pkl')
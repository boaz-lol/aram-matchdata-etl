import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, ExtraTreesRegressor
import xgboost as xgb
import lightgbm as lgb
from sklearn.model_selection import cross_val_score
from typing import Dict, List, Optional
import joblib
import os

class EnsembleRanker:
    def __init__(self):
        """
        앙상블 랭킹 모델 (XGBoost, LightGBM, RandomForest, ExtraTrees, GBM)
        """
        self.models = {
            'xgb': xgb.XGBRegressor(
                n_estimators=200,
                learning_rate=0.05,
                max_depth=6,
                min_child_weight=3,
                subsample=0.8,
                colsample_bytree=0.8,
                objective='reg:squarederror',
                random_state=42
            ),

            'lgb': lgb.LGBMRegressor(
                n_estimators=200,
                learning_rate=0.05,
                num_leaves=31,
                min_child_samples=20,
                subsample=0.8,
                colsample_bytree=0.8,
                reg_alpha=0.1,
                reg_lambda=0.1,
                random_state=42
            ),

            'rf': RandomForestRegressor(
                n_estimators=200,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                max_features='sqrt',
                random_state=42,
                n_jobs=-1
            ),

            'extra_trees': ExtraTreesRegressor(
                n_estimators=200,
                max_depth=10,
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                n_jobs=-1
            ),

            'gbm': GradientBoostingRegressor(
                n_estimators=200,
                learning_rate=0.05,
                max_depth=5,
                min_samples_split=5,
                min_samples_leaf=2,
                subsample=0.8,
                random_state=42
            )
        }

        # 모델 가중치 (CV로 결정)
        self.weights = None
        self.is_trained = False


    def train(self,
              X_train: np.ndarray,
              y_train: np.ndarray,
              X_val: Optional[np.ndarray] = None,
              y_val: Optional[np.ndarray] = None
              ):
        """
        앙상블 모델 학습

        Args:
            X_train: 학습 데이터 특징
            y_train: 학습 데이터 타겟
            X_val: 검증 데이터 특징 (early stopping용)
            y_val: 검증 데이터 타겟 (early stopping용)
        """
        # 각 모델별 train/val
        model_scores = {}

        # 모델 성능 평가(CV)
        for name, model in self.models.items():
            cv_scores = cross_val_score(
                model, X_train, y_train,
                cv=5, scoring='neg_mean_squared_error',
                n_jobs=-1
            )
            model_scores[name] = -np.mean(cv_scores)
            print(f"{name} CV MSE: {model_scores[name]:.4f}")

        # 가중치 계산
        self.calculate_weight(model_scores)

        # 전체 데이터로 최종 학습
        for name, model in self.models.items():
            if name == 'xgb' and X_val is not None:
                # XGBoost
                model.fit(
                    X_train, y_train,
                    eval_set=[(X_val, y_val)],
                    verbose=False
                )
            elif name == 'lgb' and X_val is not None:
                # LightGBM
                model.fit(
                    X_train, y_train,
                    eval_set=[(X_val, y_val)],
                    callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)]
                )
            else:
                model.fit(X_train, y_train)

            print(f"{name} 학습 완료")

        self.is_trained = True


    def calculate_weight(self, scores: Dict[str, float]):
        """
        모델 성능 기반 가중치 계산

        Args:
            scores: 모델별 MSE 점수 딕셔너리
        """
        # 역수로 MSE 점수 직관화
        inverse_scores = {k: 1/v for k, v in scores.items()}

        # 정규화
        total = sum(inverse_scores.values())
        self.weights = {k: v/total for k, v in inverse_scores.items()}


    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        앙상블 예측

        Args:
            X: 예측할 데이터 특징

        Returns:
            예측된 성능 점수 배열
        """
        if not self.is_trained:
            raise ValueError("모델이 아직 학습되지 않았습니다!")

        predictions = {}

        # 모델별 예측값 수집
        for name, model in self.models.items():
            predictions[name] = model.predict(X)

        # 가중 평균으로 최종 점수 계산
        final_scores = np.zeros(len(X))
        for name, pred in predictions.items():
            final_scores += self.weights[name] * pred

        return final_scores


    def predict_rankings(self, X: np.ndarray, match_ids: Optional[np.ndarray] = None) -> Dict[str, np.ndarray]:
        """
        점수 -> 순위 (매치별)

        Args:
            X: 예측할 데이터 특징
            match_ids: 매치 ID 배열 (None이면 전체를 하나의 그룹으로 순위 계산)

        Returns:
            {'rankings': 순위 배열, 'scores': 점수 배열}
        """
        scores = self.predict(X)

        if match_ids is None:
            rankings = self.scores_to_ranks(scores)
            return {'rankings': rankings, 'scores': scores}

        # 매치별 순위 계산
        unique_matches = np.unique(match_ids)
        rankings = np.zeros_like(scores)

        for match_id in unique_matches:
            mask = match_ids == match_id    # match 참여 인원만 뽑아내기
            match_scores = scores[mask]
            match_rankings = self.scores_to_ranks(match_scores)
            rankings[mask] = match_rankings

        return {'rankings': rankings, 'scores': scores}


    def scores_to_ranks(self, scores: np.ndarray) -> np.ndarray:
        """
        점수 -> 순위 (높은 점수 = 높은 순위 = 낮은 숫자)

        Args:
            scores: 점수 배열

        Returns:
            순위 배열 (1이 가장 높은 순위)
        """
        return (-scores).argsort().argsort() + 1


    def get_feature_importance(self, feature_names: Optional[List[str]] = None) -> pd.DataFrame:
        """
        특징 중요도 추출

        Args:
            feature_names: 특징 이름 리스트 (None이면 숫자 인덱스 사용)

        Returns:
            특징별 중요도를 담은 DataFrame (mean, std 컬럼 포함)
        """
        if not self.is_trained:
            raise ValueError("모델이 아직 학습되지 않았습니다!")

        importance_dict = {}

        for name, model in self.models.items():
            if hasattr(model, 'feature_importances_'):
                importance_dict[name] = model.feature_importances_

        importance_df = pd.DataFrame(importance_dict)

        # feature_names None이면 숫자 인덱스 사용
        if feature_names is not None:
            importance_df.index = feature_names

        importance_df['mean'] = importance_df.mean(axis=1)
        importance_df['std'] = importance_df.std(axis=1)

        return importance_df.sort_values('mean', ascending=False)


    def save_models(self, path: str = './models/'):
        """
        모델 저장

        Args:
            path: 모델을 저장할 디렉토리 경로
        """
        if not self.is_trained:
            raise ValueError("모델이 아직 학습되지 않았습니다!")

        os.makedirs(path, exist_ok=True)

        for name, model in self.models.items():
            joblib.dump(model, f'{path}ensemble_{name}.pkl')

        joblib.dump(self.weights, f'{path}ensemble_weights.pkl')
        print(f"모델이 {path}에 저장되었습니다.")


    def load_models(self, path: str = './models/'):
        """
        모델 로드

        Args:
            path: 모델이 저장된 디렉토리 경로
        """
        for name in self.models.keys():
            self.models[name] = joblib.load(f'{path}ensemble_{name}.pkl')

        self.weights = joblib.load(f'{path}ensemble_weights.pkl')
        self.is_trained = True
        print("모델을 성공적으로 로드했습니다.")
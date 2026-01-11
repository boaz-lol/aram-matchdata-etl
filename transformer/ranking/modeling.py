import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, ExtraTreesRegressor
import xgboost as xgb
import lightgbm as lgb
from sklearn.model_selection import cross_val_score
from typing import Dict


class EnsembleRanker:
    def __init__(self):
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

    def train(self, X_train: np.ndarray, y_train: np.ndarray, X_val: np.ndarray = None, y_val: np.ndarray = None):
        """
        앙상블 모델 학습
        """

        # 각 모델별 train/val
        model_scores = {}

        for name, model in self.models.items():
            if name in ['xgb', 'lgb'] and X_val is not None:
                # Early stopping
                if name == 'xgb':
                    model.fit(
                        X_train, y_train,
                        eval_set=[(X_val, y_val)],
                        early_stopping_rounds=50,
                        verbose=False
                    )
                else:   # lgb
                    model.fit(
                        X_train, y_train,
                        eval_set=[(X_val, y_val)],
                        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)]
                    )

            else:
                model.fit(X_train, y_train)

            # CV 점수 계산
            cv_scores = cross_val_score(
                model, X_train, y_train,
                cv=5, scoring='neg_mean_squared_error',
                n_jobs=-1
            )

            model_scores[name] = -np.mean(cv_scores)
            print(f"{name} MSE: {model_scores[name]:.4f}")

        # 가중치 계산
        self.calculate_weight(model_scores)
        self.is_trained = True

    def calculate_weight(self, scores: Dict[str, float]):
        """
        모델 성능 기반 가중치 계산
        """

        # 역수로 MSE 점수 직관화
        inverse_scores = {k: 1/v for k, v in scores.items()}

        # 정규화
        total = sum(inverse_scores)
        self.weights = {k: v/total for k, v in inverse_scores.items()}

    def predict(self, X: np.ndarray) -> np.ndarray:
        """
        앙상블 예측
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

    def predict_rankings(self, X: np.ndarray, match_ids: np.ndarray = None) -> Dict:
        """
        점수 -> 순위
        """
        scores = self.predict(X)

        if match_ids is None:
            rankings = (-scores).argsort().argsort() + 1    # 높은 점수 = 높은 순위 = 낮은 숫자
            return {'rankings': rankings, 'scores': scores}

        # 매치별 순위 계산
        unique_matches = np.unique(match_ids)
        rankings = np.zeros_like(scores)

        for match_id in unique_matches:
            mask = match_ids == match_id    # match 참여 인원만 뽑아내기
            match_scores = scores[mask]
            match_rankings = (-match_scores).argsort().argsort() + 1
            rankings[mask] = match_rankings

        return {'rankings': rankings, 'scores': scores}
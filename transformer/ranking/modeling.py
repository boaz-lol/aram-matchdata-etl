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






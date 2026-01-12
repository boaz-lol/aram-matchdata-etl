import os
import sys

# 프로젝트 루트를 sys.path에 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from transformer.ranking.data_extractor import MatchDataExtractor
from transformer.ranking.feature_factory import FeatureFactory
from transformer.ranking.modeling import EnsembleRanker
import numpy as np


def test_full_pipeline():
    """
    전체 파이프라인 테스트: 데이터 추출 -> 전처리 -> 학습 -> 예측
    """
    print("=" * 80)
    print("EnsembleRanker 전체 파이프라인 테스트")
    print("=" * 80)

    # 1. 데이터 추출
    print("\n[1단계] MongoDB에서 매치 데이터 추출 중...")
    extractor = MatchDataExtractor()
    df = extractor.extract_match_features(limit=100)  # 100개 매치
    print(f"  ✓ {len(df)}개 플레이어 데이터 추출 완료")
    print(f"  ✓ 매치 수: {df['match_id'].nunique()}개")

    # 2. 라벨링
    print("\n[2단계] 성능 점수 라벨링 중...")
    df = FeatureFactory.calculate_performance_labels(df)
    print(f"  ✓ 라벨링 완료")
    print(f"  ✓ 성능 점수 범위: {df['performance_score'].min():.2f} ~ {df['performance_score'].max():.2f}")

    # 3. Feature Engineering
    print("\n[3단계] Feature Engineering...")
    factory = FeatureFactory()

    # Train/Test 분할 (매치 단위)
    train_df, test_df = factory.train_test_split_by_match(df, test_size=0.2)
    print(f"  ✓ Train: {len(train_df)}명 ({train_df['match_id'].nunique()}개 매치)")
    print(f"  ✓ Test: {len(test_df)}명 ({test_df['match_id'].nunique()}개 매치)")

    # Feature 준비
    X_train, y_train = factory.prepare_features(train_df, is_train=True)
    X_test, y_test = factory.prepare_features(test_df, is_train=False)
    print(f"  ✓ Feature 개수: {X_train.shape[1]}개")

    # 정규화
    X_train_scaled = factory.fit_transform(X_train)
    X_test_scaled = factory.transform(X_test)
    print(f"  ✓ 정규화 완료")

    # Validation set 분리 (early stopping용)
    val_size = int(len(X_train_scaled) * 0.2)
    X_val = X_train_scaled[-val_size:]
    y_val = y_train[-val_size:]
    X_train_final = X_train_scaled[:-val_size]
    y_train_final = y_train[:-val_size]
    print(f"  ✓ Train: {len(X_train_final)}, Val: {len(X_val)}, Test: {len(X_test_scaled)}")

    # 4. 모델 학습
    print("\n[4단계] 앙상블 모델 학습 중...")
    print("-" * 80)
    ranker = EnsembleRanker()
    ranker.train(X_train_final, y_train_final, X_val, y_val)
    print("-" * 80)
    print("  ✓ 학습 완료")

    # 가중치 출력
    print("\n[모델 가중치]")
    for name, weight in ranker.weights.items():
        print(f"  {name:12}: {weight:.4f}")

    # 5. 예측 및 평가
    print("\n[5단계] 테스트 데이터 예측...")
    predictions = ranker.predict(X_test_scaled)
    print(f"  ✓ 예측 완료")

    # MSE 계산
    mse = np.mean((predictions - y_test) ** 2)
    rmse = np.sqrt(mse)
    mae = np.mean(np.abs(predictions - y_test))
    print(f"  ✓ MSE: {mse:.4f}")
    print(f"  ✓ RMSE: {rmse:.4f}")
    print(f"  ✓ MAE: {mae:.4f}")

    # 6. 순위 예측 테스트
    print("\n[6단계] 순위 예측 테스트...")
    match_ids = test_df['match_id'].values
    result = ranker.predict_rankings(X_test_scaled, match_ids)

    rankings_pred = result['rankings']
    scores_pred = result['scores']

    # 실제 순위 vs 예측 순위 비교
    test_df['predicted_rank'] = rankings_pred
    test_df['predicted_score'] = scores_pred

    # 랜덤으로 하나의 매치 선택
    sample_match = test_df['match_id'].iloc[0]
    sample_df = test_df[test_df['match_id'] == sample_match].copy()
    sample_df = sample_df.sort_values('rank_in_match')

    print(f"\n  샘플 매치: {sample_match}")
    print("  " + "-" * 76)
    print(f"  {'실제순위':^8} | {'예측순위':^8} | {'챔피언':^15} | "
          f"{'실제점수':^10} | {'예측점수':^10}")
    print("  " + "-" * 76)

    for _, row in sample_df.iterrows():
        print(f"  {int(row['rank_in_match']):^8} | {int(row['predicted_rank']):^8} | "
              f"{row['champion']:^15} | {row['performance_score']:^10.2f} | "
              f"{row['predicted_score']:^10.2f}")
    print("  " + "-" * 76)

    # 순위 정확도 계산
    rank_diff = np.abs(test_df['rank_in_match'] - test_df['predicted_rank'])
    print(f"\n  평균 순위 차이: {rank_diff.mean():.2f}")
    print(f"  순위 차이 중앙값: {rank_diff.median():.2f}")
    print(f"  정확히 맞춘 비율: {(rank_diff == 0).mean() * 100:.1f}%")
    print(f"  ±1 이내 비율: {(rank_diff <= 1).mean() * 100:.1f}%")
    print(f"  ±2 이내 비율: {(rank_diff <= 2).mean() * 100:.1f}%")

    # 7. Feature Importance
    print("\n[7단계] Feature Importance...")
    importance_df = ranker.get_feature_importance(factory.feature_columns)
    print("\n  Top 10 중요 특징:")
    print(importance_df.head(10)[['mean', 'std']].to_string())

    # 8. 모델 저장 테스트
    print("\n[8단계] 모델 저장 테스트...")
    test_model_path = './test_models/'
    ranker.save_models(test_model_path)
    print(f"  ✓ 모델 저장 완료: {test_model_path}")

    # 9. 모델 로드 테스트
    print("\n[9단계] 모델 로드 테스트...")
    new_ranker = EnsembleRanker()
    new_ranker.load_models(test_model_path)
    print(f"  ✓ 모델 로드 완료")

    # 로드한 모델로 예측
    predictions_loaded = new_ranker.predict(X_test_scaled)
    prediction_diff = np.abs(predictions - predictions_loaded)
    print(f"  ✓ 예측 일치 검증: 최대 차이 = {prediction_diff.max():.10f}")

    print("\n" + "=" * 80)
    print("모든 테스트 완료! ✓")
    print("=" * 80)

    return ranker, test_df


def main():
    try:
        ranker, test_df = test_full_pipeline()
        return ranker, test_df

    except Exception as e:
        print(f"\n에러 발생: {e}")
        import traceback
        traceback.print_exc()
        return None, None


if __name__ == "__main__":
    main()
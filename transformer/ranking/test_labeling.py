import os
import sys

# 프로젝트 루트를 sys.path에 추가
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from transformer.ranking.data_extractor import MatchDataExtractor
from transformer.ranking.feature_factory import FeatureFactory


def test_single_match():
    extractor = MatchDataExtractor()

    df = extractor.extract_match_features(limit=1)
    print(f"\n데이터 shape: {df.shape}")
    print(f"플레이어 수: {len(df)}")

    print(f"\n컬럼 목록 ({len(df.columns)}개):")
    for i, col in enumerate(df.columns, 1):
        print(f"  {i:2}. {col}")

    print("\n주요 컬럼 데이터 타입:")
    main_cols = ['match_id', 'champion', 'win', 'kda', 'damage_per_min',
                 'gold_per_min', 'kill_participation', 'death_share']
    for col in main_cols:
        if col in df.columns:
            print(f"  {col:25} : {df[col].dtype}")

    print("\n첫 번째 플레이어 데이터:")
    first_player = df.iloc[0]
    important_features = [
        'champion', 'win', 'kda', 'kills', 'deaths', 'assists',
        'damage_per_min', 'gold_per_min', 'kill_participation', 'death_share'
    ]
    for feature in important_features:
        if feature in first_player.index:
            value = first_player[feature]
            if isinstance(value, float):
                print(f"  {feature:25} : {value:.2f}")
            else:
                print(f"  {feature:25} : {value}")

    print("\n플레이어 요약 (10명):")
    summary_cols = ['champion', 'kda', 'damage_per_min', 'gold_per_min',
                    'kill_participation', 'death_share', 'win']

    if all(col in df.columns for col in summary_cols):
        summary_df = df[summary_cols].copy()
        # 소수점 포맷팅
        for col in ['kda', 'damage_per_min', 'gold_per_min', 'kill_participation', 'death_share']:
            if col in summary_df.columns:
                summary_df[col] = summary_df[col].apply(lambda x: f"{x:.2f}")
        print(summary_df.to_string(index=False))

    return df


def test_labeling(df):
    df_labeled = FeatureFactory.calculate_performance_labels(df)

    df_sorted = df_labeled.sort_values('rank_in_match')

    print("\n최종 순위:")
    print("-" * 100)
    print(f"{'순위':^6} | {'챔피언':^15} | {'승패':^4} | {'KDA':^7} | "
          f"{'DPM':^8} | {'킬관여율':^8} | {'데스비중':^8} | {'점수':^7}")
    print("-" * 100)

    for idx, row in df_sorted.iterrows():
        win_status = "승" if row['win'] else "패"
        print(f"{int(row['rank_in_match']):^6} | {row['champion']:^15} | {win_status:^4} | "
              f"{row['kda']:>7.2f} | {row['damage_per_min']:>8.1f} | "
              f"{row['kill_participation']:>8.2f} | {row['death_share']:>8.2f} | "
              f"{row['performance_score']:>7.2f}")

    print("-" * 100)

    print("\n승패별 평균 순위:")
    win_avg_rank = df_labeled[df_labeled['win'] == True]['rank_in_match'].mean()
    lose_avg_rank = df_labeled[df_labeled['win'] == False]['rank_in_match'].mean()
    print(f"  승리 팀 평균 순위: {win_avg_rank:.2f}")
    print(f"  패배 팀 평균 순위: {lose_avg_rank:.2f}")

    print("\n팀별 순위 분포:")
    for team_win in [True, False]:
        team_name = "승리 팀" if team_win else "패배 팀"
        team_ranks = df_labeled[df_labeled['win'] == team_win]['rank_in_match'].values
        print(f"  {team_name}: {sorted([int(r) for r in team_ranks])}")

    print("\n누락값 확인:")
    null_counts = df_labeled.isnull().sum()
    if null_counts.any():
        print("  누락값 발견:")
        print(null_counts[null_counts > 0])
    else:
        print("  누락값 없음 ✓")

    return df_labeled


def main():
    try:
        # 1. MongoDB에서 매치 데이터 1개 추출 및 feature 생성
        df = test_single_match()

        # 2. 라벨링(순위 계산) 테스트
        df_labeled = test_labeling(df)

        print("\n" + "=" * 80)
        print("모든 테스트 완료! ✓")
        print("=" * 80)

        return df_labeled

    except Exception as e:
        print(f"\n에러 발생: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == "__main__":
    main()
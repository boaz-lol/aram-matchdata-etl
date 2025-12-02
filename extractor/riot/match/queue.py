from typing import Optional
from db.redis import BaseRedisQueue


class MatchIdQueue(BaseRedisQueue):
    """Match ID 전용 Redis 큐 (중복 제거)"""

    def __init__(self):
        super().__init__(
            queue_key="match_id_queue",
            set_key="match_id_set"
        )

    def add_match_id(self, match_id: str) -> bool:
        """
        match_id를 큐에 추가 (중복 제거)

        Args:
            match_id: 추가할 match_id

        Returns:
            bool: 추가 성공 여부 (이미 존재하면 False)
        """
        # match_id는 영구 중복 제거 (TTL 없음)
        return self.add(match_id)

    def get_match_id(self) -> Optional[str]:
        """
        큐에서 match_id를 가져옴 (FIFO)

        Returns:
            Optional[str]: 가져온 match_id, 큐가 비어있으면 None
        """
        return self.get()
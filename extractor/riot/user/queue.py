from typing import Optional
from db.redis import BaseRedisQueue


class UserIdQueue(BaseRedisQueue):
    """User ID 전용 Redis 큐 (중복 제거 + TTL 지원)"""

    def __init__(self):
        super().__init__(
            queue_key="user_id_queue",
            set_key="user_id_set"
        )

    def add_user_id(self, user_id: str, ttl: Optional[int] = None) -> bool:
        """
        user_id를 큐에 추가 (중복 제거)

        Args:
            user_id: 추가할 user_id
            ttl: TTL in seconds (None이면 영구 중복 제거)

        Returns:
            bool: 추가 성공 여부 (이미 존재하면 False)
        """
        return self.add(user_id, ttl)

    def get_user_id(self) -> Optional[str]:
        """
        큐에서 user_id를 가져옴 (FIFO)

        Returns:
            Optional[str]: 가져온 user_id, 큐가 비어있으면 None
        """
        return self.get()


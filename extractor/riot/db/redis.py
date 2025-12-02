import os
import redis
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class BaseRedisQueue:
    """Redis LIST + SET을 사용한 FIFO 큐 Base 클래스 (중복 제거 + TTL 지원)"""

    def __init__(self, queue_key: str, set_key: str):
        """
        Redis 큐 초기화

        Args:
            queue_key: Redis LIST 키 이름
            set_key: Redis SET 키 이름 (중복 제거용)
        """
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_db = int(os.getenv("REDIS_DB", 0))
        redis_password = os.getenv("REDIS_PASSWORD")

        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            password=redis_password,
            decode_responses=True
        )

        self.queue_key = queue_key
        self.set_key = set_key

    def add(self, item: str, ttl: Optional[int] = None) -> bool:
        """
        아이템을 큐에 추가 (중복 제거)

        Args:
            item: 추가할 아이템
            ttl: TTL in seconds (None이면 TTL 없음, 영구 중복 제거)

        Returns:
            bool: 추가 성공 여부 (이미 존재하면 False)
        """
        # TTL이 지정된 경우, TTL 추적 키 체크
        if ttl is not None:
            ttl_key = f"{self.set_key}:ttl:{item}"
            if self.redis_client.exists(ttl_key):
                # TTL 키가 존재하면 아직 만료되지 않음 (중복)
                return False

        # SET에 추가 시도 (중복 확인)
        added = self.redis_client.sadd(self.set_key, item)

        if added:
            # SET에 추가 성공 시 LIST에도 추가
            self.redis_client.lpush(self.queue_key, item)

            # TTL이 지정된 경우, TTL 추적 키 생성
            if ttl is not None:
                ttl_key = f"{self.set_key}:ttl:{item}"
                self.redis_client.setex(ttl_key, ttl, "1")

            return True

        return False

    def get(self) -> Optional[str]:
        """
        큐에서 아이템을 가져옴 (FIFO)

        Returns:
            Optional[str]: 가져온 아이템, 큐가 비어있으면 None
        """
        # LIST에서 오른쪽에서 가져오기 (FIFO)
        item = self.redis_client.rpop(self.queue_key)

        if item:
            # SET에서도 제거
            self.redis_client.srem(self.set_key, item)

            # TTL 추적 키가 존재하면 삭제
            ttl_key = f"{self.set_key}:ttl:{item}"
            self.redis_client.delete(ttl_key)

            return item

        return None

    def queue_size(self) -> int:
        """
        큐의 크기 반환

        Returns:
            int: 큐에 있는 아이템 개수
        """
        return self.redis_client.llen(self.queue_key)

    def set_size(self) -> int:
        """
        SET의 크기 반환 (중복 제거된 전체 개수)

        Returns:
            int: SET에 있는 아이템 개수
        """
        return self.redis_client.scard(self.set_key)

    def clear(self):
        """큐와 SET 모두 초기화"""
        self.redis_client.delete(self.queue_key)
        self.redis_client.delete(self.set_key)

        # TTL 추적 키도 모두 삭제 (패턴 매칭)
        ttl_pattern = f"{self.set_key}:ttl:*"
        ttl_keys = self.redis_client.keys(ttl_pattern)
        if ttl_keys:
            self.redis_client.delete(*ttl_keys)

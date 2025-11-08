import os
import redis
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class UserIdQueue:
    """Redis LIST + SET을 사용한 FIFO 큐 (중복 제거)"""
    
    def __init__(self):
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
        
        self.queue_key = "user_id_queue"
        self.set_key = "user_id_set"
    
    def add_user_id(self, user_id: str) -> bool:
        """
        user_id를 큐에 추가 (중복 제거)
        
        Args:
            user_id: 추가할 user_id
            
        Returns:
            bool: 추가 성공 여부 (이미 존재하면 False)
        """
        # SET에 추가 시도 (중복 확인)
        added = self.redis_client.sadd(self.set_key, user_id)
        
        if added:
            # SET에 추가 성공 시 LIST에도 추가
            self.redis_client.lpush(self.queue_key, user_id)
            return True
        return False
    
    def get_user_id(self) -> Optional[str]:
        """
        큐에서 user_id를 가져옴 (FIFO)
        
        Returns:
            Optional[str]: 가져온 user_id, 큐가 비어있으면 None
        """
        # LIST에서 오른쪽에서 가져오기 (FIFO)
        user_id = self.redis_client.rpop(self.queue_key)
        
        if user_id:
            # SET에서도 제거
            self.redis_client.srem(self.set_key, user_id)
            return user_id
        return None
    
    def queue_size(self) -> int:
        """
        큐의 크기 반환
        
        Returns:
            int: 큐에 있는 user_id 개수
        """
        return self.redis_client.llen(self.queue_key)
    
    def set_size(self) -> int:
        """
        SET의 크기 반환 (중복 제거된 전체 개수)
        
        Returns:
            int: SET에 있는 user_id 개수
        """
        return self.redis_client.scard(self.set_key)
    
    def clear(self):
        """큐와 SET 모두 초기화"""
        self.redis_client.delete(self.queue_key)
        self.redis_client.delete(self.set_key)


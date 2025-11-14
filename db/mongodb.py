import os
from typing import Dict, Any, Optional
from pymongo import MongoClient
from pymongo.collection import Collection
from pymongo.database import Database
from dotenv import load_dotenv

load_dotenv()


class MongoDBClient:
    """MongoDB 연결 및 match 데이터 저장을 위한 클래스"""
    
    def __init__(self):
        mongo_url = os.getenv("MONGO_DB_URL")
        
        if not mongo_url:
            raise ValueError("MONGO_DB_URL environment variable is not set")
        
        self.client = MongoClient(mongo_url)
        self.db: Database = self.client.get_database("lp-db")
        self.collection_name = "match"
        self.collection: Collection = self.db[self.collection_name]
        self.timeline_collection_name = "match_detail"
        self.timeline_collection: Collection = self.db[self.timeline_collection_name]
    
    def save_match(self, match_detail: Dict[str, Any]) -> bool:
        """
        match 상세 데이터를 MongoDB에 저장 (upsert)
        
        Args:
            match_detail: Riot API에서 가져온 match 상세 데이터
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            # match_id를 _id로 사용
            match_id = match_detail.get("metadata", {}).get("matchId")
            
            if not match_id:
                print("Warning: match_detail에 matchId가 없습니다.")
                return False
            
            # _id 필드에 match_id 설정하고 나머지 데이터 저장
            document = {
                "_id": match_id,
                **match_detail
            }
            
            # upsert 실행 (이미 있으면 업데이트, 없으면 삽입)
            result = self.collection.replace_one(
                {"_id": match_id},
                document,
                upsert=True
            )
            
            if result.upserted_id or result.modified_count > 0:
                print(f"Match 데이터 저장 완료: {match_id}")
                return True
            else:
                print(f"Match 데이터 저장 실패 (변경 없음): {match_id}")
                return False
                
        except Exception as e:
            print(f"Error saving match to MongoDB: {str(e)}")
            return False
    
    def save_match_timeline(self, match_id: str, timeline_data: Dict[str, Any]) -> bool:
        """
        match timeline 데이터를 MongoDB의 match_detail 컬렉션에 저장 (upsert)
        
        Args:
            match_id: Riot API match_id
            timeline_data: Riot API에서 가져온 timeline 데이터
            
        Returns:
            bool: 저장 성공 여부
        """
        try:
            if not match_id:
                print("Warning: match_id가 없습니다.")
                return False
            
            # _id 필드에 match_id 설정하고 나머지 데이터 저장
            document = {
                "_id": match_id,
                **timeline_data
            }
            
            # upsert 실행 (이미 있으면 업데이트, 없으면 삽입)
            result = self.timeline_collection.replace_one(
                {"_id": match_id},
                document,
                upsert=True
            )
            
            if result.upserted_id or result.modified_count > 0:
                print(f"Match timeline 데이터 저장 완료: {match_id}")
                return True
            else:
                print(f"Match timeline 데이터 저장 실패 (변경 없음): {match_id}")
                return False
                
        except Exception as e:
            print(f"Error saving match timeline to MongoDB: {str(e)}")
            return False
    
    def close(self):
        """MongoDB 연결 종료"""
        self.client.close()


# 전역 인스턴스 (필요시 사용)
_mongodb_client: Optional[MongoDBClient] = None


def get_mongodb_client() -> MongoDBClient:
    """MongoDB 클라이언트 싱글톤 인스턴스 반환"""
    global _mongodb_client
    if _mongodb_client is None:
        _mongodb_client = MongoDBClient()
    return _mongodb_client


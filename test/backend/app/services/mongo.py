import logging
from typing import Optional, Dict, Any
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from app.core.config import settings

logger = logging.getLogger(__name__)

class MongoService:
    client: Optional[AsyncIOMotorClient] = None

    @classmethod
    def get_client(cls) -> AsyncIOMotorClient:
        if cls.client is None:
            cls.client = AsyncIOMotorClient(settings.MONGO_URI)
        return cls.client

    @classmethod
    def get_database(cls):
        client = cls.get_client()
        return client[settings.MONGO_DB]

    @classmethod
    async def save_raw_document(cls, collection_name: str, doc_data: Dict[str, Any]) -> str:
        """Сохранение сырого JSON после парсинга (резюме, вакансии)"""
        try:
            db = cls.get_database()
            result = await db[collection_name].insert_one(doc_data)
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"Error saving to MongoDB: {e}")
            return ""

    @classmethod
    async def get_raw_document(cls, collection_name: str, doc_id: str) -> Optional[Dict[str, Any]]:
        """Получение сырого документа по ID"""
        try:
            db = cls.get_database()
            doc = await db[collection_name].find_one({"_id": ObjectId(doc_id)})
            if doc:
                doc["_id"] = str(doc["_id"])
            return doc
        except Exception as e:
            logger.error(f"Error fetching from MongoDB: {e}")
            return None

    @classmethod
    async def close(cls):
        if cls.client is not None:
            cls.client.close()
            cls.client = None

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

class MemoryChunk(BaseModel):
    id: Optional[UUID] = None
    tenant_id: UUID
    conversation_id: UUID
    content: str
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = {}
    relevance_score: float = 0.0
    created_at: Optional[datetime] = None

class BaseMemory(ABC):
    @abstractmethod
    async def store(self, chunk: MemoryChunk) -> bool:
        pass

    @abstractmethod
    async def search(
        self, 
        tenant_id: UUID, 
        query: str, 
        limit: int = 5
    ) -> List[MemoryChunk]:
        pass

class BaseLearning(ABC):
    @abstractmethod
    async def extract_patterns(self, conversation_id: UUID, tenant_id: UUID) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def suggest_learning(self, patterns: List[Dict[str, Any]], tenant_id: UUID) -> bool:
        pass

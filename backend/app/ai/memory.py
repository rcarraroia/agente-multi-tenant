import json
from uuid import UUID
from typing import List, Dict, Any
import redis
from app.config import settings

class RedisMemoryManager:
    def __init__(self):
        self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        self.ttl = 86400  # 24 hours

    def _get_key(self, conversation_id: str) -> str:
        return f"agent:memory:{conversation_id}"

    def get_history(self, conversation_id: UUID) -> List[Dict[str, str]]:
        """
        Retrieves message history from Redis.
        Returns list of dicts: [{"role": "user", "content": "..."}, ...]
        """
        key = self._get_key(str(conversation_id))
        raw_data = self.redis_client.lrange(key, 0, -1)
        # Redis stores recent at right (append), so 0 is oldest.
        # We want context window.
        
        history = [json.loads(msg) for msg in raw_data]
        return history

    def add_message(self, conversation_id: UUID, role: str, content: str):
        """
        Adds a message to the history.
        """
        key = self._get_key(str(conversation_id))
        message = json.dumps({"role": role, "content": content})
        
        pipeline = self.redis_client.pipeline()
        pipeline.rpush(key, message)
        pipeline.expire(key, self.ttl)
        
        # Trim to max window size (e.g. 20 messages)
        # 0 is start, -1 is end. We want to keep last N.
        # ltrim key -N -1
        max_window = getattr(settings, "AGENT_MEMORY_WINDOW", 20)
        pipeline.ltrim(key, -max_window, -1)
        
        pipeline.execute()

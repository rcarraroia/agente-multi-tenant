from typing import List, Optional
from uuid import UUID
from app.db.supabase import get_supabase
from .interfaces import BaseMemory, MemoryChunk
from .embeddings import SICCEmbeddings
import logging

logger = logging.getLogger(__name__)

class MemoryEngine(BaseMemory):
    """
    Motor de Memória do SICC 2.0.
    Gerencia a persistência e busca de chunks no Supabase com isolamento de tenant.
    """
    def __init__(self):
        self.supabase = get_supabase()
        self.embeddings = SICCEmbeddings()

    async def store(self, chunk: MemoryChunk) -> bool:
        """Armazena um novo fragmento de memória no banco de dados."""
        try:
            # Se o embedding não foi passado, gera agora
            if not chunk.embedding:
                chunk.embedding = await self.embeddings.generate(chunk.content)

            data = {
                "tenant_id": str(chunk.tenant_id),
                "conversation_id": str(chunk.conversation_id),
                "content": chunk.content,
                "embedding": chunk.embedding,
                "metadata": chunk.metadata,
                "relevance_score": chunk.relevance_score
            }

            result = self.supabase.table("sicc_memory_chunks").insert(data).execute()
            return len(result.data) > 0
        except Exception as e:
            logger.error(f"Erro ao salvar memória SICC: {e}")
            return False

    async def search(
        self, 
        tenant_id: UUID, 
        query: str, 
        limit: int = 5,
        similarity_threshold: float = 0.1
    ) -> List[MemoryChunk]:
        """Busca memórias similares usando a função RPC híbrida do Supabase."""
        try:
            # 1. Gerar embedding da query
            query_embedding = await self.embeddings.generate(query)
            
            # 2. Chamar RPC híbrido
            result = self.supabase.rpc("search_sicc_memories_hybrid", {
                "p_tenant_id": str(tenant_id),
                "p_embedding": query_embedding,
                "p_query_text": query,
                "p_similarity_threshold": similarity_threshold,
                "p_max_results": limit
            }).execute()

            chunks = []
            for row in result.data:
                chunks.append(MemoryChunk(
                    id=row["id"],
                    tenant_id=tenant_id,
                    conversation_id=row["conversation_id"],
                    content=row["content"],
                    embedding=[], # Não retornamos o vetor na busca por eficiência
                    metadata=row["metadata"],
                    relevance_score=row["combined_score"],
                    created_at=row["created_at"]
                ))
            
            # 3. Registrar "boost" de relevância para as memórias encontradas (assíncrono)
            for chunk in chunks:
                self.supabase.rpc("update_sicc_memory_relevance", {
                    "p_tenant_id": str(tenant_id),
                    "p_memory_id": str(chunk.id),
                    "p_boost": 0.05
                }).execute()

            return chunks
        except Exception as e:
            logger.error(f"Erro na busca de memória SICC: {e}")
            return []

import asyncio
import numpy as np
import logging
from typing import List
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

class SICCEmbeddings:
    """
    Motor de Embeddings para SICC 2.0.
    Utiliza o modelo local all-MiniLM-L6-v2 (384 dimensões).
    """
    _model = None
    _lock = asyncio.Lock()
    model_name = "sentence-transformers/all-MiniLM-L6-v2"

    @classmethod
    async def get_model(cls) -> SentenceTransformer:
        if cls._model is None:
            async with cls._lock:
                if cls._model is None:
                    logger.info(f"Carregando modelo de embeddings: {cls.model_name}")
                    # Carregar modelo em thread separada para não travar o loop
                    loop = asyncio.get_event_loop()
                    cls._model = await loop.run_in_executor(
                        None, 
                        lambda: SentenceTransformer(cls.model_name)
                    )
        return cls._model

    async def generate(self, text: str) -> List[float]:
        """Gera o vetor de embedding para o texto fornecido."""
        if not text or not text.strip():
            return []

        model = await self.get_model()
        loop = asyncio.get_event_loop()
        
        # Gerar e normalizar
        embedding = await loop.run_in_executor(
            None,
            lambda: model.encode(text.strip())
        )
        
        # Normalização Coseno
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
            
        return embedding.tolist()

    async def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """Gera embeddings em lote."""
        if not texts:
            return []
            
        model = await self.get_model()
        loop = asyncio.get_event_loop()
        
        embeddings = await loop.run_in_executor(
            None,
            lambda: model.encode(texts)
        )
        
        return [ (e / np.linalg.norm(e)).tolist() if np.linalg.norm(e) > 0 else e.tolist() for e in embeddings]

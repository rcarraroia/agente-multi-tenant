"""
Serviço de Embeddings para Base de Conhecimento (RAG)
Responsável por:
1. Fazer parsing de documentos (PDF, TXT)
2. Chunking do texto
3. Gerar embeddings via OpenAI
4. Armazenar vetores no Supabase (pgvector)
"""

from uuid import UUID
from typing import List, Optional
import os

from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, TextLoader

from app.db.supabase import get_supabase
from app.config import settings


class EmbeddingService:
    def __init__(self, tenant_api_key: Optional[str] = None):
        # Usa chave do tenant se disponível, senão fallback para global
        api_key = tenant_api_key or settings.OPENAI_API_KEY
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=api_key
        )
        self.supabase = get_supabase()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        self.vectors_table = "multi_agent_embeddings"

    async def process_document(self, tenant_id: UUID, document_id: UUID, file_path: str, content_type: str) -> bool:
        """
        Processa um documento: extrai texto, divide em chunks, gera embeddings e armazena.
        Retorna True se sucesso, False se erro.
        """
        try:
            # 1. Atualizar status para 'processing'
            self._update_document_status(document_id, "processing")

            # 2. Baixar arquivo do Storage
            local_path = await self._download_from_storage(file_path)

            # 3. Carregar e extrair texto
            if content_type == "application/pdf":
                loader = PyPDFLoader(local_path)
            else:
                loader = TextLoader(local_path, encoding="utf-8")

            documents = loader.load()

            # 4. Dividir em chunks
            chunks = self.text_splitter.split_documents(documents)

            # 5. Gerar embeddings e armazenar
            for i, chunk in enumerate(chunks):
                embedding = self.embeddings.embed_query(chunk.page_content)
                
                self.supabase.table(self.vectors_table).insert({
                    "tenant_id": str(tenant_id),
                    "document_id": str(document_id),
                    "content": chunk.page_content,
                    "embedding": embedding,
                    "chunk_index": i,
                    "metadata": chunk.metadata
                }).execute()

            # 6. Atualizar status para 'completed'
            self._update_document_status(document_id, "completed")

            # 7. Limpar arquivo temporário
            os.remove(local_path)

            return True

        except Exception as e:
            # Atualizar status para 'failed' com mensagem de erro
            self._update_document_status(document_id, "failed", str(e))
            return False

    async def _download_from_storage(self, file_path: str) -> str:
        """Baixa arquivo do Supabase Storage para processamento local"""
        bucket = "tenant-documents"
        local_dir = "/tmp/documents"
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, os.path.basename(file_path))

        response = self.supabase.storage.from_(bucket).download(file_path)
        with open(local_path, "wb") as f:
            f.write(response)

        return local_path

    def _update_document_status(self, document_id: UUID, status: str, error_message: str = None):
        """Atualiza o status de processamento do documento"""
        update_data = {"status": status}
        if error_message:
            update_data["error_message"] = error_message

        self.supabase.table("multi_agent_documents")\
            .update(update_data)\
            .eq("id", str(document_id))\
            .execute()

    async def delete_embeddings_for_document(self, document_id: UUID):
        """Remove todos os embeddings de um documento"""
        self.supabase.table(self.vectors_table)\
            .delete()\
            .eq("document_id", str(document_id))\
            .execute()

    def search_similar(self, tenant_id: UUID, query: str, limit: int = 5) -> List[str]:
        """
        Busca vetores similares para uma query.
        Usado pelo RAG para responder perguntas.
        """
        query_embedding = self.embeddings.embed_query(query)

        # Usar função RPC do Supabase para buscar por similaridade
        # Requer extensão pgvector e função match_documents
        response = self.supabase.rpc(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "match_tenant_id": str(tenant_id),
                "match_count": limit
            }
        ).execute()

        return [r["content"] for r in response.data] if response.data else []

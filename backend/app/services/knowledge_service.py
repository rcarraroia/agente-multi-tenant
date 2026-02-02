from uuid import UUID
from typing import List
from app.db.supabase import get_supabase
from app.schemas.document import Document, DocumentCreate
from app.core.exceptions import EntityNotFoundException
import asyncio

class KnowledgeService:
    def __init__(self):
        self.supabase = get_supabase()
        self.table = "multi_agent_documents"
        self.bucket = "tenant-documents"

    async def upload_document(self, tenant_id: UUID, file_name: str, file_content: bytes, content_type: str) -> Document:
        # 1. Upload to Supabase Storage
        file_path = f"{tenant_id}/{file_name}"
        
        # storage.from_('bucket').upload(path, file)
        self.supabase.storage.from_(self.bucket).upload(
            path=file_path,
            file=file_content,
            file_options={"content-type": content_type}
        )

        # 2. Register in Database
        doc_in = DocumentCreate(
            tenant_id=tenant_id,
            name=file_name,
            file_path=file_path,
            content_type=content_type,
            size_bytes=len(file_content)
        )
        
        res = self.supabase.table(self.table)\
            .insert(doc_in.model_dump(mode='json'))\
            .execute()
        
        document = Document.model_validate(res.data[0])
        
        # 3. Disparar vetorização em background (não bloqueia o upload)
        asyncio.create_task(self._trigger_vectorization(tenant_id, document.id, file_path, content_type))
        
        return document

    async def _trigger_vectorization(self, tenant_id: UUID, document_id: UUID, file_path: str, content_type: str):
        """Dispara o processo de vetorização em background"""
        try:
            from app.services.embedding_service import EmbeddingService
            embedding_service = EmbeddingService()
            await embedding_service.process_document(tenant_id, document_id, file_path, content_type)
        except Exception as e:
            print(f"Erro na vetorização do documento {document_id}: {str(e)}")

    def list_documents(self, tenant_id: UUID) -> List[Document]:
        res = self.supabase.table(self.table)\
            .select("*")\
            .eq("tenant_id", str(tenant_id))\
            .order("created_at", desc=True)\
            .execute()
            
        return [Document.model_validate(d) for d in res.data]

    async def delete_document(self, tenant_id: UUID, document_id: UUID):
        # 1. Get doc details
        res = self.supabase.table(self.table)\
            .select("file_path")\
            .eq("id", str(document_id))\
            .eq("tenant_id", str(tenant_id))\
            .execute()
            
        if not res.data:
            raise EntityNotFoundException("Document not found")
            
        file_path = res.data[0]["file_path"]

        # 2. Delete from Storage
        self.supabase.storage.from_(self.bucket).remove([file_path])

        # 3. Delete from DB
        self.supabase.table(self.table)\
            .delete()\
            .eq("id", str(document_id))\
            .execute()
            
        # 4. TODO: Trigger deletion of related vector embeddings

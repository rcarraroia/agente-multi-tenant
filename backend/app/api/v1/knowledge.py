from typing import List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from app.api import deps
from app.schemas.tenant import Tenant
from app.services.knowledge_service import KnowledgeService
from app.schemas.document import Document
from app.api.deps import APIResponse

router = APIRouter()

@router.post("/upload", response_model=APIResponse)
async def upload_document(
    file: UploadFile = File(...),
    tenant: Tenant = Depends(deps.get_current_tenant),
    service: KnowledgeService = Depends(KnowledgeService)
):
    """
    Fazer upload de documento para a base de conhecimento.
    Protegido por: login + assinatura ativa.
    """
    content = await file.read()
    try:
        doc = await service.upload_document(
            tenant_id=tenant.id,
            file_name=file.filename,
            file_content=content,
            content_type=file.content_type
        )
        return APIResponse(data=doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no upload: {str(e)}")

@router.get("/", response_model=APIResponse)
def list_documents(
    tenant: Tenant = Depends(deps.get_current_tenant),
    service: KnowledgeService = Depends(KnowledgeService)
):
    docs = service.list_documents(tenant.id)
    return APIResponse(data=docs)

@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    tenant: Tenant = Depends(deps.get_current_tenant),
    service: KnowledgeService = Depends(KnowledgeService)
):
    try:
        await service.delete_document(tenant.id, document_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from uuid import UUID
from typing import Optional, List
from fastapi import HTTPException
from app.db.supabase import get_supabase
from app.schemas.crm import (
    FunnelCreate, FunnelUpdate, Funnel, FunnelWithStages,
    StageCreate, StageUpdate, Stage, StageReorderItem,
    MoveConversationRequest, StageHistoryCreate
)

class CRMService:
    def __init__(self):
        self.supabase = get_supabase()
        self.funnel_table = "crm_funnels"
        self.stage_table = "crm_stages"
        self.history_table = "crm_stage_history"
        self.conv_table = "multi_agent_conversations"

    # ========== FUNNELS ==========

    def create_funnel(self, tenant_id: UUID, data: FunnelCreate) -> Funnel:
        """Criar funil com validação de limite (máx 5)"""
        # Verificar limite de 5 funis
        funnels = self.supabase.table(self.funnel_table)\
            .select("id", count="exact")\
            .eq("tenant_id", str(tenant_id))\
            .execute()
        
        if funnels.count >= 5:
            raise HTTPException(
                status_code=409, 
                detail="Limite de 5 funis por inquilino atingido"
            )
        
        # Inserir
        insert_data = data.model_dump()
        insert_data["tenant_id"] = str(tenant_id)
        
        response = self.supabase.table(self.funnel_table)\
            .insert(insert_data)\
            .execute()
        
        if not response.data:
            raise HTTPException(status_code=500, detail="Erro ao criar funil")
            
        return Funnel.model_validate(response.data[0])

    def list_funnels(self, tenant_id: UUID) -> List[Funnel]:
        """Listar funis do inquilino"""
        response = self.supabase.table(self.funnel_table)\
            .select("*")\
            .eq("tenant_id", str(tenant_id))\
            .order("created_at")\
            .execute()
        
        return [Funnel.model_validate(f) for f in response.data]

    def get_funnel_with_stages(self, tenant_id: UUID, funnel_id: UUID) -> FunnelWithStages:
        """Buscar funil com todas as suas etapas"""
        # Buscar funil
        funnel_res = self.supabase.table(self.funnel_table)\
            .select("*")\
            .eq("id", str(funnel_id))\
            .eq("tenant_id", str(tenant_id))\
            .single()\
            .execute()
        
        if not funnel_res.data:
            raise HTTPException(status_code=404, detail="Funil não encontrado")
            
        funnel = funnel_res.data
        
        # Buscar etapas
        stages_res = self.supabase.table(self.stage_table)\
            .select("*")\
            .eq("funnel_id", str(funnel_id))\
            .order("position")\
            .execute()
            
        funnel_with_stages = FunnelWithStages.model_validate(funnel)
        funnel_with_stages.stages = [Stage.model_validate(s) for s in stages_res.data]
        
        return funnel_with_stages

    def update_funnel(self, tenant_id: UUID, funnel_id: UUID, data: FunnelUpdate) -> Funnel:
        """Atualizar campos do funil"""
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="Sem dados para atualizar")
            
        response = self.supabase.table(self.funnel_table)\
            .update(update_data)\
            .eq("id", str(funnel_id))\
            .eq("tenant_id", str(tenant_id))\
            .execute()
            
        if not response.data:
            raise HTTPException(status_code=404, detail="Funil não encontrado")
            
        return Funnel.model_validate(response.data[0])

    def delete_funnel(self, tenant_id: UUID, funnel_id: UUID, move_to_funnel_id: Optional[UUID] = None):
        """Deletar funil (impede se tiver conversas e move_to não fornecido)"""
        # Buscar funil
        funnel_res = self.supabase.table(self.funnel_table)\
            .select("*")\
            .eq("id", str(funnel_id))\
            .eq("tenant_id", str(tenant_id))\
            .single()\
            .execute()
            
        if not funnel_res.data:
            raise HTTPException(status_code=404, detail="Funil não encontrado")
            
        funnel = funnel_res.data
        
        # Proibir deletar funil padrão
        if funnel.get("is_default"):
            raise HTTPException(status_code=403, detail="Funil padrão não pode ser deletado")
            
        # Verificar se há conversas vinculadas
        conv_count = self.supabase.table(self.conv_table)\
            .select("id", count="exact")\
            .eq("funnel_id", str(funnel_id))\
            .execute()
            
        if conv_count.count > 0:
            if not move_to_funnel_id:
                raise HTTPException(
                    status_code=409, 
                    detail=f"Funil possui {conv_count.count} conversas. Forneça move_to_funnel_id para migrar."
                )
            
            # Migrar conversas para o novo funil (etapa 1 do novo funil)
            self._migrate_conversations_to_funnel(tenant_id, funnel_id, move_to_funnel_id)
            
        # Deletar funil (cascade delete apagará as etapas via FK)
        self.supabase.table(self.funnel_table)\
            .delete()\
            .eq("id", str(funnel_id))\
            .eq("tenant_id", str(tenant_id))\
            .execute()
            
        return {"status": "success", "message": "Funil deletado com sucesso"}

    def _migrate_conversations_to_funnel(self, tenant_id: UUID, from_id: UUID, to_id: UUID):
        """Migrar conversas entre funis (move para a primeira etapa do destino)"""
        # Buscar primeira etapa do funil de destino
        target_stage = self.supabase.table(self.stage_table)\
            .select("id")\
            .eq("funnel_id", str(to_id))\
            .order("position")\
            .limit(1)\
            .execute()
            
        if not target_stage.data:
            raise HTTPException(status_code=400, detail="Funil de destino não possui etapas")
            
        stage_id = target_stage.data[0]["id"]
        
        # Atualizar todas as conversas
        self.supabase.table(self.conv_table)\
            .update({
                "funnel_id": str(to_id),
                "stage_id": str(stage_id)
            })\
            .eq("funnel_id", str(from_id))\
            .eq("tenant_id", str(tenant_id))\
            .execute()

    # ========== STAGES ==========

    def create_stage(self, tenant_id: UUID, data: StageCreate) -> Stage:
        """Criar nova etapa no funil"""
        # Validar se funil existe e pertence ao tenant
        funnel_res = self.supabase.table(self.funnel_table)\
            .select("id")\
            .eq("id", str(data.funnel_id))\
            .eq("tenant_id", str(tenant_id))\
            .execute()
            
        if not funnel_res.data:
            raise HTTPException(status_code=404, detail="Funil não encontrado")
            
        insert_data = data.model_dump()
        insert_data["tenant_id"] = str(tenant_id)
        
        response = self.supabase.table(self.stage_table)\
            .insert(insert_data)\
            .execute()
            
        if not response.data:
            raise HTTPException(status_code=500, detail="Erro ao criar etapa")
            
        return Stage.model_validate(response.data[0])

    def list_stages(self, tenant_id: UUID, funnel_id: UUID) -> List[Stage]:
        """Listar etapas de um funil"""
        response = self.supabase.table(self.stage_table)\
            .select("*")\
            .eq("funnel_id", str(funnel_id))\
            .eq("tenant_id", str(tenant_id))\
            .order("position")\
            .execute()
            
        return [Stage.model_validate(s) for s in response.data]

    def update_stage(self, tenant_id: UUID, stage_id: UUID, data: StageUpdate) -> Stage:
        """Atualizar etapa"""
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="Sem dados para atualizar")
            
        response = self.supabase.table(self.stage_table)\
            .update(update_data)\
            .eq("id", str(stage_id))\
            .eq("tenant_id", str(tenant_id))\
            .execute()
            
        if not response.data:
            raise HTTPException(status_code=404, detail="Etapa não encontrada")
            
        return Stage.model_validate(response.data[0])

    def reorder_stages(self, tenant_id: UUID, funnel_id: UUID, items: List[StageReorderItem]):
        """Reordenar etapas via lote (ajusta a coluna position)"""
        # No Supabase/Postgrest Python, fazemos um update por ID ou usamos RPC se os items forem muitos
        for item in items:
            self.supabase.table(self.stage_table)\
                .update({"position": item.position})\
                .eq("id", str(item.id))\
                .eq("funnel_id", str(funnel_id))\
                .eq("tenant_id", str(tenant_id))\
                .execute()
                
        return {"status": "success", "message": "Etapas reordenadas"}

    def delete_stage(self, tenant_id: UUID, stage_id: UUID, move_to_stage_id: Optional[UUID] = None):
        """GAP 3: Deletar etapa com reordenação automática de positions"""
        # Buscar etapa para obter funnel_id e position
        stage_res = self.supabase.table(self.stage_table)\
            .select("funnel_id, position")\
            .eq("id", str(stage_id))\
            .eq("tenant_id", str(tenant_id))\
            .single()\
            .execute()
        
        if not stage_res.data:
            raise HTTPException(status_code=404, detail="Etapa não encontrada")
        
        stage = stage_res.data
        funnel_id = stage["funnel_id"]
        deleted_position = stage["position"]
        
        # Verificar conversas vinculadas
        conv_count = self.supabase.table(self.conv_table)\
            .select("id", count="exact")\
            .eq("stage_id", str(stage_id))\
            .execute()
        
        if conv_count.count > 0:
            if not move_to_stage_id:
                raise HTTPException(
                    status_code=409,
                    detail=f"{conv_count.count} conversas vinculadas. Use move_to_stage_id para migrar."
                )
            
            # Migrar conversas
            self.supabase.table(self.conv_table)\
                .update({"stage_id": str(move_to_stage_id)})\
                .eq("stage_id", str(stage_id))\
                .execute()
        
        # Deletar etapa
        self.supabase.table(self.stage_table)\
            .delete()\
            .eq("id", str(stage_id))\
            .eq("tenant_id", str(tenant_id))\
            .execute()
        
        # GAP 3: Reordenar etapas restantes (fechar gaps)
        # Buscar etapas após a deletada
        stages_after = self.supabase.table(self.stage_table)\
            .select("id, position")\
            .eq("funnel_id", str(funnel_id))\
            .gt("position", deleted_position)\
            .execute()
        
        # Atualizar position de cada uma (decrementando 1)
        for stage_after in stages_after.data:
            self.supabase.table(self.stage_table)\
                .update({"position": stage_after["position"] - 1})\
                .eq("id", stage_after["id"])\
                .execute()
                
        return {"status": "success"}

    # ========== MOVIMENTAÇÃO ==========

    def move_conversation(self, tenant_id: UUID, conversation_id: UUID, request: MoveConversationRequest, moved_by: Optional[UUID] = None):
        """GAP 2 e 4: Mover conversa com validações de compatibilidade e permissão"""
        # Buscar conversa
        conv_res = self.supabase.table(self.conv_table)\
            .select("*")\
            .eq("id", str(conversation_id))\
            .eq("tenant_id", str(tenant_id))\
            .single()\
            .execute()
            
        if not conv_res.data:
            raise HTTPException(status_code=404, detail="Conversa não encontrada")
            
        conv = conv_res.data
        from_stage_id = conv.get("stage_id")
        
        # GAP 4: Validar permissão (apenas dono da conversa)
        if moved_by and conv.get("assigned_to_user_id") != str(moved_by):
            raise HTTPException(status_code=403, detail="Apenas o proprietário da conversa pode movê-la")
            
        # Buscar etapa de destino
        to_stage_res = self.supabase.table(self.stage_table)\
            .select("funnel_id")\
            .eq("id", str(request.to_stage_id))\
            .eq("tenant_id", str(tenant_id))\
            .single()\
            .execute()
            
        if not to_stage_res.data:
            raise HTTPException(status_code=404, detail="Etapa de destino não encontrada")
            
        # GAP 2: Validar compatibilidade stage ↔ funnel
        if to_stage_res.data["funnel_id"] != conv["funnel_id"]:
            raise HTTPException(status_code=400, detail="Etapa não pertence ao funil da conversa")
            
        # Atualizar conversa
        self.supabase.table(self.conv_table)\
            .update({"stage_id": str(request.to_stage_id)})\
            .eq("id", str(conversation_id))\
            .execute()
            
        # Gravar histórico
        history_data = {
            "conversation_id": str(conversation_id),
            "tenant_id": str(tenant_id),
            "from_stage_id": from_stage_id,
            "to_stage_id": str(request.to_stage_id),
            "moved_by": str(moved_by) if moved_by else None,
            "notes": request.notes
        }
        
        self.supabase.table(self.history_table)\
            .insert(history_data)\
            .execute()
            
        return {"status": "success", "message": "Conversa movida com sucesso"}

    def get_conversation_history(self, tenant_id: UUID, conversation_id: UUID):
        """Buscar histórico de movimentações de uma conversa"""
        # Validar conversa
        conv = self.supabase.table(self.conv_table)\
            .select("id")\
            .eq("id", str(conversation_id))\
            .eq("tenant_id", str(tenant_id))\
            .single()\
            .execute()
            
        if not conv.data:
            raise HTTPException(status_code=404, detail="Conversa não encontrada")
            
        response = self.supabase.table(self.history_table)\
            .select("*, from_stage:crm_stages!from_stage_id(name), to_stage:crm_stages!to_stage_id(name)")\
            .eq("conversation_id", str(conversation_id))\
            .order("moved_at", desc=True)\
            .execute()
            
        return response.data

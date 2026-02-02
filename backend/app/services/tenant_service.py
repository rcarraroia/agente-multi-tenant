from uuid import UUID
from typing import Optional, List
from app.db.supabase import get_supabase
from app.schemas.tenant import TenantCreate, TenantUpdate, Tenant
from app.core.exceptions import EntityNotFoundException
from postgrest.exceptions import APIError

class TenantService:
    def __init__(self):
        self.supabase = get_supabase()
        self.table = "multi_agent_tenants"

    def create_tenant(self, data: TenantCreate) -> Tenant:
        try:
            # Check if exists (idempotency by affiliate_id)
            existing = self.supabase.table(self.table)\
                .select("*")\
                .eq("affiliate_id", str(data.affiliate_id))\
                .execute()
            
            if existing.data:
                return Tenant.model_validate(existing.data[0])

            response = self.supabase.table(self.table)\
                .insert(data.model_dump(mode='json'))\
                .execute()
            
            tenant = Tenant.model_validate(response.data[0])
            
            # GAP 5: Criar funil padrão automaticamente
            self._create_default_funnel(tenant.id)
            
            return tenant
        except APIError as e:
            raise e

    def get_by_id(self, tenant_id: UUID) -> Tenant:
        response = self.supabase.table(self.table)\
            .select("*")\
            .eq("id", str(tenant_id))\
            .execute()
        
        if not response.data:
            raise EntityNotFoundException(f"Tenant {tenant_id} not found")
        
        return Tenant.model_validate(response.data[0])

    def get_by_affiliate_id(self, affiliate_id: UUID) -> Tenant:
        response = self.supabase.table(self.table)\
            .select("*")\
            .eq("affiliate_id", str(affiliate_id))\
            .execute()
        
        if not response.data:
            raise EntityNotFoundException(f"Tenant for affiliate {affiliate_id} not found")
        
        return Tenant.model_validate(response.data[0])

    def get_by_chatwoot_account_id(self, account_id: int) -> Tenant:
        response = self.supabase.table(self.table)\
            .select("*")\
            .eq("chatwoot_account_id", account_id)\
            .execute()
        
        if not response.data:
            raise EntityNotFoundException(f"Tenant for chatwoot account {account_id} not found")
        
        # If multiple, take first? Usually 1:1 map.
        return Tenant.model_validate(response.data[0])

    def update_tenant(self, tenant_id: UUID, data: TenantUpdate) -> Tenant:
        update_data = data.model_dump(exclude_unset=True, mode='json')
        if not update_data:
            return self.get_by_id(tenant_id)

        response = self.supabase.table(self.table)\
            .update(update_data)\
            .eq("id", str(tenant_id))\
            .execute()
        
        if not response.data:
            raise EntityNotFoundException(f"Tenant {tenant_id} not found")
        
        return Tenant.model_validate(response.data[0])

    def _create_default_funnel(self, tenant_id: UUID):
        """GAP 5: Criar funil padrão ("Funil de Vendas") com 6 etapas para o novo tenant"""
        try:
            # 1. Criar funil
            funnel_res = self.supabase.table('crm_funnels').insert({
                'tenant_id': str(tenant_id),
                'name': 'Funil de Vendas',
                'description': 'Funil padrão criado automaticamente',
                'is_default': True
            }).execute()
            
            if not funnel_res.data:
                return
            
            funnel_id = funnel_res.data[0]['id']
            
            # 2. Criar 6 etapas padrão
            stages = [
                {'name': 'Novo Lead', 'position': 1, 'color': '#3B82F6'},
                {'name': 'Contato Inicial', 'position': 2, 'color': '#8B5CF6'},
                {'name': 'Proposta Enviada', 'position': 3, 'color': '#F59E0B'},
                {'name': 'Negociação', 'position': 4, 'color': '#EF4444'},
                {'name': 'Fechado', 'position': 5, 'color': '#10B981'},
                {'name': 'Perdido', 'position': 6, 'color': '#6B7280'}
            ]
            
            # Adicionar metadata
            for stage in stages:
                stage['funnel_id'] = funnel_id
                stage['tenant_id'] = str(tenant_id)
            
            # Inserir em lote
            self.supabase.table('crm_stages').insert(stages).execute()
        except Exception as e:
            # Logar erro, mas não travar criação do tenant se for crítico
            print(f"Erro ao criar funil padrão para o tenant {tenant_id}: {str(e)}")

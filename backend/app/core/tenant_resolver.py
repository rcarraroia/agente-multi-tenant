"""
Tenant Resolution System - Via JWT (affiliate_id)

Este módulo implementa a resolução de tenant baseada em JWT tokens,
extraindo o affiliate_id do token e resolvendo o tenant correspondente.

Substitui completamente qualquer sistema baseado em subdomain.
"""

import json
from typing import Optional
from uuid import UUID
from functools import wraps
from fastapi import Request
from jose import jwt, JWTError
import redis

from app.config import settings
from app.core.security import verify_token
from app.core.exceptions import CredentialsException, EntityNotFoundException
from app.db.supabase import get_supabase
from app.schemas.tenant import Tenant


def cache_tenant(ttl=300):  # 5 minutos
    """
    Decorator para cache de tenant resolution com TTL.
    
    Args:
        ttl: Time to live em segundos (default: 5 minutos)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(self, token: str):
            # Extrair user_id do token para usar como chave de cache
            try:
                payload = verify_token(token)
                user_id = payload.get("sub")
                if not user_id:
                    # Se não conseguir extrair user_id, não usar cache
                    return func(self, token)
                
                cache_key = f"tenant:resolution:{user_id}"
                
                # Tentar buscar do cache se Redis disponível
                if self.redis_client:
                    try:
                        cached = self.redis_client.get(cache_key)
                        if cached:
                            tenant_data = json.loads(cached)
                            return Tenant.model_validate(tenant_data)
                    except Exception:
                        # Se cache falhar, continuar sem cache
                        pass
                
                # Buscar do banco
                result = func(self, token)
                
                # Salvar no cache se Redis disponível
                if self.redis_client:
                    try:
                        tenant_dict = result.model_dump() if hasattr(result, 'model_dump') else result.dict()
                        self.redis_client.setex(cache_key, ttl, json.dumps(tenant_dict, default=str))
                    except Exception:
                        # Se cache falhar, continuar sem cache
                        pass
                
                return result
                
            except Exception:
                # Se qualquer coisa falhar, executar função original
                return func(self, token)
                
        return wrapper
    return decorator


class TenantResolver:
    """
    Classe responsável por resolver tenant a partir de JWT tokens.
    
    Fluxo:
    1. Extrai JWT token do header Authorization
    2. Valida e decodifica o token
    3. Extrai user_id (sub) do payload
    4. Busca affiliate_id correspondente ao user_id
    5. Resolve tenant via affiliate_id
    """
    
    def __init__(self):
        self.supabase = get_supabase()
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        except Exception as e:
            # Se Redis não estiver disponível, continuar sem cache
            self.redis_client = None
    
    @cache_tenant(ttl=300)
    def get_tenant_from_jwt(self, token: str) -> Tenant:
        """
        Resolve tenant a partir de JWT token.
        
        Args:
            token: JWT token (sem 'Bearer ' prefix)
            
        Returns:
            Tenant: Objeto tenant resolvido
            
        Raises:
            CredentialsException: Token inválido ou malformado
            EntityNotFoundException: User não é afiliado ou tenant não existe
        """
        try:
            # 1. Validar e decodificar token
            payload = verify_token(token)
            user_id = payload.get("sub")
            
            if not user_id:
                raise CredentialsException(detail="Token não contém user_id válido")
            
            # 2. Buscar affiliate_id pelo user_id
            affiliate_id = self._get_affiliate_id_by_user_id(user_id)
            
            # 3. Resolver tenant pelo affiliate_id
            tenant = self._get_tenant_by_affiliate_id(affiliate_id)
            
            return tenant
            
        except JWTError as e:
            raise CredentialsException(detail=f"Token JWT inválido: {str(e)}")
        except Exception as e:
            if isinstance(e, (CredentialsException, EntityNotFoundException)):
                raise e
            raise CredentialsException(detail=f"Erro ao resolver tenant: {str(e)}")
    
    def get_tenant_from_request(self, request: Request) -> Tenant:
        """
        Extrai token do header Authorization e resolve tenant.
        
        Args:
            request: FastAPI Request object
            
        Returns:
            Tenant: Objeto tenant resolvido
            
        Raises:
            CredentialsException: Header Authorization ausente ou inválido
            EntityNotFoundException: Tenant não encontrado
        """
        # Extrair token do header Authorization
        authorization = request.headers.get("Authorization")
        
        if not authorization:
            raise CredentialsException(detail="Header Authorization não fornecido")
        
        if not authorization.startswith("Bearer "):
            raise CredentialsException(detail="Formato de Authorization inválido. Use 'Bearer <token>'")
        
        token = authorization.replace("Bearer ", "")
        
        return self.get_tenant_from_jwt(token)
    
    def _get_affiliate_id_by_user_id(self, user_id: str) -> UUID:
        """
        Busca affiliate_id correspondente ao user_id.
        
        Args:
            user_id: ID do usuário do token JWT
            
        Returns:
            UUID: affiliate_id encontrado
            
        Raises:
            EntityNotFoundException: Usuário não é afiliado
        """
        response = self.supabase.table("affiliates")\
            .select("id")\
            .eq("user_id", user_id)\
            .execute()
        
        if not response.data:
            raise EntityNotFoundException(
                detail=f"Usuário {user_id} não é um afiliado cadastrado"
            )
        
        id_value = response.data[0]["id"]
        return id_value if isinstance(id_value, UUID) else UUID(id_value)
    
    def _get_tenant_by_affiliate_id(self, affiliate_id: UUID) -> Tenant:
        """
        Busca tenant correspondente ao affiliate_id.
        
        Args:
            affiliate_id: ID do afiliado
            
        Returns:
            Tenant: Tenant encontrado
            
        Raises:
            EntityNotFoundException: Tenant não configurado para o afiliado
        """
        response = self.supabase.table("multi_agent_tenants")\
            .select("*")\
            .eq("affiliate_id", str(affiliate_id))\
            .execute()
        
        if not response.data:
            raise EntityNotFoundException(
                detail=f"Tenant não configurado para o afiliado {affiliate_id}"
            )
        
        tenant_data = response.data[0]
        
        # Verificar se tenant está ativo
        if tenant_data.get("status") == "canceled":
            raise EntityNotFoundException(
                detail="Tenant foi cancelado e não pode ser usado"
            )
        
        return Tenant.model_validate(tenant_data)
    
    def invalidate_tenant_cache(self, user_id: str) -> None:
        """
        Invalida o cache de tenant para um usuário específico.
        
        Args:
            user_id: ID do usuário para invalidar cache
        """
        if self.redis_client:
            try:
                cache_key = f"tenant:resolution:{user_id}"
                self.redis_client.delete(cache_key)
            except Exception:
                # Se falhar, continuar silenciosamente
                pass


# Instância global para uso em dependências
tenant_resolver = TenantResolver()


def get_tenant_from_jwt(token: str) -> Tenant:
    """
    Função utilitária para resolver tenant a partir de JWT token.
    
    Args:
        token: JWT token (sem 'Bearer ' prefix)
        
    Returns:
        Tenant: Objeto tenant resolvido
    """
    return tenant_resolver.get_tenant_from_jwt(token)


def get_tenant_from_request(request: Request) -> Tenant:
    """
    Função utilitária para resolver tenant a partir de Request.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        Tenant: Objeto tenant resolvido
    """
    return tenant_resolver.get_tenant_from_request(request)
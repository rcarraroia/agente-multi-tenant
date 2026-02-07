from datetime import datetime, timedelta
from typing import Any, Union, Optional, Dict, List
from jose import jwt, JWTError
from passlib.context import CryptContext
import secrets
import hashlib
from app.config import settings
from app.core.exceptions import CredentialsException
from app.core.logging import get_logger

logger = get_logger(__name__)

class JWTSecurityManager:
    """
    Gerenciador de segurança JWT com validações avançadas e refresh tokens.
    
    Implementa:
    - Validação de algoritmos seguros
    - Verificação de secrets não-padrão
    - Refresh token mechanism
    - Logs de segurança
    """
    
    # Algoritmos seguros permitidos
    SECURE_ALGORITHMS = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512", "ES256", "ES384", "ES512"]
    
    # Algoritmos inseguros (deprecated)
    INSECURE_ALGORITHMS = ["none", "HS1", "RS1", "ES1"]
    
    # Secrets padrão conhecidos (NUNCA usar em produção)
    KNOWN_WEAK_SECRETS = [
        "secret",
        "your-secret-key",
        "jwt-secret",
        "change-me",
        "default-secret",
        "123456",
        "password",
        "secret-key",
        "my-secret",
        "super-secret"
    ]
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self._validate_configuration()
    
    def _validate_configuration(self) -> None:
        """Valida a configuração de segurança JWT."""
        logger.info("🔐 Validando configuração de segurança JWT")
        
        # Validar algoritmo
        if settings.JWT_ALGORITHM not in self.SECURE_ALGORITHMS:
            logger.error(f"❌ Algoritmo JWT inseguro: {settings.JWT_ALGORITHM}")
            raise ValueError(f"Algoritmo JWT inseguro: {settings.JWT_ALGORITHM}")
        
        if settings.JWT_ALGORITHM in self.INSECURE_ALGORITHMS:
            logger.error(f"❌ Algoritmo JWT explicitamente inseguro: {settings.JWT_ALGORITHM}")
            raise ValueError(f"Algoritmo JWT explicitamente inseguro: {settings.JWT_ALGORITHM}")
        
        # Validar secret
        self._validate_jwt_secret(settings.JWT_SECRET)
        
        # Validar Supabase JWT secret se configurado
        if settings.SUPABASE_JWT_SECRET:
            self._validate_jwt_secret(settings.SUPABASE_JWT_SECRET, "SUPABASE_JWT_SECRET")
        
        logger.info("✅ Configuração de segurança JWT validada com sucesso")
    
    def _validate_jwt_secret(self, secret: str, secret_name: str = "JWT_SECRET") -> None:
        """Valida se o secret JWT é seguro."""
        if not secret:
            logger.error(f"❌ {secret_name} não configurado")
            raise ValueError(f"{secret_name} não pode estar vazio")
        
        # Verificar se é um secret conhecido/fraco
        if secret.lower() in [s.lower() for s in self.KNOWN_WEAK_SECRETS]:
            logger.error(f"❌ {secret_name} é um secret conhecido/fraco")
            raise ValueError(f"{secret_name} é um secret conhecido e inseguro")
        
        # Verificar comprimento mínimo
        if len(secret) < 32:
            logger.warning(f"⚠️ {secret_name} tem menos de 32 caracteres (recomendado: 64+)")
        
        # Verificar complexidade básica
        if secret.isalnum() and len(secret) < 64:
            logger.warning(f"⚠️ {secret_name} parece simples demais (use caracteres especiais)")
        
        logger.debug(f"✅ {secret_name} passou na validação básica")
    
    def create_access_token(
        self, 
        subject: Union[str, Any], 
        expires_delta: Optional[timedelta] = None,
        additional_claims: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Cria um access token JWT com validações de segurança.
        
        Args:
            subject: Subject do token (user_id)
            expires_delta: Tempo de expiração customizado
            additional_claims: Claims adicionais para o token
            
        Returns:
            str: Token JWT assinado
        """
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # Claims obrigatórios
        to_encode = {
            "sub": str(subject),
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        }
        
        # Adicionar claims extras se fornecidos
        if additional_claims:
            to_encode.update(additional_claims)
        
        try:
            encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
            
            logger.debug(f"🔐 Access token criado para subject: {subject}")
            logger.debug(f"   Expira em: {expire}")
            logger.debug(f"   Algoritmo: {settings.JWT_ALGORITHM}")
            
            return encoded_jwt
            
        except Exception as e:
            logger.error(f"💥 Erro ao criar access token: {str(e)}")
            raise CredentialsException(detail="Erro ao criar token de acesso")
    
    def create_refresh_token(self, subject: Union[str, Any]) -> str:
        """
        Cria um refresh token JWT com validade estendida.
        
        Args:
            subject: Subject do token (user_id)
            
        Returns:
            str: Refresh token JWT
        """
        # Refresh tokens têm validade muito maior (30 dias)
        expire = datetime.utcnow() + timedelta(days=30)
        
        to_encode = {
            "sub": str(subject),
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "refresh",
            "jti": secrets.token_urlsafe(32)  # Unique token ID
        }
        
        try:
            encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
            
            logger.debug(f"🔄 Refresh token criado para subject: {subject}")
            logger.debug(f"   Expira em: {expire}")
            
            return encoded_jwt
            
        except Exception as e:
            logger.error(f"💥 Erro ao criar refresh token: {str(e)}")
            raise CredentialsException(detail="Erro ao criar refresh token")
    
    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Verifica e decodifica um token JWT com validações de segurança.
        
        Args:
            token: Token JWT para verificar
            token_type: Tipo esperado do token ("access" ou "refresh")
            
        Returns:
            Dict: Payload do token decodificado
            
        Raises:
            CredentialsException: Se token inválido ou inseguro
        """
        if not token:
            logger.warning("⚠️ Tentativa de verificação com token vazio")
            raise CredentialsException(detail="Token não fornecido")
        
        try:
            # Primeiro, tenta validar como token Supabase Auth
            if settings.SUPABASE_JWT_SECRET:
                try:
                    payload = jwt.decode(
                        token,
                        settings.SUPABASE_JWT_SECRET,
                        algorithms=["HS256"],
                        audience="authenticated"
                    )
                    
                    logger.debug("✅ Token Supabase Auth validado com sucesso")
                    return payload
                    
                except JWTError:
                    logger.debug("🔄 Token não é Supabase Auth, tentando JWT local")
            
            # Validar como JWT local
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            
            # Validar tipo do token se especificado
            if token_type and payload.get("type") != token_type:
                logger.warning(f"⚠️ Tipo de token incorreto. Esperado: {token_type}, Recebido: {payload.get('type')}")
                raise CredentialsException(detail=f"Tipo de token incorreto")
            
            # Validar expiração (jose já faz isso, mas vamos logar)
            exp = payload.get("exp")
            if exp:
                exp_datetime = datetime.fromtimestamp(exp)
                if exp_datetime < datetime.utcnow():
                    logger.warning(f"⚠️ Token expirado: {exp_datetime}")
                    raise CredentialsException(detail="Token expirado")
            
            logger.debug(f"✅ Token JWT local validado com sucesso (tipo: {payload.get('type', 'unknown')})")
            return payload
            
        except JWTError as e:
            logger.warning(f"⚠️ Token JWT inválido: {str(e)}")
            raise CredentialsException(detail="Token inválido")
        except Exception as e:
            logger.error(f"💥 Erro inesperado na verificação do token: {str(e)}")
            raise CredentialsException(detail="Erro na verificação do token")
    
    def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """
        Gera um novo access token usando um refresh token válido.
        
        Args:
            refresh_token: Refresh token válido
            
        Returns:
            Dict: Novo access token e refresh token
        """
        try:
            # Verificar refresh token
            payload = self.verify_token(refresh_token, token_type="refresh")
            subject = payload.get("sub")
            
            if not subject:
                logger.warning("⚠️ Refresh token sem subject")
                raise CredentialsException(detail="Refresh token inválido")
            
            # Gerar novos tokens
            new_access_token = self.create_access_token(subject)
            new_refresh_token = self.create_refresh_token(subject)
            
            logger.info(f"🔄 Tokens renovados para subject: {subject}")
            
            return {
                "access_token": new_access_token,
                "refresh_token": new_refresh_token,
                "token_type": "bearer"
            }
            
        except CredentialsException:
            raise
        except Exception as e:
            logger.error(f"💥 Erro ao renovar tokens: {str(e)}")
            raise CredentialsException(detail="Erro ao renovar tokens")
    
    def get_token_info(self, token: str) -> Dict[str, Any]:
        """
        Obtém informações sobre um token sem validar assinatura (para debug).
        
        Args:
            token: Token JWT
            
        Returns:
            Dict: Informações do token
        """
        try:
            # Decodificar sem verificar assinatura (apenas para info)
            payload = jwt.decode(token, options={"verify_signature": False})
            
            info = {
                "subject": payload.get("sub"),
                "type": payload.get("type", "unknown"),
                "issued_at": payload.get("iat"),
                "expires_at": payload.get("exp"),
                "algorithm": "unknown"  # Não podemos determinar sem header
            }
            
            # Converter timestamps para datetime legível
            if info["issued_at"]:
                info["issued_at_readable"] = datetime.fromtimestamp(info["issued_at"]).isoformat()
            
            if info["expires_at"]:
                info["expires_at_readable"] = datetime.fromtimestamp(info["expires_at"]).isoformat()
                info["is_expired"] = datetime.fromtimestamp(info["expires_at"]) < datetime.utcnow()
            
            return info
            
        except Exception as e:
            logger.error(f"💥 Erro ao obter informações do token: {str(e)}")
            return {"error": str(e)}
    
    def generate_secure_secret(self, length: int = 64) -> str:
        """
        Gera um secret seguro para JWT.
        
        Args:
            length: Comprimento do secret (padrão: 64)
            
        Returns:
            str: Secret seguro gerado
        """
        secure_secret = secrets.token_urlsafe(length)
        
        logger.info(f"🔐 Secret seguro gerado com {length} caracteres")
        logger.warning("⚠️ IMPORTANTE: Salve este secret em local seguro e configure no .env")
        
        return secure_secret

# Instância global do gerenciador de segurança
jwt_security_manager = JWTSecurityManager()

# Funções de compatibilidade com código existente
def create_access_token(subject: Union[str, Any], expires_delta: timedelta = None) -> str:
    """Função de compatibilidade - usa o JWTSecurityManager."""
    return jwt_security_manager.create_access_token(subject, expires_delta)

def verify_token(token: str) -> dict:
    """Função de compatibilidade - usa o JWTSecurityManager."""
    return jwt_security_manager.verify_token(token)

def get_tenant_id_from_token(payload: dict) -> Optional[str]:
    """
    Extracts tenant_id from JWT payload metadata if present.
    Adapt based on actual token structure from Slim Quality auth.
    """
    # Placeholder: Assuming tenant_id might be in app_metadata or user_metadata
    # This needs verification with the actual auth implementation
    return payload.get("app_metadata", {}).get("tenant_id")

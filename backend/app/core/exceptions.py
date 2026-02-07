from typing import Any, Dict, Optional
from fastapi import HTTPException, status

class CredentialsException(HTTPException):
    """
    Exceção de credenciais com suporte a códigos de erro específicos.
    """
    def __init__(
        self, 
        detail: str = "Could not validate credentials",
        error_code: str = "AUTH_UNKNOWN",
        error_type: str = "authentication_error"
    ):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
        self.error_code = error_code
        self.error_type = error_type

class PermissionDeniedException(HTTPException):
    """
    Exceção de permissão com suporte a códigos de erro específicos.
    """
    def __init__(
        self, 
        detail: str = "Permission denied",
        error_code: str = "PERM_UNKNOWN",
        error_type: str = "permission_error"
    ):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail
        )
        self.error_code = error_code
        self.error_type = error_type

class EntityNotFoundException(HTTPException):
    """
    Exceção de entidade não encontrada com suporte a códigos de erro específicos.
    """
    def __init__(
        self, 
        detail: str = "Entity not found",
        error_code: str = "NOT_FOUND_UNKNOWN",
        error_type: str = "not_found_error"
    ):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail
        )
        self.error_code = error_code
        self.error_type = error_type

class ValidationException(HTTPException):
    """
    Exceção de validação com suporte a códigos de erro específicos.
    """
    def __init__(
        self, 
        detail: str = "Validation error",
        error_code: str = "VALIDATION_UNKNOWN",
        error_type: str = "validation_error"
    ):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail
        )
        self.error_code = error_code
        self.error_type = error_type

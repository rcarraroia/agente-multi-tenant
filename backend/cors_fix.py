#!/usr/bin/env python3
"""
CORS FIX - ARQUIVO SEPARADO PARA GARANTIR CORS
Este arquivo deve ser importado ANTES de qualquer coisa
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.logging import get_logger

logger = get_logger('cors_fix')

def setup_cors(app: FastAPI):
    """Configurar CORS de forma ULTRA PERMISSIVA"""
    
    logger.info("CORS FIX - Configurando CORS ultra permissivo")
    
    # Obter CORS_ORIGINS do ambiente
    cors_origins_env = os.getenv("CORS_ORIGINS", "")
    
    # Lista de origens permitidas
    allowed_origins = [
        "https://agente-multi-tenant.vercel.app",
        "http://localhost:3000",
        "http://localhost:5173",
        "https://slimquality.com.br"
    ]
    
    # Adicionar origens do ambiente se existirem
    if cors_origins_env:
        env_origins = [origin.strip() for origin in cors_origins_env.split(",")]
        allowed_origins.extend(env_origins)
        logger.info(f"Origens do ambiente adicionadas: {env_origins}")
    
    logger.info(f"Origens CORS permitidas: {allowed_origins}")
    
    # CORS ULTRA PERMISSIVO - DEVE FUNCIONAR
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,  # ORIGENS ESPECÍFICAS PARA PERMITIR CREDENTIALS
        allow_credentials=True,  # HABILITAR CREDENTIALS PARA AUTHORIZATION HEADER
        allow_methods=["*"],  # TODOS OS MÉTODOS
        allow_headers=["*"],  # TODOS OS HEADERS
        expose_headers=["*"],  # EXPOR TODOS OS HEADERS
    )
    
    logger.info("CORS ultra permissivo configurado!")
    
    return app
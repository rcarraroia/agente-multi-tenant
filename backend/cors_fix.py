#!/usr/bin/env python3
"""
CORS FIX - ARQUIVO SEPARADO PARA GARANTIR CORS
Este arquivo deve ser importado ANTES de qualquer coisa
"""

import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

def setup_cors(app: FastAPI):
    """Configurar CORS de forma ULTRA PERMISSIVA"""
    
    print("🚀 CORS FIX - CONFIGURANDO CORS ULTRA PERMISSIVO")
    
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
        print(f"📋 Origens do ambiente adicionadas: {env_origins}")
    
    print(f"🌐 Origens CORS permitidas: {allowed_origins}")
    
    # CORS ULTRA PERMISSIVO - DEVE FUNCIONAR
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,  # ORIGENS ESPECÍFICAS PARA PERMITIR CREDENTIALS
        allow_credentials=True,  # HABILITAR CREDENTIALS PARA AUTHORIZATION HEADER
        allow_methods=["*"],  # TODOS OS MÉTODOS
        allow_headers=["*"],  # TODOS OS HEADERS
        expose_headers=["*"],  # EXPOR TODOS OS HEADERS
    )
    
    print("✅ CORS ULTRA PERMISSIVO CONFIGURADO!")
    
    # Adicionar headers manualmente também
    @app.middleware("http")
    async def add_cors_headers(request, call_next):
        response = await call_next(request)
        
        # Obter origem da requisição
        origin = request.headers.get("origin")
        
        # Lista de origens permitidas (mesma do middleware)
        allowed_origins = [
            "https://agente-multi-tenant.vercel.app",
            "http://localhost:3000",
            "http://localhost:5173",
            "https://slimquality.com.br"
        ]
        
        # Adicionar origens do ambiente se existirem
        cors_origins_env = os.getenv("CORS_ORIGINS", "")
        if cors_origins_env:
            env_origins = [origin.strip() for origin in cors_origins_env.split(",")]
            allowed_origins.extend(env_origins)
        
        # Se origem está na lista permitida, adicionar headers
        if origin in allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
        
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Expose-Headers"] = "*"
        return response
    
    print("✅ HEADERS CORS MANUAIS ADICIONADOS!")
    
    return app
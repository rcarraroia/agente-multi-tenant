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
    
    # CORS ULTRA PERMISSIVO - DEVE FUNCIONAR
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # PERMITIR TODAS AS ORIGENS
        allow_credentials=False,  # Desabilitar credentials para permitir *
        allow_methods=["*"],  # TODOS OS MÉTODOS
        allow_headers=["*"],  # TODOS OS HEADERS
        expose_headers=["*"],  # EXPOR TODOS OS HEADERS
    )
    
    print("✅ CORS ULTRA PERMISSIVO CONFIGURADO!")
    
    # Adicionar headers manualmente também
    @app.middleware("http")
    async def add_cors_headers(request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "*"
        response.headers["Access-Control-Allow-Headers"] = "*"
        response.headers["Access-Control-Expose-Headers"] = "*"
        return response
    
    print("✅ HEADERS CORS MANUAIS ADICIONADOS!")
    
    return app
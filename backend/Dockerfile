# Agente Multi-Tenant Backend - Otimizado para EasyPanel com AI Dependencies
# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Instalar dependências de sistema para compilação
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    gcc \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Configurar pip para downloads grandes e timeouts estendidos
RUN pip install --no-cache-dir --upgrade pip

# Copiar requirements e instalar em etapas para otimizar cache
COPY requirements.txt .

# Instalar dependências básicas primeiro (cache layer)
RUN pip install --no-cache-dir --timeout=300 \
    fastapi==0.115.6 \
    uvicorn[standard]==0.34.0 \
    pydantic==2.10.4 \
    pydantic-settings==2.7.0 \
    python-dotenv==1.0.1 \
    python-multipart==0.0.9 \
    supabase==2.11.0 \
    python-jose[cryptography]==3.3.0 \
    passlib[bcrypt]==1.7.4 \
    redis==5.2.1 \
    structlog==24.4.0

# Instalar dependências AI com timeout estendido (cache layer separado)
RUN pip install --no-cache-dir --timeout=600 --retries=3 \
    numpy==1.26.4 \
    tiktoken==0.8.0

# Instalar LangChain (cache layer separado)
RUN pip install --no-cache-dir --timeout=600 --retries=3 \
    langchain==0.3.14 \
    langchain-openai==0.3.1 \
    langchain-community==0.3.14 \
    langgraph==0.2.62

# Instalar sentence-transformers por último (maior download)
RUN pip install --no-cache-dir --timeout=900 --retries=3 \
    sentence-transformers==3.3.1

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Instalar apenas dependências runtime necessárias
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Criar usuário não-root para segurança
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Copiar dependências instaladas do builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiar código da aplicação
COPY . .

# Configurar timezone
ENV TZ=America/Sao_Paulo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Configurar permissões
RUN chown -R appuser:appuser /app
USER appuser

# Expor porta
EXPOSE 8000

# Health check otimizado
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando de inicialização otimizado para produção
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--access-log", "--log-level", "info"]

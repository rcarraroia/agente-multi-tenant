# Agente Multi-Tenant Backend - Otimizado para EasyPanel (CPU-ONLY) - VERSÃO CORS CORRIGIDA
# Build stage
FROM python:3.11-slim-bookworm as builder

WORKDIR /app

# Instalar dependências de sistema para compilação
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Configurar pip
RUN pip install --no-cache-dir --upgrade pip

# Copiar requirements
COPY requirements.txt .

# 1. Instalar Torch CPU-ONLY primeiro (GRANDE ECONOMIA DE ESPAÇO)
# Isso evita o download de ~600MB de drivers CUDA desnecessários
RUN pip install --no-cache-dir --timeout=600 --retries=3 \
    torch==2.4.1 --index-url https://download.pytorch.org/whl/cpu

# 2. Instalar demais dependências do requirements.txt
RUN pip install --no-cache-dir --timeout=600 --retries=3 -r requirements.txt

# Production stage
FROM python:3.11-slim-bookworm

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

# Variáveis de ambiente padrão
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expor porta
EXPOSE 8000

# Health check otimizado
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando de inicialização otimizado para produção
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--access-log", "--log-level", "info"]

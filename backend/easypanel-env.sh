#!/bin/bash
# Script para configurar variáveis de ambiente no EasyPanel
# Execute este script no EasyPanel para configurar as variáveis necessárias

echo "🔧 Configurando variáveis de ambiente para EasyPanel..."

# CORS Origins - CRÍTICO para funcionamento do frontend
export CORS_ORIGINS="https://agente-multi-tenant.vercel.app,https://agente-multi-tenant-rcarraroias-projects.vercel.app,https://agente-multi-tenant-git-main-rcarraroias-projects.vercel.app"

# Environment
export ENVIRONMENT="production"
export DEBUG="False"

# Supabase
export SUPABASE_URL="https://vtynmmtuvxreiwcxxlma.supabase.co"
export SUPABASE_SERVICE_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ0eW5tbXR1dnhyZWl3Y3h4bG1hIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NjM4MTYwMiwiZXhwIjoyMDcxOTU3NjAyfQ.-vh-TMWwltqy8--3Ka9Fb9ToYwRw8nkdP49QtKZ77e0"
export SUPABASE_ANON_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InZ0eW5tbXR1dnhyZWl3Y3h4bG1hIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYzODE2MDIsImV4cCI6MjA3MTk1NzYwMn0.fd-WSqFh7QsSlB0Q62cXAZZ-yDcI0n0sXyJ4eWIRKH8"

# JWT
export JWT_SECRET_KEY="_O3O3Oq58pf5dd1y8Kkfeyk0aNFQttvih26JBXzztUDIUju8QlxcYjAZdEoKZsZJC5zZvYYMc_lUxk6VCXIFyQ"
export JWT_ALGORITHM="HS256"

# Supabase Auth JWT
export SUPABASE_JWT_SECRET="HOwlz7ir1R2EvyMSy9yj+HSh25RtIVzSeORRcM9T1MlCiux5w6wGfYf9dLbyYPQnJgrfaGbb/dR1oin1cS7BnA=="

# Redis
export REDIS_URL="redis://localhost:6379"

# OpenAI
export OPENAI_API_KEY="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"

# Evolution API
export EVOLUTION_API_URL="https://slimquality-evolution-api.wpjtfd.easypanel.host"
export EVOLUTION_API_KEY="Ombp1cOulPQzW3vhx9YRcF9x9b32D95mWZVwTLuF9nFxpizJlMdkvRUqH08OEy07K6eOUsVNiblaBVQ87bSDn0SoZi033ujz4on90dRm9XDJsWCFq23jEph9KmC5IIjt"

# Chatwoot
export CHATWOOT_URL="https://slimquality-chatwoot.wpjtfd.easypanel.host"
export CHATWOOT_ADMIN_TOKEN="YSEK4JiCW6HHXNvhkoj3m8pe"
export CHATWOOT_ACCOUNT_ID="5"
export CHATWOOT_INBOX_ID="1"

echo "✅ Variáveis de ambiente configuradas!"
echo "🚨 IMPORTANTE: Configure estas variáveis no EasyPanel Dashboard:"
echo "   - CORS_ORIGINS=$CORS_ORIGINS"
echo "   - ENVIRONMENT=$ENVIRONMENT"
echo "   - E todas as outras variáveis listadas acima"
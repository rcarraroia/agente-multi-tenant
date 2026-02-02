# Backend Agente Multi-Tenant

API em FastAPI para gerenciamento do Agente Multi-Tenant (Slim Quality).

## Estrutura
- **app/core**: Configurações e Segurança.
- **app/db**: Conexão com Supabase.
- **app/api**: Rotas e endpoints.
- **app/services**: Lógica de negócio.

## Instalação

1. Crie um ambiente virtual:
```bash
python -m venv venv
# Windows
.\venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

2. Instale as dependências:
```bash
pip install -r requirements.txt
```

3. Configure as variáveis de ambiente:
Copie `.env.example` para `.env` e preencha as chaves.

## Execução

Inicie o servidor de desenvolvimento:
```bash
uvicorn app.main:app --reload
```

Acesse a documentação:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Testes
```bash
pytest
```

-- Migração: Criar tabela multi_agent_embeddings para vetores RAG
-- Data: 2026-02-01
-- Descrição: Armazena embeddings dos documentos para busca semântica
-- Requer: Extensão pgvector habilitada

-- Habilitar extensão pgvector (se não estiver)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS multi_agent_embeddings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES multi_agent_tenants(id) ON DELETE CASCADE,
    document_id UUID NOT NULL REFERENCES multi_agent_documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    embedding vector(1536), -- Dimensão do text-embedding-3-small
    chunk_index INTEGER NOT NULL DEFAULT 0,
    metadata JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índice vetorial para busca por similaridade
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON multi_agent_embeddings 
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- Índice para filtrar por tenant
CREATE INDEX IF NOT EXISTS idx_embeddings_tenant_id ON multi_agent_embeddings(tenant_id);

-- Índice para filtrar por documento
CREATE INDEX IF NOT EXISTS idx_embeddings_document_id ON multi_agent_embeddings(document_id);

-- RLS: Cada tenant só vê seus próprios embeddings
ALTER TABLE multi_agent_embeddings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Tenants can view their own embeddings"
    ON multi_agent_embeddings
    FOR SELECT
    USING (tenant_id IN (
        SELECT id FROM multi_agent_tenants 
        WHERE affiliate_id = auth.uid()
    ));

-- Função RPC para buscar documentos similares (usado pelo RAG)
CREATE OR REPLACE FUNCTION match_documents(
    query_embedding vector(1536),
    match_tenant_id UUID,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id UUID,
    content TEXT,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id,
        e.content,
        1 - (e.embedding <=> query_embedding) AS similarity
    FROM multi_agent_embeddings e
    WHERE e.tenant_id = match_tenant_id
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;

COMMENT ON TABLE multi_agent_embeddings IS 'Vetores de embeddings para busca semântica RAG';
COMMENT ON FUNCTION match_documents IS 'Busca documentos similares por cosine similarity';

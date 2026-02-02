-- Migração: Criar tabela multi_agent_documents para Base de Conhecimento
-- Data: 2026-02-01
-- Descrição: Armazena metadados de documentos enviados pelos tenants para RAG

CREATE TABLE IF NOT EXISTS multi_agent_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES multi_agent_tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    file_path TEXT NOT NULL,
    content_type VARCHAR(100) NOT NULL,
    size_bytes BIGINT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, processing, completed, failed
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Índice para buscar documentos por tenant
CREATE INDEX IF NOT EXISTS idx_documents_tenant_id ON multi_agent_documents(tenant_id);

-- RLS: Cada tenant só vê seus próprios documentos
ALTER TABLE multi_agent_documents ENABLE ROW LEVEL SECURITY;

-- Política: SELECT apenas para o próprio tenant
CREATE POLICY "Tenants can view their own documents"
    ON multi_agent_documents
    FOR SELECT
    USING (tenant_id IN (
        SELECT id FROM multi_agent_tenants 
        WHERE affiliate_id = auth.uid()
    ));

-- Política: INSERT apenas para o próprio tenant
CREATE POLICY "Tenants can insert their own documents"
    ON multi_agent_documents
    FOR INSERT
    WITH CHECK (tenant_id IN (
        SELECT id FROM multi_agent_tenants 
        WHERE affiliate_id = auth.uid()
    ));

-- Política: DELETE apenas para o próprio tenant
CREATE POLICY "Tenants can delete their own documents"
    ON multi_agent_documents
    FOR DELETE
    USING (tenant_id IN (
        SELECT id FROM multi_agent_tenants 
        WHERE affiliate_id = auth.uid()
    ));

-- Trigger para atualizar updated_at automaticamente
CREATE OR REPLACE FUNCTION update_documents_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_documents_updated_at
    BEFORE UPDATE ON multi_agent_documents
    FOR EACH ROW
    EXECUTE FUNCTION update_documents_updated_at();

-- Criar bucket no Storage se não existir (executar manualmente no dashboard)
-- INSERT INTO storage.buckets (id, name, public) VALUES ('tenant-documents', 'tenant-documents', false);

COMMENT ON TABLE multi_agent_documents IS 'Documentos da Base de Conhecimento dos Agentes IA';
COMMENT ON COLUMN multi_agent_documents.status IS 'pending=aguardando, processing=vetorizando, completed=pronto para RAG, failed=erro';

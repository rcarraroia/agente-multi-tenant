import path from "path"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

export default defineConfig({
  plugins: [
    react(),
    // Plugin customizado para validação de ambiente
    {
      name: 'validate-environment',
      buildStart() {
        // Validar variáveis de ambiente obrigatórias
        const required = [
          'VITE_API_URL',
          'VITE_SUPABASE_URL', 
          'VITE_SUPABASE_ANON_KEY'
        ];

        const missing = required.filter(key => !process.env[key]);
        
        if (missing.length > 0) {
          throw new Error(`Variáveis de ambiente obrigatórias não definidas: ${missing.join(', ')}`);
        }

        // Validar URL do Supabase unificado
        const supabaseUrl = process.env.VITE_SUPABASE_URL;
        if (supabaseUrl && !supabaseUrl.includes('vtynmmtuvxreiwcxxlma')) {
          console.warn('⚠️ AVISO: VITE_SUPABASE_URL deve usar o banco unificado (vtynmmtuvxreiwcxxlma)');
        }

        // Log da configuração (sem secrets)
        console.log('✅ Validação de ambiente concluída');
        console.log(`   API URL: ${process.env.VITE_API_URL}`);
        console.log(`   Supabase URL: ${process.env.VITE_SUPABASE_URL}`);
        console.log(`   Ambiente: ${process.env.VITE_ENVIRONMENT || 'auto-detectado'}`);
      }
    }
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  // Configurações específicas para produção
  build: {
    sourcemap: process.env.VITE_ENVIRONMENT !== 'production',
    minify: process.env.VITE_ENVIRONMENT === 'production' ? 'esbuild' : false,
  },
  // Configurações do servidor de desenvolvimento
  server: {
    port: 3000,
    host: true, // Permite acesso externo
  },
  // Configurações de preview (produção local)
  preview: {
    port: 3000,
    host: true,
  }
})

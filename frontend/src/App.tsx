import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import Settings from './pages/Settings';
import WhatsAppConnection from './pages/WhatsAppConnection';
import KnowledgeBase from './pages/KnowledgeBase';
import CRMKanban from './pages/CRMKanban';
import ChatMonitor from './pages/ChatMonitor';
import { Toaster } from './components/ui/toaster';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Router>
          <Routes>
            {/* Protected Routes */}
            <Route element={<ProtectedRoute />}>
              <Route
                path="/"
                element={
                  <div className="p-8 h-screen w-full flex items-center justify-center">
                    <div className="glass-card p-12 rounded-3xl max-w-2xl text-center space-y-6 animate-in fade-in zoom-in duration-500">
                      <h1 className="text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-accent">
                        Bem-vindo ao Portal do Agente IA
                      </h1>
                      <p className="text-muted-foreground text-lg">
                        Seu assistente multi-tenant está configurado e pronto para agir.
                      </p>
                      <div className="flex justify-center gap-4">
                        <button
                          onClick={() => window.location.href = '/whatsapp'}
                          className="glass-button px-6 py-3 rounded-full font-medium"
                        >
                          Conectar WhatsApp
                        </button>
                        <button
                          onClick={() => window.location.href = '/settings'}
                          className="glass-button px-6 py-3 rounded-full font-medium border-primary/20"
                        >
                          Configurações
                        </button>
                      </div>
                    </div>
                  </div>
                }
              />
              <Route path="/settings" element={<Settings />} />
              <Route path="/whatsapp" element={<WhatsAppConnection />} />
              <Route path="/knowledge" element={<KnowledgeBase />} />
              <Route path="/crm" element={<CRMKanban />} />
              <Route path="/chats" element={<ChatMonitor />} />
            </Route>

            {/* Fallback */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Router>
        <Toaster />
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;

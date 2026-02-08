// Build trigger: 2026-02-07 22:30
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';
import DashboardLayout from './components/layout/DashboardLayout';
import HomePage from './pages/Home/HomePage';
import Settings from './pages/Settings';
import WhatsAppConnection from './pages/WhatsAppConnection';
import KnowledgeBase from './pages/KnowledgeBase';
import CRMKanban from './pages/CRMKanban';
import ChatMonitor from './pages/ChatMonitor';
import { ToastProvider } from './components/ui/toast';
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
        <ToastProvider>
          <Router>
            <Routes>
              {/* Protected Routes */}
              <Route element={<ProtectedRoute />}>
                <Route element={<DashboardLayout />}>
                  <Route path="/" element={<HomePage />} />
                  <Route path="/settings" element={<Settings />} />
                  <Route path="/whatsapp" element={<WhatsAppConnection />} />
                  <Route path="/knowledge" element={<KnowledgeBase />} />
                  <Route path="/crm" element={<CRMKanban />} />
                  <Route path="/chats" element={<ChatMonitor />} />
                </Route>
              </Route>

              {/* Fallback */}
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Router>
        </ToastProvider>
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;

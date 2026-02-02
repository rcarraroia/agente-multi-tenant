import { Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface ProtectedRouteProps {
    redirectPath?: string;
}

const ProtectedRoute = ({ redirectPath = 'https://slimquality.com.br/login' }: ProtectedRouteProps) => {
    const { user, loading, isSubscribed } = useAuth();

    if (loading) {
        return (
            <div className="h-screen w-screen flex items-center justify-center bg-background">
                <div className="flex flex-col items-center gap-4">
                    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
                    <p className="text-muted-foreground animate-pulse">Verificando acesso...</p>
                </div>
            </div>
        );
    }

    if (!user) {
        // Redirect to main panel login with returnUrl
        const currentUrl = window.location.href;
        const baseLoginUrl = redirectPath.endsWith('/') ? redirectPath.slice(0, -1) : redirectPath;
        window.location.href = `${baseLoginUrl}?returnUrl=${encodeURIComponent(currentUrl)}`;
        return null;
    }

    if (!isSubscribed) {
        // Redirect to the tools page in the main panel to sign up
        window.location.href = 'https://slimquality.com.br/afiliados/dashboard/ferramentas-ia';
        return null;
    }

    return <Outlet />;
};

export default ProtectedRoute;

import { Outlet } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface ProtectedRouteProps {
    redirectPath?: string;
}

const ProtectedRoute = ({ redirectPath }: ProtectedRouteProps) => {
    const { user, loading, isSubscribed } = useAuth();

    // URLs configuráveis via environment variables
    const slimQualityUrl = import.meta.env.VITE_SLIM_QUALITY_URL || 'https://slimquality.com.br';
    const defaultRedirectPath = `${slimQualityUrl}/login`;
    const toolsPageUrl = `${slimQualityUrl}/afiliados/dashboard/ferramentas-ia`;

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
        const loginUrl = redirectPath || defaultRedirectPath;
        // Clean redirectPath to ensure no trailing slash before appending query params
        const cleanBaseUrl = loginUrl.replace(/\/$/, "");
        window.location.href = `${cleanBaseUrl}?returnUrl=${encodeURIComponent(currentUrl)}`;
        return null;
    }

    if (!isSubscribed) {
        // Redirect to the tools page in the main panel to sign up
        window.location.href = toolsPageUrl;
        return null;
    }

    return <Outlet />;
};

export default ProtectedRoute;

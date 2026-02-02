import React from 'react';
import { Outlet } from 'react-router-dom';
import { Sidebar } from './Sidebar';

const DashboardLayout: React.FC = () => {
    return (
        <div className="flex min-h-screen bg-background">
            <Sidebar />
            <main className="flex-1 ml-64 min-h-screen relative overflow-y-auto bg-gradient-to-br from-background to-background/50">
                {/* Efeito de luz de fundo */}
                <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-primary/5 rounded-full blur-[120px] pointer-events-none" />
                <div className="absolute bottom-0 left-0 w-[300px] h-[300px] bg-accent/5 rounded-full blur-[100px] pointer-events-none" />

                <div className="relative z-10">
                    <Outlet />
                </div>
            </main>
        </div>
    );
};

export default DashboardLayout;

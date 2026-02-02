import React from 'react';
import { Bot, Zap, Shield, MessageSquare, LayoutGrid } from 'lucide-react';

const HomePage: React.FC = () => {
    return (
        <div className="p-8 space-y-8 animate-in fade-in duration-500">
            {/* Header / Hero Section */}
            <div className="glass-card p-10 rounded-3xl overflow-hidden relative">
                <div className="absolute top-0 right-0 p-8 opacity-10">
                    <Bot size={120} />
                </div>

                <div className="max-w-2xl space-y-4 relative z-10">
                    <h1 className="text-4xl font-bold tracking-tight">
                        Bem-vindo ao seu <span className="text-primary italic">Dashboard IA</span>
                    </h1>
                    <p className="text-muted-foreground text-lg leading-relaxed">
                        Seu assistente virtual está conectado e pronto para converter leads em vendas 24/7.
                        Gerencie suas conversas, etapas do funil e base de conhecimento em um só lugar.
                    </p>
                </div>
            </div>

            {/* Quick Stats / Overview */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="glass-card p-6 rounded-2xl border-l-4 border-l-primary flex items-center gap-4 transition-all hover:translate-y-[-4px]">
                    <div className="p-3 rounded-xl bg-primary/10">
                        <Zap className="w-6 h-6 text-primary" />
                    </div>
                    <div>
                        <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Status do Agente</p>
                        <p className="text-xl font-bold">Ativo & Online</p>
                    </div>
                </div>

                <div className="glass-card p-6 rounded-2xl border-l-4 border-l-success flex items-center gap-4 transition-all hover:translate-y-[-4px]">
                    <div className="p-3 rounded-xl bg-success/10">
                        <MessageSquare className="w-6 h-6 text-success" />
                    </div>
                    <div>
                        <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Sessões Recentes</p>
                        <p className="text-xl font-bold">Monitorando</p>
                    </div>
                </div>

                <div className="glass-card p-6 rounded-2xl border-l-4 border-l-accent flex items-center gap-4 transition-all hover:translate-y-[-4px]">
                    <div className="p-3 rounded-xl bg-accent/10">
                        <LayoutGrid className="w-6 h-6 text-accent" />
                    </div>
                    <div>
                        <p className="text-xs text-muted-foreground uppercase tracking-wider font-semibold">Funil CRM</p>
                        <p className="text-xl font-bold">Integrado</p>
                    </div>
                </div>
            </div>

            {/* Feature Access Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-8 mt-12">
                <div className="space-y-4">
                    <h3 className="text-xl font-semibold flex items-center gap-2">
                        <Shield className="w-5 h-5 text-primary" />
                        Acesso Rápido
                    </h3>
                    <div className="space-y-3">
                        <p className="text-sm text-muted-foreground">
                            Utilize o menu lateral para gerenciar as funcionalidades do seu agente.
                            Se é sua primeira vez, comece conectando seu WhatsApp.
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default HomePage;

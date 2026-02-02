import React from 'react';
import { NavLink } from 'react-router-dom';
import {
    LayoutDashboard,
    MessageSquare,
    LayoutGrid,
    BookOpen,
    Phone,
    Settings,
    LogOut,
    Bot
} from 'lucide-react';
import { supabase } from '../../lib/supabase';

const menuItems = [
    { icon: LayoutDashboard, label: 'Início', path: '/' },
    { icon: MessageSquare, label: 'Conversas', path: '/chats' },
    { icon: LayoutGrid, label: 'Funil CRM', path: '/crm' },
    { icon: BookOpen, label: 'Conhecimento', path: '/knowledge' },
    { icon: Phone, label: 'Conexão WhatsApp', path: '/whatsapp' },
    { icon: Settings, label: 'Configurações', path: '/settings' },
];

export const Sidebar: React.FC = () => {
    const handleLogout = async () => {
        await supabase.auth.signOut();
        window.location.href = 'https://slimquality.com.br/login';
    };

    return (
        <div className="w-64 h-screen border-r border-primary/10 bg-background/50 backdrop-blur-xl flex flex-col fixed left-0 top-0 z-50">
            <div className="p-6 flex items-center gap-3">
                <div className="p-2 rounded-xl bg-primary/20 border border-primary/30">
                    <Bot className="w-6 h-6 text-primary" />
                </div>
                <span className="font-bold text-lg tracking-tight">Agente IA</span>
            </div>

            <nav className="flex-1 px-4 py-4 space-y-2 overflow-y-auto">
                {menuItems.map((item) => (
                    <NavLink
                        key={item.path}
                        to={item.path}
                        className={({ isActive }) => `
                            flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200
                            ${isActive
                                ? 'bg-primary/20 text-primary border border-primary/20 shadow-[0_0_15px_rgba(var(--primary-rgb),0.1)]'
                                : 'text-muted-foreground hover:bg-primary/10 hover:text-foreground'
                            }
                        `}
                    >
                        <item.icon className="w-5 h-5" />
                        <span className="font-medium">{item.label}</span>
                    </NavLink>
                ))}
            </nav>

            <div className="p-4 border-t border-primary/10">
                <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-3 px-4 py-3 rounded-xl text-muted-foreground hover:bg-destructive/10 hover:text-destructive transition-all duration-200"
                >
                    <LogOut className="w-5 h-5" />
                    <span className="font-medium">Sair</span>
                </button>
            </div>
        </div>
    );
};

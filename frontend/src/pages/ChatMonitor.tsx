import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import api from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import {
    MessageSquare,
    Search,
    Phone,
    User,
    Clock,
    RefreshCw,
    Filter
} from 'lucide-react';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';

interface Conversation {
    id: string;
    phone_number: string;
    lead_name: string | null;
    status: string;
    updated_at: string;
}

interface Message {
    id: string;
    role: 'user' | 'assistant';
    content: string;
    created_at: string;
}

const ChatMonitor = () => {
    const [selectedConversation, setSelectedConversation] = useState<string | null>(null);
    const [searchTerm, setSearchTerm] = useState('');

    // 1. Buscar conversas
    const { data: conversations, isLoading: convsLoading } = useQuery<Conversation[]>({
        queryKey: ['conversations'],
        queryFn: async () => {
            const res = await api.get('/conversations');
            return res.data.data || [];
        }
    });

    // 2. Buscar mensagens da conversa selecionada
    const { data: messages, isLoading: msgsLoading } = useQuery<Message[]>({
        queryKey: ['messages', selectedConversation],
        queryFn: async () => {
            if (!selectedConversation) return [];
            const res = await api.get(`/conversations/${selectedConversation}/messages`);
            return res.data.data || [];
        },
        enabled: !!selectedConversation
    });

    // Filtrar conversas por busca
    const filteredConversations = conversations?.filter(c =>
        c.phone_number.includes(searchTerm) ||
        c.lead_name?.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const formatPhone = (phone: string) => {
        const cleaned = phone.replace(/\D/g, '');
        if (cleaned.length === 13) {
            return `+${cleaned.slice(0, 2)} (${cleaned.slice(2, 4)}) ${cleaned.slice(4, 9)}-${cleaned.slice(9)}`;
        }
        return phone;
    };

    return (
        <div className="h-screen flex overflow-hidden">
            {/* Sidebar - Lista de conversas */}
            <div className="w-80 border-r border-primary/10 bg-background/50 flex flex-col">
                {/* Header */}
                <div className="p-4 border-b border-primary/10">
                    <div className="flex items-center gap-2 mb-4">
                        <MessageSquare className="w-5 h-5 text-primary" />
                        <h2 className="font-bold text-lg">Conversas</h2>
                    </div>
                    <div className="relative">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                        <Input
                            placeholder="Buscar por nome ou telefone..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="pl-9 glass-input"
                        />
                    </div>
                </div>

                {/* Lista */}
                <div className="flex-1 overflow-y-auto">
                    {convsLoading ? (
                        <div className="p-8 text-center">
                            <RefreshCw className="w-6 h-6 animate-spin mx-auto text-primary/40" />
                        </div>
                    ) : filteredConversations?.length === 0 ? (
                        <div className="p-8 text-center text-muted-foreground text-sm">
                            Nenhuma conversa encontrada
                        </div>
                    ) : (
                        filteredConversations?.map((conv) => (
                            <button
                                key={conv.id}
                                onClick={() => setSelectedConversation(conv.id)}
                                className={`w-full p-4 text-left border-b border-primary/5 hover:bg-primary/5 transition-colors ${selectedConversation === conv.id ? 'bg-primary/10 border-l-2 border-l-primary' : ''
                                    }`}
                            >
                                <div className="flex items-center gap-3">
                                    <div className="p-2 rounded-full bg-primary/10">
                                        <User className="w-4 h-4 text-primary" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="font-medium text-sm truncate">
                                            {conv.lead_name || 'Lead sem nome'}
                                        </p>
                                        <p className="text-xs text-muted-foreground truncate">
                                            {formatPhone(conv.phone_number)}
                                        </p>
                                    </div>
                                    <div className={`w-2 h-2 rounded-full ${conv.status === 'active' ? 'bg-green-400' : 'bg-gray-400'
                                        }`} />
                                </div>
                            </button>
                        ))
                    )}
                </div>
            </div>

            {/* Chat view */}
            <div className="flex-1 flex flex-col">
                {!selectedConversation ? (
                    <div className="flex-1 flex items-center justify-center">
                        <div className="text-center space-y-4">
                            <MessageSquare className="w-16 h-16 mx-auto text-muted-foreground/20" />
                            <p className="text-muted-foreground">Selecione uma conversa para visualizar</p>
                        </div>
                    </div>
                ) : (
                    <>
                        {/* Chat Header */}
                        <div className="p-4 border-b border-primary/10 bg-background/50 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="p-2 rounded-full bg-primary/10">
                                    <User className="w-5 h-5 text-primary" />
                                </div>
                                <div>
                                    <p className="font-semibold">
                                        {conversations?.find(c => c.id === selectedConversation)?.lead_name || 'Lead'}
                                    </p>
                                    <p className="text-xs text-muted-foreground flex items-center gap-1">
                                        <Phone className="w-3 h-3" />
                                        {formatPhone(conversations?.find(c => c.id === selectedConversation)?.phone_number || '')}
                                    </p>
                                </div>
                            </div>
                            <span className="text-xs text-muted-foreground bg-muted/50 px-3 py-1 rounded-full">
                                Somente leitura
                            </span>
                        </div>

                        {/* Messages */}
                        <div className="flex-1 overflow-y-auto p-4 space-y-4">
                            {msgsLoading ? (
                                <div className="text-center py-8">
                                    <RefreshCw className="w-6 h-6 animate-spin mx-auto text-primary/40" />
                                </div>
                            ) : messages?.length === 0 ? (
                                <div className="text-center py-8 text-muted-foreground text-sm">
                                    Nenhuma mensagem ainda
                                </div>
                            ) : (
                                messages?.map((msg) => (
                                    <div
                                        key={msg.id}
                                        className={`flex ${msg.role === 'user' ? 'justify-start' : 'justify-end'}`}
                                    >
                                        <div className={`max-w-[70%] p-4 rounded-2xl ${msg.role === 'user'
                                                ? 'bg-muted/30 rounded-tl-none'
                                                : 'bg-primary/10 border border-primary/20 rounded-tr-none'
                                            }`}>
                                            <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                                            <p className="text-[10px] text-muted-foreground mt-2 flex items-center gap-1">
                                                <Clock className="w-3 h-3" />
                                                {format(new Date(msg.created_at), "HH:mm", { locale: ptBR })}
                                            </p>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>

                        {/* Read-only notice */}
                        <div className="p-4 border-t border-primary/10 bg-muted/20">
                            <p className="text-center text-xs text-muted-foreground">
                                Este é um monitor somente leitura. A interação é feita pelo WhatsApp.
                            </p>
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

export default ChatMonitor;

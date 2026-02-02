import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
    DndContext,
    DragOverlay,
    closestCorners,
    KeyboardSensor,
    PointerSensor,
    useSensor,
    useSensors,
} from '@dnd-kit/core';
import type { DragStartEvent, DragEndEvent } from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import api from '../services/api';
import { KanbanColumn } from '../components/crm/KanbanColumn';
import { KanbanCard } from '../components/crm/KanbanCard';
import { useToast } from '../hooks/use-toast';
import { Button } from '../components/ui/button';
import {
    LayoutGrid,
    Plus,
    Settings2,
    RefreshCw
} from 'lucide-react';

interface Stage {
    id: string;
    name: string;
    color: string;
    position: number;
}

interface Conversation {
    id: string;
    phone_number: string;
    lead_name: string | null;
    current_stage_id: string;
    status: string;
    updated_at: string;
}

interface FunnelWithStages {
    id: string;
    name: string;
    stages: Stage[];
}

const CRMKanban = () => {
    const { toast } = useToast();
    const queryClient = useQueryClient();
    const [activeCard, setActiveCard] = useState<Conversation | null>(null);

    const sensors = useSensors(
        useSensor(PointerSensor, {
            activationConstraint: { distance: 8 },
        }),
        useSensor(KeyboardSensor, {
            coordinateGetter: sortableKeyboardCoordinates,
        })
    );

    // 1. Buscar funil padrão com etapas
    const { data: funnel, isLoading: funnelLoading } = useQuery<FunnelWithStages | null>({
        queryKey: ['crm-funnel'],
        queryFn: async () => {
            const funnelsRes = await api.get('/crm/funnels');
            const defaultFunnel = funnelsRes.data.find((f: { is_default: boolean }) => f.is_default) || funnelsRes.data[0];

            if (!defaultFunnel) return null;

            const res = await api.get(`/crm/funnels/${defaultFunnel.id}`);
            return res.data;
        }
    });

    // 2. Buscar conversas
    const { data: conversations, isLoading: convsLoading } = useQuery<Conversation[]>({
        queryKey: ['crm-conversations'],
        queryFn: async () => {
            const res = await api.get('/conversations');
            return res.data.data || [];
        }
    });

    // 3. Mutation para mover conversa entre etapas
    const moveConversationMutation = useMutation({
        mutationFn: ({ conversationId, targetStageId }: { conversationId: string; targetStageId: string }) =>
            api.post(`/crm/conversations/${conversationId}/move`, { to_stage_id: targetStageId }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['crm-conversations'] });
            toast({
                title: "Movido!",
                description: "Conversa atualizada no funil.",
            });
        }
    });

    const handleDragStart = (event: DragStartEvent) => {
        const { active } = event;
        const conv = conversations?.find(c => c.id === active.id);
        if (conv) setActiveCard(conv);
    };

    const handleDragEnd = (event: DragEndEvent) => {
        const { active, over } = event;
        setActiveCard(null);

        if (!over) return;

        const activeConv = conversations?.find(c => c.id === active.id);
        if (!activeConv) return;

        const targetStageId = over.id as string;
        const isStage = funnel?.stages.some(s => s.id === targetStageId);

        if (isStage && activeConv.current_stage_id !== targetStageId) {
            moveConversationMutation.mutate({
                conversationId: activeConv.id,
                targetStageId,
            });
        }
    };

    const getConversationsByStage = (stageId: string) => {
        return conversations?.filter(c => c.current_stage_id === stageId) || [];
    };

    if (funnelLoading || convsLoading) {
        return (
            <div className="p-8 h-screen flex items-center justify-center">
                <RefreshCw className="w-8 h-8 animate-spin text-primary" />
            </div>
        );
    }

    if (!funnel) {
        return (
            <div className="p-8 h-screen flex items-center justify-center">
                <div className="glass-card p-8 text-center space-y-4">
                    <LayoutGrid className="w-12 h-12 mx-auto text-muted-foreground/30" />
                    <p className="text-lg font-medium">Nenhum funil configurado</p>
                    <Button className="glass-button">
                        <Plus className="w-4 h-4 mr-2" />
                        Criar Funil
                    </Button>
                </div>
            </div>
        );
    }

    return (
        <div className="h-screen flex flex-col overflow-hidden">
            {/* Header */}
            <div className="p-6 border-b border-primary/10 bg-background/50 backdrop-blur-sm flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-3 rounded-2xl bg-primary/10 border border-primary/20">
                        <LayoutGrid className="w-6 h-6 text-primary" />
                    </div>
                    <div>
                        <h1 className="text-2xl font-bold">{funnel.name}</h1>
                        <p className="text-sm text-muted-foreground">
                            {funnel.stages.length} etapas • {conversations?.length || 0} conversas
                        </p>
                    </div>
                </div>
                <Button variant="outline" className="gap-2 border-primary/20">
                    <Settings2 className="w-4 h-4" />
                    Editar Funil
                </Button>
            </div>

            {/* Kanban Board */}
            <div className="flex-1 overflow-x-auto p-6">
                <DndContext
                    sensors={sensors}
                    collisionDetection={closestCorners}
                    onDragStart={handleDragStart}
                    onDragEnd={handleDragEnd}
                >
                    <div className="flex gap-4 h-full min-w-max">
                        {funnel.stages
                            .sort((a, b) => a.position - b.position)
                            .map((stage) => (
                                <KanbanColumn
                                    key={stage.id}
                                    stage={stage}
                                    conversations={getConversationsByStage(stage.id)}
                                />
                            ))}

                        <div className="w-72 flex-shrink-0">
                            <Button
                                variant="ghost"
                                className="w-full h-16 border-2 border-dashed border-primary/20 hover:border-primary/40 hover:bg-primary/5 rounded-2xl"
                            >
                                <Plus className="w-5 h-5 mr-2" />
                                Nova Etapa
                            </Button>
                        </div>
                    </div>

                    <DragOverlay>
                        {activeCard ? <KanbanCard conversation={activeCard} isDragging /> : null}
                    </DragOverlay>
                </DndContext>
            </div>
        </div>
    );
};

export default CRMKanban;

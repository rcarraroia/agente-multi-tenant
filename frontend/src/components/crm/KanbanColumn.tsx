import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { KanbanCard } from './KanbanCard';

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

interface KanbanColumnProps {
    stage: Stage;
    conversations: Conversation[];
}

export const KanbanColumn = ({ stage, conversations }: KanbanColumnProps) => {
    const { setNodeRef, isOver } = useDroppable({
        id: stage.id,
    });

    return (
        <div
            ref={setNodeRef}
            className={`w-72 flex-shrink-0 flex flex-col h-full transition-all duration-200 ${isOver ? 'scale-[1.02]' : ''
                }`}
        >
            {/* Header da coluna */}
            <div
                className="p-4 rounded-t-2xl border border-b-0 border-primary/10 bg-background/50 backdrop-blur-sm"
                style={{ borderTopColor: stage.color }}
            >
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <div
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: stage.color }}
                        />
                        <h3 className="font-semibold text-sm">{stage.name}</h3>
                    </div>
                    <span className="text-xs text-muted-foreground bg-muted/50 px-2 py-1 rounded-full">
                        {conversations.length}
                    </span>
                </div>
            </div>

            {/* Cards container */}
            <div
                className={`flex-1 p-3 space-y-3 rounded-b-2xl border border-t-0 border-primary/10 bg-muted/20 overflow-y-auto transition-colors ${isOver ? 'bg-primary/5 border-primary/30' : ''
                    }`}
            >
                <SortableContext
                    items={conversations.map(c => c.id)}
                    strategy={verticalListSortingStrategy}
                >
                    {conversations.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground/50 text-sm">
                            Nenhuma conversa
                        </div>
                    ) : (
                        conversations.map((conversation) => (
                            <KanbanCard key={conversation.id} conversation={conversation} />
                        ))
                    )}
                </SortableContext>
            </div>
        </div>
    );
};

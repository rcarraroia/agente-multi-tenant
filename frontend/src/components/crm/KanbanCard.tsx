import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { format } from 'date-fns';
import { ptBR } from 'date-fns/locale';
import { MessageSquare, User, Phone, Clock } from 'lucide-react';

interface Conversation {
    id: string;
    phone_number: string;
    lead_name: string | null;
    current_stage_id: string;
    status: string;
    updated_at: string;
}

interface KanbanCardProps {
    conversation: Conversation;
    isDragging?: boolean;
}

export const KanbanCard = ({ conversation, isDragging = false }: KanbanCardProps) => {
    const {
        attributes,
        listeners,
        setNodeRef,
        transform,
        transition,
        isDragging: isSortableDragging,
    } = useSortable({ id: conversation.id });

    const style = {
        transform: CSS.Transform.toString(transform),
        transition,
    };

    const formatPhone = (phone: string) => {
        // Formata número brasileiro
        const cleaned = phone.replace(/\D/g, '');
        if (cleaned.length === 13) {
            return `+${cleaned.slice(0, 2)} (${cleaned.slice(2, 4)}) ${cleaned.slice(4, 9)}-${cleaned.slice(9)}`;
        }
        return phone;
    };

    return (
        <div
            ref={setNodeRef}
            style={style}
            {...attributes}
            {...listeners}
            className={`
        glass-card p-4 rounded-xl cursor-grab active:cursor-grabbing
        border border-primary/10 hover:border-primary/30
        transition-all duration-200 hover:shadow-lg hover:shadow-primary/5
        ${isDragging || isSortableDragging ? 'opacity-50 shadow-xl rotate-2' : ''}
      `}
        >
            {/* Header do card */}
            <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-primary/10 border border-primary/20">
                        <User className="w-3 h-3 text-primary" />
                    </div>
                    <div>
                        <p className="font-medium text-sm leading-tight">
                            {conversation.lead_name || 'Lead sem nome'}
                        </p>
                        <div className="flex items-center gap-1 text-xs text-muted-foreground">
                            <Phone className="w-3 h-3" />
                            <span>{formatPhone(conversation.phone_number)}</span>
                        </div>
                    </div>
                </div>

                {/* Status indicator */}
                <div className={`w-2 h-2 rounded-full ${conversation.status === 'active' ? 'bg-green-400' :
                        conversation.status === 'waiting_human' ? 'bg-yellow-400' : 'bg-gray-400'
                    }`} />
            </div>

            {/* Footer */}
            <div className="flex items-center justify-between pt-2 border-t border-primary/5">
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                    <Clock className="w-3 h-3" />
                    <span>
                        {format(new Date(conversation.updated_at), "dd MMM 'às' HH:mm", { locale: ptBR })}
                    </span>
                </div>
                <div className="flex items-center gap-1 text-xs text-primary/60">
                    <MessageSquare className="w-3 h-3" />
                    <span>Ver</span>
                </div>
            </div>
        </div>
    );
};

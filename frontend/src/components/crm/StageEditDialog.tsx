import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../../services/api';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { useToast } from '../../hooks/use-toast';
import { Palette, Trash2 } from 'lucide-react';

interface Stage {
    id: string;
    name: string;
    color: string;
    position: number;
}

interface StageEditDialogProps {
    stage: Stage | null;
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

const PRESET_COLORS = [
    '#3B82F6', // Azul
    '#8B5CF6', // Roxo
    '#EC4899', // Rosa
    '#F59E0B', // Amarelo
    '#10B981', // Verde
    '#EF4444', // Vermelho
    '#6B7280', // Cinza
    '#06B6D4', // Ciano
];

export const StageEditDialog = ({ stage, open, onOpenChange }: StageEditDialogProps) => {
    const { toast } = useToast();
    const queryClient = useQueryClient();
    const [name, setName] = useState(stage?.name || '');
    const [color, setColor] = useState(stage?.color || '#3B82F6');

    // Update quando stage muda
    useState(() => {
        if (stage) {
            setName(stage.name);
            setColor(stage.color);
        }
    });

    // Mutation para atualizar etapa
    const updateMutation = useMutation({
        mutationFn: () => api.patch(`/crm/stages/${stage?.id}`, { name, color }),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['crm-funnel'] });
            onOpenChange(false);
            toast({
                title: "Etapa atualizada",
                description: "As alterações foram salvas.",
            });
        }
    });

    // Mutation para deletar etapa
    const deleteMutation = useMutation({
        mutationFn: () => api.delete(`/crm/stages/${stage?.id}`),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['crm-funnel'] });
            onOpenChange(false);
            toast({
                title: "Etapa removida",
                description: "A etapa foi excluída do funil.",
            });
        }
    });

    return (
        <Dialog open={open} onOpenChange={onOpenChange}>
            <DialogContent className="glass-card border-primary/20 sm:max-w-md">
                <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                        <Palette className="w-5 h-5 text-primary" />
                        Editar Etapa
                    </DialogTitle>
                    <DialogDescription>
                        Personalize o nome e a cor desta etapa do funil.
                    </DialogDescription>
                </DialogHeader>

                <div className="space-y-6 py-4">
                    {/* Nome */}
                    <div className="space-y-2">
                        <Label htmlFor="stage-name">Nome da Etapa</Label>
                        <Input
                            id="stage-name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="Ex: Proposta Enviada"
                            className="glass-input"
                        />
                    </div>

                    {/* Cor */}
                    <div className="space-y-2">
                        <Label>Cor</Label>
                        <div className="flex flex-wrap gap-2">
                            {PRESET_COLORS.map((presetColor) => (
                                <button
                                    key={presetColor}
                                    type="button"
                                    onClick={() => setColor(presetColor)}
                                    className={`w-8 h-8 rounded-full border-2 transition-all ${color === presetColor
                                            ? 'border-white scale-110 shadow-lg'
                                            : 'border-transparent hover:scale-105'
                                        }`}
                                    style={{ backgroundColor: presetColor }}
                                />
                            ))}
                        </div>
                    </div>

                    {/* Preview */}
                    <div className="p-4 rounded-xl bg-muted/30 border border-primary/10">
                        <p className="text-xs text-muted-foreground mb-2">Prévia:</p>
                        <div className="flex items-center gap-2">
                            <div
                                className="w-3 h-3 rounded-full"
                                style={{ backgroundColor: color }}
                            />
                            <span className="font-semibold text-sm">{name || 'Nome da etapa'}</span>
                        </div>
                    </div>
                </div>

                <DialogFooter className="flex justify-between">
                    <Button
                        variant="destructive"
                        size="sm"
                        onClick={() => deleteMutation.mutate()}
                        disabled={deleteMutation.isPending}
                        className="bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30"
                    >
                        <Trash2 className="w-4 h-4 mr-2" />
                        Excluir
                    </Button>
                    <div className="flex gap-2">
                        <Button variant="outline" onClick={() => onOpenChange(false)}>
                            Cancelar
                        </Button>
                        <Button
                            onClick={() => updateMutation.mutate()}
                            disabled={updateMutation.isPending || !name.trim()}
                            className="glass-button"
                        >
                            Salvar
                        </Button>
                    </div>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
};

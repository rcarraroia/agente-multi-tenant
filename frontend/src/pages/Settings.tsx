import { useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle
} from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Textarea } from '../components/ui/textarea';
import { Button } from '../components/ui/button';
import { Switch } from '../components/ui/switch';
import { useToast } from '../hooks/use-toast';
import { Settings as SettingsIcon, Brain, Sparkles, Save } from 'lucide-react';

interface SettingsForm {
    agent_name: string;
    agent_personality: string;
    knowledge_enabled: boolean;
}

const Settings = () => {
    const { toast } = useToast();
    const queryClient = useQueryClient();
    const { register, handleSubmit, setValue, watch } = useForm<SettingsForm>({
        defaultValues: {
            agent_name: 'BIA',
            agent_personality: '',
            knowledge_enabled: true,
        }
    });

    const knowledgeEnabled = watch('knowledge_enabled');

    // 1. Fetch current settings
    const { data: tenantData, isLoading } = useQuery({
        queryKey: ['tenant-me'],
        queryFn: async () => {
            const res = await api.get('/tenants/me');
            return res.data.data;
        }
    });

    // 2. Set form values when data arrives
    useEffect(() => {
        if (tenantData) {
            setValue('agent_name', tenantData.agent_name || 'BIA');
            setValue('agent_personality', tenantData.agent_personality || '');
            setValue('knowledge_enabled', tenantData.knowledge_enabled ?? true);
        }
    }, [tenantData, setValue]);

    // 3. Update mutation
    const mutation = useMutation({
        mutationFn: (data: SettingsForm) => api.patch('/tenants/me', data),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['tenant-me'] });
            toast({
                title: "Sucesso!",
                description: "Configurações do Agente atualizadas corretamente.",
            });
        },
        onError: () => {
            toast({
                variant: "destructive",
                title: "Erro",
                description: "Não foi possível salvar as configurações.",
            });
        }
    });

    const onSubmit = (data: SettingsForm) => {
        mutation.mutate(data);
    };

    if (isLoading) {
        return (
            <div className="p-8 flex items-center justify-center min-h-[400px]">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            </div>
        );
    }

    return (
        <div className="p-8 max-w-4xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center gap-3">
                <div className="p-3 rounded-2xl bg-primary/10 border border-primary/20">
                    <SettingsIcon className="w-6 h-6 text-primary" />
                </div>
                <div>
                    <h1 className="text-3xl font-bold">Configurações do Agente</h1>
                    <p className="text-muted-foreground">Personalize a identidade e o comportamento da sua IA.</p>
                </div>
            </div>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
                <Card className="glass-card overflow-hidden border-none">
                    <CardHeader className="border-b border-primary/10">
                        <div className="flex items-center gap-2">
                            <Sparkles className="w-5 h-5 text-accent" />
                            <CardTitle>Identidade & Nome</CardTitle>
                        </div>
                        <CardDescription>Como seu cliente deve chamar sua IA?</CardDescription>
                    </CardHeader>
                    <CardContent className="p-6 space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="agent_name">Nome do Agente</Label>
                            <Input
                                id="agent_name"
                                className="bg-background/50 border-primary/20 focus:border-primary transition-colors"
                                placeholder="Ex: BIA, Assistente Slim..."
                                {...register('agent_name', { required: true })}
                            />
                        </div>
                    </CardContent>
                </Card>

                <Card className="glass-card overflow-hidden border-none">
                    <CardHeader className="border-b border-primary/10">
                        <div className="flex items-center gap-2">
                            <Brain className="w-5 h-5 text-accent" />
                            <CardTitle>Personalidade e Instruções</CardTitle>
                        </div>
                        <CardDescription>Defina o tom de voz e como o Agente deve se comportar.</CardDescription>
                    </CardHeader>
                    <CardContent className="p-6 space-y-4">
                        <div className="space-y-2">
                            <Label htmlFor="agent_personality">Instruções de Comportamento</Label>
                            <Textarea
                                id="agent_personality"
                                className="min-h-[200px] bg-background/50 border-primary/20 focus:border-primary transition-colors resize-none"
                                placeholder="Ex: Você é um assistente de vendas gentil da Slim Quality. Seu objetivo é ajudar o cliente a escolher o melhor colchão..."
                                {...register('agent_personality')}
                            />
                            <p className="text-xs text-muted-foreground">
                                Dica: Seja específico sobre o que o Agente pode ou não responder.
                            </p>
                        </div>
                    </CardContent>
                </Card>

                <Card className="glass-card overflow-hidden border-none">
                    <CardHeader className="border-b border-primary/10">
                        <div className="flex items-center gap-2">
                            <Brain className="w-5 h-5 text-accent" />
                            <CardTitle>Inteligência Aplicada</CardTitle>
                        </div>
                    </CardHeader>
                    <CardContent className="p-6 flex items-center justify-between">
                        <div className="space-y-0.5">
                            <Label>Base de Conhecimento</Label>
                            <p className="text-sm text-muted-foreground">
                                Permitir que o Agente use documentos e produtos externos para responder.
                            </p>
                        </div>
                        <Switch
                            checked={knowledgeEnabled}
                            onCheckedChange={(checked) => setValue('knowledge_enabled', checked)}
                        />
                    </CardContent>
                </Card>

                <div className="flex justify-end pt-4">
                    <Button
                        type="submit"
                        disabled={mutation.isPending}
                        className="px-8 py-6 rounded-2xl glass-button text-lg gap-2"
                    >
                        {mutation.isPending ? (
                            <span className="animate-spin rounded-full h-4 w-4 border-b-2 border-current"></span>
                        ) : (
                            <Save className="w-5 h-5" />
                        )}
                        Salvar Alterações
                    </Button>
                </div>
            </form>
        </div>
    );
};

export default Settings;

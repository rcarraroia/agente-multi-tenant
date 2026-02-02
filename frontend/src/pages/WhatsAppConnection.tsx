import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle
} from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Skeleton } from '../components/ui/skeleton';
import { Alert, AlertDescription, AlertTitle } from '../components/ui/alert';
import { useToast } from '../hooks/use-toast';
import {
    MessageSquare,
    QrCode,
    RefreshCw,
    Power,
    CheckCircle2,
    Smartphone
} from 'lucide-react';

interface QRCodeData {
    qrcode: string | null;
    type: string;
    message?: string;
}

const WhatsAppConnection = () => {
    const { toast } = useToast();
    const queryClient = useQueryClient();
    const [pollingActive, setPollingActive] = useState(false);

    // 1. Fetch Connection Status
    const { data: statusData, isLoading: statusLoading, refetch: refetchStatus } = useQuery({
        queryKey: ['whatsapp-status'],
        queryFn: async () => {
            const res = await api.get('/whatsapp/status');
            return res.data;
        },
        refetchInterval: pollingActive ? 5000 : false, // Poll every 5s if connecting
    });

    // 2. Fetch QR Code
    const { data: qrData, isLoading: qrLoading, refetch: refetchQR } = useQuery<QRCodeData>({
        queryKey: ['whatsapp-qrcode'],
        queryFn: async () => {
            const res = await api.get('/whatsapp/qrcode');
            return res.data;
        },
        enabled: statusData?.status === 'waiting_qr' || statusData?.status === 'DISCONNECTED',
    });

    // 3. Mutation: Connect/Create Instance
    const connectMutation = useMutation({
        mutationFn: () => api.post('/whatsapp/connect'),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['whatsapp-status'] });
            setPollingActive(true);
            toast({
                title: "Instância Criada",
                description: "Aguardando geração do QR Code...",
            });
        }
    });

    // 4. Mutation: Disconnect (To be implemented in backend if not exists)
    const disconnectMutation = useMutation({
        mutationFn: () => api.post('/whatsapp/disconnect'), // Placeholder for Etapa 5 logic
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['whatsapp-status'] });
            setPollingActive(false);
            toast({
                title: "Desconectado",
                description: "A instância do WhatsApp foi removida.",
            });
        }
    });

    useEffect(() => {
        if (statusData?.status === 'CONNECTED') {
            setPollingActive(false);
        }
    }, [statusData]);

    const isConnected = statusData?.status === 'CONNECTED';
    const isWaitingQR = statusData?.status === 'waiting_qr' || (statusData?.status === 'DISCONNECTED' && qrData?.qrcode);

    return (
        <div className="p-8 max-w-4xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center gap-3">
                <div className="p-3 rounded-2xl bg-primary/10 border border-primary/20">
                    <MessageSquare className="w-6 h-6 text-primary" />
                </div>
                <div>
                    <h1 className="text-3xl font-bold">Conexão WhatsApp</h1>
                    <p className="text-muted-foreground">Conecte o WhatsApp do seu Agente para começar a atender.</p>
                </div>
            </div>

            <div className="grid md:grid-cols-3 gap-6">
                {/* Status Card */}
                <Card className="glass-card border-none md:col-span-1">
                    <CardHeader>
                        <CardTitle className="text-lg flex items-center gap-2">
                            <Smartphone className="w-5 h-5" />
                            Status
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                        <div className="flex flex-col items-center gap-4 py-4">
                            {statusLoading ? (
                                <Skeleton className="h-10 w-24 rounded-full" />
                            ) : (
                                <Badge
                                    variant={isConnected ? "default" : "secondary"}
                                    className={`text-sm px-4 py-1 rounded-full ${isConnected ? 'bg-green-500/20 text-green-400 border-green-500/30' : 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'}`}
                                >
                                    {isConnected ? 'Conectado' : 'Desconectado'}
                                </Badge>
                            )}

                            <div className="text-center">
                                <p className="text-xs text-muted-foreground uppercase tracking-widest font-bold mb-1">Instância</p>
                                <p className="font-mono text-sm">{statusData?.instance_name || 'Agente_Principal'}</p>
                            </div>
                        </div>

                        <Button
                            variant="outline"
                            className="w-full border-primary/20 hover:bg-primary/10"
                            onClick={() => refetchStatus()}
                            disabled={statusLoading}
                        >
                            <RefreshCw className={`w-4 h-4 mr-2 ${statusLoading ? 'animate-spin' : ''}`} />
                            Atualizar Status
                        </Button>
                    </CardContent>
                </Card>

                {/* Action Card */}
                <Card className="glass-card border-none md:col-span-2">
                    <CardHeader>
                        <CardTitle className="text-lg flex items-center gap-2">
                            <QrCode className="w-5 h-5 font-bold" />
                            Conectar WhatsApp
                        </CardTitle>
                        <CardDescription>Siga as instruções para parear o dispositivo.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        {!isConnected && !isWaitingQR && (
                            <div className="flex flex-col items-center justify-center p-8 border-2 border-dashed border-primary/20 rounded-2xl space-y-4">
                                <Power className="w-12 h-12 text-muted-foreground/30" />
                                <p className="text-sm text-muted-foreground text-center">Nenhuma instância ativa. Clique para gerar um código.</p>
                                <Button
                                    onClick={() => connectMutation.mutate()}
                                    className="glass-button"
                                    disabled={connectMutation.isPending}
                                >
                                    Gerar QR Code
                                </Button>
                            </div>
                        )}

                        {isWaitingQR && !isConnected && (
                            <div className="flex flex-col items-center space-y-6">
                                <div className="relative p-4 bg-white rounded-2xl border-4 border-primary/20">
                                    {qrLoading ? (
                                        <Skeleton className="w-[250px] h-[250px]" />
                                    ) : qrData?.qrcode ? (
                                        <img
                                            src={qrData.qrcode}
                                            alt="WhatsApp QR Code"
                                            className="w-[250px] h-[250px] shadow-2xl"
                                        />
                                    ) : (
                                        <div className="w-[250px] h-[250px] flex items-center justify-center text-center p-4">
                                            <p className="text-sm text-black font-medium">QR Code não disponível. Tente novamente.</p>
                                        </div>
                                    )}
                                </div>

                                <div className="space-y-2 text-center">
                                    <p className="font-medium text-primary">Instruções:</p>
                                    <ol className="text-sm text-muted-foreground space-y-1 text-left list-decimal list-inside">
                                        <li>Abra o WhatsApp no seu celular</li>
                                        <li>Toque em Mais opções (ou Configurações)</li>
                                        <li>Toque em Aparelhos conectados</li>
                                        <li>Toque em Conectar um aparelho e aponte para a tela</li>
                                    </ol>
                                </div>
                            </div>
                        )}

                        {isConnected && (
                            <Alert className="bg-green-500/10 border-green-500/20 text-green-400">
                                <CheckCircle2 className="h-4 w-4 text-green-400" />
                                <AlertTitle className="font-bold">O Agente está Online!</AlertTitle>
                                <AlertDescription>
                                    Sua conta do WhatsApp está pareada e o agente está processando mensagens em tempo real.
                                </AlertDescription>
                            </Alert>
                        )}
                    </CardContent>
                </Card>
            </div>

            {isConnected && (
                <div className="flex justify-center">
                    <Button
                        variant="destructive"
                        className="bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 px-8"
                        onClick={() => disconnectMutation.mutate()}
                        disabled={disconnectMutation.isPending}
                    >
                        <Power className="w-4 h-4 mr-2" />
                        Desconectar WhatsApp
                    </Button>
                </div>
            )}
        </div>
    );
};

export default WhatsAppConnection;

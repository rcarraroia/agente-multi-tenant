import { useState } from 'react';
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
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow
} from '../components/ui/table';
import { Progress } from '../components/ui/progress';
import { useToast } from '../hooks/use-toast';
import {
    BookOpen,
    FileText,
    Trash2,
    Plus,
    Loader2,
    FileSearch
} from 'lucide-react';
import { Label } from '../components/ui/label';
import { format } from 'date-fns';

interface Document {
    id: string;
    name: string;
    size_bytes: number;
    status: 'pending' | 'processing' | 'completed' | 'failed';
    created_at: string;
}

const KnowledgeBase = () => {
    const { toast } = useToast();
    const queryClient = useQueryClient();
    const [uploading, setUploading] = useState(false);
    const [uploadProgress, setUploadProgress] = useState(0);

    // 1. Fetch Documents
    const { data: documents, isLoading } = useQuery<Document[]>({
        queryKey: ['documents'],
        queryFn: async () => {
            const res = await api.get('/knowledge');
            return res.data.data;
        }
    });

    // 2. Upload Mutation
    const uploadMutation = useMutation({
        mutationFn: async (file: File) => {
            const formData = new FormData();
            formData.append('file', file);
            return api.post('/knowledge/upload', formData, {
                onUploadProgress: (progressEvent) => {
                    const percent = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1));
                    setUploadProgress(percent);
                }
            });
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] });
            setUploading(false);
            setUploadProgress(0);
            toast({
                title: "Sucesso!",
                description: "Documento enviado para processamento.",
            });
        },
        onError: () => {
            setUploading(false);
            setUploadProgress(0);
            toast({
                variant: "destructive",
                title: "Erro",
                description: "Falha ao enviar arquivo.",
            });
        }
    });

    // 3. Delete Mutation
    const deleteMutation = useMutation({
        mutationFn: (id: string) => api.delete(`/knowledge/${id}`),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['documents'] });
            toast({
                title: "Removido",
                description: "Documento excluído da base de conhecimento.",
            });
        }
    });

    const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            setUploading(true);
            uploadMutation.mutate(file);
        }
    };

    const formatFileSize = (bytes: number) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    return (
        <div className="p-8 max-w-5xl mx-auto space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-500">
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="p-3 rounded-2xl bg-primary/10 border border-primary/20">
                        <BookOpen className="w-6 h-6 text-primary" />
                    </div>
                    <div>
                        <h1 className="text-3xl font-bold">Base de Conhecimento</h1>
                        <p className="text-muted-foreground">Adicione documentos para que o Agente aprenda sobre seu negócio.</p>
                    </div>
                </div>

                <div className="relative">
                    <input
                        type="file"
                        id="file-upload"
                        className="hidden"
                        onChange={handleFileUpload}
                        accept=".pdf,.txt,.doc,.docx"
                        disabled={uploading}
                    />
                    <Label htmlFor="file-upload">
                        <Button asChild className="glass-button gap-2 px-6 h-12 rounded-2xl cursor-pointer">
                            <span>
                                <Plus className="w-5 h-5" />
                                Adicionar Documento
                            </span>
                        </Button>
                    </Label>
                </div>
            </div>

            {uploading && (
                <Card className="glass-card border-primary/20 bg-primary/5 animate-pulse">
                    <CardContent className="p-6 space-y-4">
                        <div className="flex items-center justify-between text-sm">
                            <div className="flex items-center gap-2">
                                <Loader2 className="w-4 h-4 animate-spin text-primary" />
                                <span>Enviando arquivo...</span>
                            </div>
                            <span className="font-mono">{uploadProgress}%</span>
                        </div>
                        <Progress value={uploadProgress} className="h-2" />
                    </CardContent>
                </Card>
            )}

            <Card className="glass-card border-none overflow-hidden">
                <CardHeader className="border-b border-primary/10 bg-primary/5">
                    <CardTitle className="text-lg flex items-center gap-2">
                        <FileSearch className="w-5 h-5" />
                        Documentos Armazenados
                    </CardTitle>
                    <CardDescription>O Agente consultará estes arquivos para responder aos clientes.</CardDescription>
                </CardHeader>
                <CardContent className="p-0">
                    {isLoading ? (
                        <div className="p-12 text-center space-y-4">
                            <Loader2 className="w-8 h-8 animate-spin mx-auto text-primary/40" />
                            <p className="text-muted-foreground">Carregando documentos...</p>
                        </div>
                    ) : documents?.length === 0 ? (
                        <div className="p-12 text-center space-y-4">
                            <FileText className="w-12 h-12 mx-auto text-muted-foreground/20" />
                            <div className="space-y-1">
                                <p className="font-medium">Nenhum documento encontrado</p>
                                <p className="text-sm text-muted-foreground">Faça o primeiro upload para começar.</p>
                            </div>
                        </div>
                    ) : (
                        <Table>
                            <TableHeader className="bg-muted/30">
                                <TableRow className="hover:bg-transparent border-primary/10">
                                    <TableHead className="w-[400px]">Nome do Arquivo</TableHead>
                                    <TableHead>Tamanho</TableHead>
                                    <TableHead>Data</TableHead>
                                    <TableHead>Status</TableHead>
                                    <TableHead className="text-right">Ações</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                {documents?.map((doc) => (
                                    <TableRow key={doc.id} className="border-primary/5 hover:bg-primary/5 transition-colors">
                                        <TableCell className="font-medium flex items-center gap-3">
                                            <div className="p-2 rounded-lg bg-background/50 border border-primary/10">
                                                <FileText className="w-4 h-4 text-primary" />
                                            </div>
                                            {doc.name}
                                        </TableCell>
                                        <TableCell className="text-muted-foreground text-sm">
                                            {formatFileSize(doc.size_bytes)}
                                        </TableCell>
                                        <TableCell className="text-muted-foreground text-sm">
                                            {format(new Date(doc.created_at), 'dd/MM/yyyy HH:mm')}
                                        </TableCell>
                                        <TableCell>
                                            <span className={`text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full border ${doc.status === 'completed'
                                                ? 'bg-green-500/10 text-green-400 border-green-500/20'
                                                : doc.status === 'processing'
                                                    ? 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
                                                    : 'bg-red-500/10 text-red-400 border-red-500/20'
                                                }`}>
                                                {doc.status === 'completed' ? 'Treinado' : doc.status === 'processing' ? 'Processando' : 'Erro'}
                                            </span>
                                        </TableCell>
                                        <TableCell className="text-right">
                                            <Button
                                                variant="ghost"
                                                size="icon"
                                                className="text-muted-foreground hover:text-red-400 hover:bg-red-400/10 rounded-xl"
                                                onClick={() => deleteMutation.mutate(doc.id)}
                                                disabled={deleteMutation.isPending}
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </Button>
                                        </TableCell>
                                    </TableRow>
                                ))}
                            </TableBody>
                        </Table>
                    )}
                </CardContent>
            </Card>
        </div>
    );
};

export default KnowledgeBase;

'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
    LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
    Tooltip, Legend, ResponsiveContainer
} from 'recharts';
import {
    TrendingUp, TrendingDown, Calendar, CheckCircle,
    Users, Clock, ArrowUpRight, ArrowDownRight
} from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { metricsAPI } from '@/lib/api';
import { formatNumber, formatPercent, formatDuration } from '@/lib/utils';

type Periodo = 'hoje' | '7d' | '30d' | '90d';

export default function DashboardPage({ params }: { params: { tenant: string } }) {
    const [periodo, setPeriodo] = useState<Periodo>('7d');

    // Queries
    const { data: overview, isLoading: loadingOverview } = useQuery({
        queryKey: ['metrics-overview', periodo],
        queryFn: () => metricsAPI.getOverview(periodo),
        staleTime: 5 * 60 * 1000, // 5 minutos
    });

    const { data: conversationsByDay, isLoading: loadingConversations } = useQuery({
        queryKey: ['conversations-by-day', periodo],
        queryFn: () => metricsAPI.getConversationsByDay(periodo === 'hoje' ? '7d' : periodo),
        staleTime: 5 * 60 * 1000,
    });

    const { data: topProcedures, isLoading: loadingProcedures } = useQuery({
        queryKey: ['top-procedures'],
        queryFn: () => metricsAPI.getTopProcedures(10),
        staleTime: 5 * 60 * 1000,
    });

    const { data: performance, isLoading: loadingPerformance } = useQuery({
        queryKey: ['agent-performance', periodo],
        queryFn: () => metricsAPI.getAgentPerformance(periodo),
        staleTime: 5 * 60 * 1000,
    });

    return (
        <div className="min-h-screen bg-gray-50 p-8">
            <div className="max-w-7xl mx-auto space-y-8">
                {/* Header */}
                <div className="flex justify-between items-center">
                    <div>
                        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
                        <p className="text-gray-500 mt-1">Visão geral das métricas da plataforma</p>
                    </div>

                    {/* Filtro de Período */}
                    <div className="flex gap-2">
                        {(['hoje', '7d', '30d', '90d'] as Periodo[]).map((p) => (
                            <button
                                key={p}
                                onClick={() => setPeriodo(p)}
                                className={`px-4 py-2 rounded-lg font-medium transition-colors ${periodo === p
                                        ? 'bg-blue-600 text-white'
                                        : 'bg-white text-gray-700 hover:bg-gray-100'
                                    }`}
                            >
                                {p === 'hoje' ? 'Hoje' : p.replace('d', ' dias')}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Cards de Resumo */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
                    {/* Conversas */}
                    <MetricCard
                        title="Conversas"
                        value={overview?.total_conversas}
                        subtitle={`${overview?.conversas_ativas || 0} ativas`}
                        icon={<Users className="w-5 h-5" />}
                        trend={5.2}
                        loading={loadingOverview}
                    />

                    {/* Agendamentos */}
                    <MetricCard
                        title="Agendamentos"
                        value={overview?.total_agendamentos}
                        subtitle="esta semana"
                        icon={<Calendar className="w-5 h-5" />}
                        trend={12.5}
                        loading={loadingOverview}
                    />

                    {/* Taxa de Confirmação */}
                    <MetricCard
                        title="Taxa de Confirmação"
                        value={overview?.taxa_confirmacao}
                        suffix="%"
                        subtitle={`${overview?.agendamentos_confirmados || 0} confirmados`}
                        icon={<CheckCircle className="w-5 h-5" />}
                        trend={-2.1}
                        loading={loadingOverview}
                    />

                    {/* Leads em Recuperação */}
                    <MetricCard
                        title="Leads Recuperados"
                        value={overview?.leads_recuperados}
                        subtitle={`${formatPercent(overview?.taxa_recuperacao || 0)} taxa`}
                        icon={<TrendingUp className="w-5 h-5" />}
                        trend={8.3}
                        loading={loadingOverview}
                    />
                </div>

                {/* Gráficos */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                    {/* Conversas por Dia */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Conversas por Dia</CardTitle>
                            <CardDescription>Últimos {periodo === 'hoje' ? '7' : periodo.replace('d', '')} dias</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {loadingConversations ? (
                                <SkeletonChart />
                            ) : (
                                <ResponsiveContainer width="100%" height={300}>
                                    <LineChart data={conversationsByDay}>
                                        <CartesianGrid strokeDasharray="3 3" />
                                        <XAxis
                                            dataKey="data"
                                            tickFormatter={(value) => new Date(value).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' })}
                                        />
                                        <YAxis />
                                        <Tooltip
                                            labelFormatter={(value) => new Date(value).toLocaleDateString('pt-BR')}
                                        />
                                        <Legend />
                                        <Line type="monotone" dataKey="total" stroke="#3b82f6" name="Total" strokeWidth={2} />
                                        <Line type="monotone" dataKey="agendadas" stroke="#10b981" name="Agendadas" strokeWidth={2} />
                                    </LineChart>
                                </ResponsiveContainer>
                            )}
                        </CardContent>
                    </Card>

                    {/* Top Procedimentos */}
                    <Card>
                        <CardHeader>
                            <CardTitle>Procedimentos Mais Agendados</CardTitle>
                            <CardDescription>Top 10 procedimentos</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {loadingProcedures ? (
                                <SkeletonChart />
                            ) : (
                                <ResponsiveContainer width="100%" height={300}>
                                    <BarChart data={topProcedures} layout="vertical">
                                        <CartesianGrid strokeDasharray="3 3" />
                                        <XAxis type="number" />
                                        <YAxis dataKey="nome" type="category" width={150} />
                                        <Tooltip />
                                        <Bar dataKey="total_agendamentos" fill="#3b82f6" name="Agendamentos" />
                                    </BarChart>
                                </ResponsiveContainer>
                            )}
                        </CardContent>
                    </Card>
                </div>

                {/* Performance do Agente */}
                <Card>
                    <CardHeader>
                        <CardTitle>Performance do Agente IA</CardTitle>
                        <CardDescription>Métricas de eficiência do agente</CardDescription>
                    </CardHeader>
                    <CardContent>
                        {loadingPerformance ? (
                            <div className="grid grid-cols-3 gap-6">
                                {[1, 2, 3].map((i) => <SkeletonMetric key={i} />)}
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                                <div className="text-center p-4 bg-gray-50 rounded-lg">
                                    <p className="text-sm text-gray-600 mb-2">Taxa de Escalação</p>
                                    <p className="text-3xl font-bold text-gray-900">
                                        {formatPercent(performance?.taxa_escalacao || 0)}
                                    </p>
                                    <p className="text-xs text-gray-500 mt-1">Conversas transferidas para humano</p>
                                </div>

                                <div className="text-center p-4 bg-gray-50 rounded-lg">
                                    <p className="text-sm text-gray-600 mb-2">Taxa de Agendamento</p>
                                    <p className="text-3xl font-bold text-green-600">
                                        {formatPercent(performance?.taxa_agendamento || 0)}
                                    </p>
                                    <p className="text-xs text-gray-500 mt-1">Conversas que resultaram em agendamento</p>
                                </div>

                                <div className="text-center p-4 bg-gray-50 rounded-lg">
                                    <p className="text-sm text-gray-600 mb-2">Tempo Médio de Resolução</p>
                                    <p className="text-3xl font-bold text-blue-600">
                                        {Math.round(performance?.tempo_medio_resolucao_minutos || 0)}m
                                    </p>
                                    <p className="text-xs text-gray-500 mt-1">Tempo para concluir conversa</p>
                                </div>
                            </div>
                        )}
                    </CardContent>
                </Card>

                {/* Métricas Adicionais */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <Card>
                        <CardHeader>
                            <CardTitle>Tempo Médio de Resposta</CardTitle>
                            <CardDescription>Velocidade do agente IA</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {loadingOverview ? (
                                <SkeletonMetric />
                            ) : (
                                <div className="flex items-center justify-between">
                                    <div>
                                        <p className="text-4xl font-bold text-gray-900">
                                            {formatDuration(overview?.tempo_medio_resposta_segundos || 0)}
                                        </p>
                                        <p className="text-sm text-gray-500 mt-2">Tempo médio de resposta</p>
                                    </div>
                                    <Clock className="w-12 h-12 text-blue-500" />
                                </div>
                            )}
                        </CardContent>
                    </Card>

                    <Card>
                        <CardHeader>
                            <CardTitle>Mensagens Enviadas</CardTitle>
                            <CardDescription>Distribuição por origem</CardDescription>
                        </CardHeader>
                        <CardContent>
                            {loadingOverview ? (
                                <SkeletonMetric />
                            ) : (
                                <div className="space-y-4">
                                    <div className="flex justify-between items-center">
                                        <span className="text-sm text-gray-600">Agente IA</span>
                                        <span className="text-2xl font-bold text-blue-600">
                                            {formatNumber(overview?.mensagens_enviadas_agente || 0)}
                                        </span>
                                    </div>
                                    <div className="flex justify-between items-center">
                                        <span className="text-sm text-gray-600">Atendente Humano</span>
                                        <span className="text-2xl font-bold text-green-600">
                                            {formatNumber(overview?.mensagens_enviadas_humano || 0)}
                                        </span>
                                    </div>
                                </div>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}

// Componentes auxiliares
function MetricCard({
    title,
    value,
    suffix = '',
    subtitle,
    icon,
    trend,
    loading
}: {
    title: string;
    value?: number;
    suffix?: string;
    subtitle: string;
    icon: React.ReactNode;
    trend?: number;
    loading: boolean;
}) {
    if (loading) {
        return (
            <Card>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                    <CardTitle className="text-sm font-medium">{title}</CardTitle>
                    {icon}
                </CardHeader>
                <CardContent>
                    <div className="h-8 bg-gray-200 rounded animate-pulse mb-2" />
                    <div className="h-4 bg-gray-100 rounded animate-pulse w-2/3" />
                </CardContent>
            </Card>
        );
    }

    const isPositive = trend && trend > 0;

    return (
        <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{title}</CardTitle>
                {icon}
            </CardHeader>
            <CardContent>
                <div className="text-2xl font-bold">
                    {formatNumber(value || 0)}{suffix}
                </div>
                <div className="flex items-center gap-2 mt-1">
                    <p className="text-xs text-muted-foreground">{subtitle}</p>
                    {trend !== undefined && (
                        <span className={`flex items-center text-xs ${isPositive ? 'text-green-600' : 'text-red-600'}`}>
                            {isPositive ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                            {Math.abs(trend)}%
                        </span>
                    )}
                </div>
            </CardContent>
        </Card>
    );
}

function SkeletonChart() {
    return (
        <div className="h-[300px] bg-gray-100 rounded animate-pulse" />
    );
}

function SkeletonMetric() {
    return (
        <div className="space-y-3">
            <div className="h-8 bg-gray-200 rounded animate-pulse" />
            <div className="h-4 bg-gray-100 rounded animate-pulse w-2/3" />
        </div>
    );
}

'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import './globals.css';

export default function RootLayout({
    children,
}: {
    children: React.ReactNode;
}) {
    const [queryClient] = useState(() => new QueryClient({
        defaultOptions: {
            queries: {
                staleTime: 5 * 60 * 1000, // 5 minutos
                refetchOnWindowFocus: false,
            },
        },
    }));

    return (
        <html lang="pt-BR">
            <body>
                <QueryClientProvider client={queryClient}>
                    {children}
                </QueryClientProvider>
            </body>
        </html>
    );
}

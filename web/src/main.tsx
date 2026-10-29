import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import '@fontsource-variable/inter';
import '@fontsource-variable/fraunces';
import '@fontsource/jetbrains-mono/400.css';
import '@fontsource/jetbrains-mono/600.css';
import App from './App';
import { PreferencesProvider, usePreferences } from './design/preferences';
import './index.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, refetchOnWindowFocus: false, staleTime: 15_000 },
  },
});

const ThemedToaster: React.FC = () => {
  const { resolvedTheme } = usePreferences();
  return <Toaster theme={resolvedTheme} position="bottom-right" duration={4000} closeButton toastOptions={{ style: { fontFamily: 'inherit' } }} />;
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <PreferencesProvider>
        <App />
        <ThemedToaster />
      </PreferencesProvider>
    </QueryClientProvider>
  </React.StrictMode>
);

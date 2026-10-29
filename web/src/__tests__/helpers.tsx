import React from 'react';
import { render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { PreferencesProvider } from '../design/preferences';

export function renderWithProviders(ui: React.ReactElement, { route = '/', path }: { route?: string; path?: string } = {}) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <PreferencesProvider>
        <MemoryRouter initialEntries={[route]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
          {path ? (
            <Routes>
              <Route path={path} element={ui} />
              <Route path="*" element={<div data-testid="navigated" />} />
            </Routes>
          ) : (
            ui
          )}
        </MemoryRouter>
      </PreferencesProvider>
    </QueryClientProvider>
  );
}

export function setDemoDataMode() {
  window.localStorage.setItem('vf.dataMode', 'demo');
}

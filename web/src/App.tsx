import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { MarketingLayout } from './layouts/MarketingLayout';
import { ConsoleLayout } from './layouts/ConsoleLayout';
import { Skeleton } from './design/ui';

const Home = lazy(() => import('./pages/marketing/Home'));
const PublicVerify = lazy(() => import('./pages/verify/PublicVerifyPage'));
const NotFound = lazy(() => import('./pages/NotFound'));
const Dashboard = lazy(() => import('./pages/console/Dashboard'));
const Analyze = lazy(() => import('./pages/console/Analyze'));
const Cases = lazy(() => import('./pages/console/Cases'));
const CaseDetail = lazy(() => import('./pages/console/CaseDetail'));
const ReviewQueue = lazy(() => import('./pages/console/ReviewQueue'));
const ReviewWorkspace = lazy(() => import('./pages/console/ReviewWorkspace'));
const Policies = lazy(() => import('./pages/console/Policies'));
const SettingsPage = lazy(() => import('./pages/console/Settings'));

const PageFallback: React.FC = () => (
  <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-10" aria-busy="true" aria-label="Loading">
    <Skeleton className="h-8 w-64" />
    <Skeleton className="h-4 w-96 max-w-full" />
    <div className="grid gap-4 sm:grid-cols-3">
      <Skeleton className="h-24" />
      <Skeleton className="h-24" />
      <Skeleton className="h-24" />
    </div>
  </div>
);

/** Old HashRouter links (#/review, #/cases/:id, #/verify) keep working. */
function legacyHashTarget(hash: string): string | null {
  if (!hash.startsWith('#/')) return null;
  const path = hash.slice(1);
  if (path === '/' || path === '') return '/app';
  if (path.startsWith('/verify')) return path;
  return `/app${path}`;
}

const LegacyRedirect: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const location = useLocation();
  const target = legacyHashTarget(location.hash);
  if (target) return <Navigate to={target} replace />;
  return <>{children}</>;
};

export function AppRoutes() {
  return (
    <LegacyRedirect>
      <Suspense fallback={<PageFallback />}>
        <Routes>
          <Route element={<MarketingLayout />}>
            <Route index element={<Home />} />
            <Route path="verify" element={<PublicVerify />} />
            <Route path="*" element={<NotFound />} />
          </Route>
          <Route path="app" element={<ConsoleLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="analyze" element={<Analyze />} />
            <Route path="cases" element={<Cases />} />
            <Route path="cases/:id" element={<CaseDetail />} />
            <Route path="review" element={<ReviewQueue />} />
            <Route path="review/:id" element={<ReviewWorkspace />} />
            <Route path="policies" element={<Policies />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </Suspense>
    </LegacyRedirect>
  );
}

export default function App() {
  return (
    <BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <AppRoutes />
    </BrowserRouter>
  );
}

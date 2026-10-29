import React from 'react';
import { HashRouter, Routes, Route, useNavigate, useParams, useMatch } from 'react-router-dom';
import { Dashboard } from './routes/Dashboard';
import { ReviewWorkspace } from './routes/ReviewWorkspace';
import { CaseDetail } from './routes/CaseDetail';

function AppContent() {
  const navigate = useNavigate();
  const isDashboard = Boolean(useMatch('/'));
  const isReview = Boolean(useMatch('/review/*')) || Boolean(useMatch('/review'));

  return (
    <div className="min-h-screen bg-bg text-text flex flex-col">
      {/* Top Navigation Bar */}
      <nav className="border-b border-border bg-surface px-6 py-2.5 flex items-center justify-between text-xs">
        <div className="flex items-center gap-6">
          <button
            onClick={() => navigate('/')}
            className="flex items-center gap-2 font-bold tracking-wider text-accent text-sm"
          >
            <span>SENTINEL-V</span>
            <span className="bg-amber-100 dark:bg-amber-950/60 text-amber-800 dark:text-amber-300 text-[10px] px-1.5 py-0.2 rounded font-mono font-medium">
              CONSOLE
            </span>
          </button>

          <div className="flex items-center gap-1 border-l border-border pl-4">
            <button
              onClick={() => navigate('/')}
              className={`px-3 py-1 rounded font-medium transition-colors ${
                isDashboard
                  ? 'bg-accent text-white'
                  : 'text-muted hover:text-text hover:bg-bg'
              }`}
              aria-current={isDashboard ? 'page' : undefined}
            >
              Queue Dashboard
            </button>
            <button
              onClick={() => navigate('/review')}
              className={`px-3 py-1 rounded font-medium transition-colors ${
                isReview
                  ? 'bg-accent text-white'
                  : 'text-muted hover:text-text hover:bg-bg'
              }`}
              aria-current={isReview ? 'page' : undefined}
            >
              Review Workspace
            </button>
          </div>
        </div>

      </nav>

      {/* Route Views */}
      <div className="flex-1">
        <Routes>
          <Route
            path="/"
            element={
              <Dashboard
                onStartReview={() => navigate('/review')}
                onViewCase={(id) => navigate(`/cases/${id}`)}
              />
            }
          />
          <Route path="/review" element={<ReviewWorkspace />} />
          <Route
            path="/cases/:id"
            element={
              <CaseDetailWrapper
                onBack={() => navigate('/')}
                onOpenReview={() => navigate('/review')}
              />
            }
          />
        </Routes>
      </div>
    </div>
  );
}

function CaseDetailWrapper({ onBack, onOpenReview }: { onBack: () => void; onOpenReview: () => void }) {
  const { id: caseId } = useParams<{ id: string }>();
  return <CaseDetail caseId={caseId || 'an_mock_default'} onBack={onBack} onOpenReview={onOpenReview} />;
}

export function App() {
  return (
    <HashRouter>
      <AppContent />
    </HashRouter>
  );
}

export default App;

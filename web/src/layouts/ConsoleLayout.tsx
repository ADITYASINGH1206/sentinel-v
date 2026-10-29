import React, { useEffect, useState } from 'react';
import { Link, NavLink, useLocation, useOutlet } from 'react-router-dom';
import { AnimatePresence, m } from 'framer-motion';
import {
  ChevronsLeft,
  ChevronsRight,
  ClipboardCheck,
  FileSearch,
  LayoutDashboard,
  Menu,
  Settings,
  SlidersHorizontal,
  UploadCloud,
  ShieldCheck,
  X,
} from 'lucide-react';
import { Logo, LogoMark } from '../design/Logo';
import { ThemeToggle } from '../design/ThemeToggle';
import { Badge, cn, DemoBadge } from '../design/ui';
import { pageTransition } from '../design/motion';
import { useReviewQueue, useCases } from '../data/hooks';

const NAV = [
  { to: '/app', label: 'Dashboard', icon: LayoutDashboard, end: true },
  { to: '/app/analyze', label: 'Analyze', icon: UploadCloud },
  { to: '/app/cases', label: 'Cases', icon: FileSearch },
  { to: '/app/review', label: 'Review', icon: ClipboardCheck, badge: 'review' as const },
  { to: '/app/policies', label: 'Policies', icon: SlidersHorizontal },
];

const BOTTOM = [
  { to: '/verify', label: 'Verify a receipt', icon: ShieldCheck },
  { to: '/app/settings', label: 'Settings', icon: Settings },
];

function readCollapsed(): boolean {
  try {
    return window.localStorage.getItem('vf.sidebar') === 'collapsed';
  } catch {
    return false;
  }
}

const CRUMBS: Record<string, string> = {
  app: 'Console',
  analyze: 'Analyze',
  cases: 'Cases',
  review: 'Review',
  policies: 'Policies',
  settings: 'Settings',
};

export const ConsoleLayout: React.FC = () => {
  const location = useLocation();
  const outlet = useOutlet();
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [drawer, setDrawer] = useState(false);
  const queue = useReviewQueue();
  const cases = useCases();
  const isDemo = Boolean(queue.data?.isDemo || cases.data?.isDemo);
  const backlog = queue.data?.data.length ?? null;

  useEffect(() => setDrawer(false), [location.pathname]);
  useEffect(() => {
    try {
      window.localStorage.setItem('vf.sidebar', collapsed ? 'collapsed' : 'expanded');
    } catch {
      /* ignore */
    }
  }, [collapsed]);

  const parts = location.pathname.split('/').filter(Boolean);

  const navList = (compact: boolean) => (
    <nav className="flex flex-1 flex-col gap-1 px-3" aria-label="Console">
      {NAV.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          title={compact ? item.label : undefined}
          className={({ isActive }) =>
            cn(
              'group relative flex h-9 items-center gap-3 rounded-md px-2.5 text-sm transition-colors',
              isActive ? 'bg-accent/10 text-accent' : 'text-muted hover:bg-surface-2 hover:text-text'
            )
          }
        >
          {({ isActive }) => (
            <>
              {isActive && <m.span layoutId="side-active" className="absolute inset-y-1.5 left-0 w-0.5 rounded-full bg-accent" />}
              <item.icon className="h-4 w-4 shrink-0" aria-hidden />
              {!compact && <span className="flex-1 truncate">{item.label}</span>}
              {!compact && item.badge === 'review' && backlog != null && backlog > 0 && (
                <span className="rounded-full bg-band-review/15 px-1.5 font-mono text-[11px] text-band-review">{backlog}</span>
              )}
            </>
          )}
        </NavLink>
      ))}
      <div className="mt-auto flex flex-col gap-1 border-t border-border pt-3">
        {BOTTOM.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            title={compact ? item.label : undefined}
            className={({ isActive }) =>
              cn('flex h-9 items-center gap-3 rounded-md px-2.5 text-sm transition-colors', isActive ? 'bg-accent/10 text-accent' : 'text-muted hover:bg-surface-2 hover:text-text')
            }
          >
            <item.icon className="h-4 w-4 shrink-0" aria-hidden />
            {!compact && <span className="truncate">{item.label}</span>}
          </NavLink>
        ))}
      </div>
    </nav>
  );

  return (
    <div className="flex min-h-screen bg-bg">
      <m.aside
        initial={false}
        animate={{ width: collapsed ? 72 : 240 }}
        transition={{ duration: 0.2, ease: [0.2, 0, 0, 1] }}
        className="sticky top-0 hidden h-screen shrink-0 flex-col border-r border-border bg-surface py-4 lg:flex"
      >
        <div className={cn('mb-6 flex items-center px-4', collapsed ? 'justify-center' : 'justify-between')}>
          <Link to="/" aria-label="VeriFrame home">
            {collapsed ? <LogoMark /> : <Logo suffix="Console" />}
          </Link>
        </div>
        {navList(collapsed)}
        <button
          type="button"
          onClick={() => setCollapsed((v) => !v)}
          className="mx-3 mt-3 flex h-8 items-center justify-center gap-2 rounded-md text-xs text-muted hover:bg-surface-2 hover:text-text"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronsRight className="h-4 w-4" /> : (<><ChevronsLeft className="h-4 w-4" /> Collapse</>)}
        </button>
      </m.aside>

      <AnimatePresence>
        {drawer && (
          <>
            <m.div className="fixed inset-0 z-40 bg-black/40 lg:hidden" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setDrawer(false)} />
            <m.aside
              className="fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-surface py-4 lg:hidden"
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ duration: 0.22, ease: [0.2, 0, 0, 1] }}
            >
              <div className="mb-6 flex items-center justify-between px-4">
                <Logo suffix="Console" />
                <button className="grid h-8 w-8 place-items-center rounded-md hover:bg-surface-2" onClick={() => setDrawer(false)} aria-label="Close navigation">
                  <X className="h-4 w-4" />
                </button>
              </div>
              {navList(false)}
            </m.aside>
          </>
        )}
      </AnimatePresence>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between gap-3 border-b border-border bg-bg/80 px-4 backdrop-blur-md sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <button className="grid h-9 w-9 place-items-center rounded-md text-muted hover:bg-surface-2 lg:hidden" onClick={() => setDrawer(true)} aria-label="Open navigation">
              <Menu className="h-5 w-5" />
            </button>
            <ol className="flex min-w-0 items-center gap-1.5 text-sm" aria-label="Breadcrumb">
              {parts.map((p, i) => (
                <li key={`${p}-${i}`} className="flex min-w-0 items-center gap-1.5">
                  {i > 0 && <span className="text-muted">/</span>}
                  <span className={cn('truncate', i === parts.length - 1 ? 'font-medium text-text' : 'text-muted', /^an_/.test(p) && 'font-mono text-xs')}>
                    {CRUMBS[p] ?? p}
                  </span>
                </li>
              ))}
            </ol>
          </div>
          <div className="flex items-center gap-2">
            {isDemo && <DemoBadge />}
            <Badge tone="neutral" className="hidden font-mono sm:inline-flex">
              {import.meta.env?.MODE === 'production' ? 'PROD BUILD' : 'DEV'}
            </Badge>
            <ThemeToggle />
          </div>
        </header>
        {isDemo && (
          <div className="border-b border-band-review/25 bg-band-review/10 px-4 py-2 text-xs text-text sm:px-6">
            The API list endpoints are not available, so the console is showing <strong>generated demo data</strong>. Nothing marked DEMO is an
            actual analysis.
          </div>
        )}
        <main id="main" className="flex-1 px-4 py-6 sm:px-6 lg:px-8">
          <AnimatePresence mode="wait" initial={false}>
            <m.div key={location.pathname} {...pageTransition} className="mx-auto w-full max-w-7xl">
              {outlet}
            </m.div>
          </AnimatePresence>
        </main>
      </div>
    </div>
  );
};

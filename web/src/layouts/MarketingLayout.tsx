import React, { useEffect, useState } from 'react';
import { Link, NavLink, useLocation, useOutlet } from 'react-router-dom';
import { AnimatePresence, m } from 'framer-motion';
import { Github, Menu, X } from 'lucide-react';
import { Logo } from '../design/Logo';
import { ThemeToggle } from '../design/ThemeToggle';
import { buttonVariants, cn } from '../design/ui';
import { BRAND } from '../brand';
import { REQUIRED_DISCLAIMER } from '../copy/forbidden';

export const SECTIONS = [
  { id: 'how', label: 'How it works' },
  { id: 'features', label: 'Features' },
  { id: 'base-rates', label: 'Base rates' },
  { id: 'verify', label: 'Verify' },
  { id: 'research', label: 'Research' },
  { id: 'faq', label: 'FAQ' },
];

function useScrolled(threshold = 8) {
  const [scrolled, setScrolled] = useState(false);
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > threshold);
    onScroll();
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, [threshold]);
  return scrolled;
}

function useActiveSection(enabled: boolean) {
  const [active, setActive] = useState<string | null>(null);
  useEffect(() => {
    if (!enabled || typeof IntersectionObserver === 'undefined') return;
    const els = SECTIONS.map((s) => document.getElementById(s.id)).filter(Boolean) as HTMLElement[];
    const obs = new IntersectionObserver(
      (entries) => {
        const visible = entries.filter((e) => e.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio);
        if (visible[0]) setActive(visible[0].target.id);
      },
      { rootMargin: '-35% 0px -55% 0px', threshold: [0, 0.25, 0.5] }
    );
    els.forEach((el) => obs.observe(el));
    return () => obs.disconnect();
  }, [enabled]);
  return active;
}

export const MarketingLayout: React.FC = () => {
  const location = useLocation();
  const outlet = useOutlet();
  const onHome = location.pathname === '/';
  const scrolled = useScrolled();
  const active = useActiveSection(onHome);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => setMenuOpen(false), [location.pathname, location.hash]);

  const sectionHref = (id: string) => (onHome ? `#${id}` : `/#${id}`);

  return (
    <div className="flex min-h-screen flex-col bg-bg">
      <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-surface focus:px-3 focus:py-2">
        Skip to content
      </a>
      <header
        className={cn(
          'sticky top-0 z-40 border-b transition-[background-color,border-color,backdrop-filter] duration-200',
          scrolled || !onHome ? 'border-border bg-bg/80 backdrop-blur-md' : 'border-transparent bg-transparent'
        )}
      >
        <nav className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-6 px-4 sm:px-6" aria-label="Main">
          <Link to="/" aria-label={`${BRAND.name} home`}>
            <Logo />
          </Link>
          <ul className="hidden items-center gap-1 lg:flex">
            {SECTIONS.map((s) => (
              <li key={s.id} className="relative">
                <a
                  href={sectionHref(s.id)}
                  className={cn(
                    'relative block rounded-md px-3 py-2 text-sm transition-colors',
                    active === s.id ? 'text-text' : 'text-muted hover:text-text'
                  )}
                >
                  {s.label}
                  {active === s.id && (
                    <m.span layoutId="nav-underline" className="absolute inset-x-3 -bottom-px h-0.5 rounded-full bg-accent" transition={{ duration: 0.25 }} />
                  )}
                </a>
              </li>
            ))}
          </ul>
          <div className="flex items-center gap-2">
            <ThemeToggle />
            <Link to="/verify" className={cn(buttonVariants({ variant: 'ghost', size: 'sm' }), 'hidden sm:inline-flex')}>
              Verify a receipt
            </Link>
            <Link to="/app" className={cn(buttonVariants({ variant: 'primary', size: 'sm' }), 'hidden sm:inline-flex')}>
              Open console
            </Link>
            <button
              type="button"
              className="grid h-9 w-9 place-items-center rounded-md text-muted hover:bg-surface-2 lg:hidden"
              aria-label={menuOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={menuOpen}
              onClick={() => setMenuOpen((v) => !v)}
            >
              {menuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            </button>
          </div>
        </nav>
        <AnimatePresence>
          {menuOpen && (
            <m.div
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.18 }}
              className="border-t border-border bg-bg/95 backdrop-blur-md lg:hidden"
            >
              <m.ul
                className="mx-auto flex max-w-6xl flex-col gap-1 px-4 py-4"
                initial="hidden"
                animate="show"
                variants={{ hidden: {}, show: { transition: { staggerChildren: 0.03 } } }}
              >
                {SECTIONS.map((s) => (
                  <m.li key={s.id} variants={{ hidden: { opacity: 0, x: -8 }, show: { opacity: 1, x: 0 } }}>
                    <a href={sectionHref(s.id)} className="block rounded-md px-3 py-2.5 text-sm text-text hover:bg-surface-2" onClick={() => setMenuOpen(false)}>
                      {s.label}
                    </a>
                  </m.li>
                ))}
                <li className="mt-2 flex gap-2 px-3">
                  <Link to="/verify" className={buttonVariants({ variant: 'secondary', size: 'sm' })}>
                    Verify a receipt
                  </Link>
                  <Link to="/app" className={buttonVariants({ variant: 'primary', size: 'sm' })}>
                    Open console
                  </Link>
                </li>
              </m.ul>
            </m.div>
          )}
        </AnimatePresence>
      </header>

      <main id="main" className="flex-1">
        <AnimatePresence mode="wait" initial={false}>
          <m.div key={location.pathname} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.16 }}>
            {outlet}
          </m.div>
        </AnimatePresence>
      </main>

      <footer className="border-t border-border bg-surface/50">
        <div className="mx-auto grid max-w-6xl gap-8 px-4 py-12 sm:px-6 md:grid-cols-[1.4fr_1fr_1fr]">
          <div className="space-y-3">
            <Logo />
            <p className="max-w-sm text-sm text-muted">{BRAND.tagline}</p>
            <p className="max-w-sm text-xs italic text-muted">{REQUIRED_DISCLAIMER}</p>
          </div>
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">Product</p>
            <ul className="space-y-2 text-sm">
              <li><NavLink to="/app" className="text-text hover:text-accent">Console</NavLink></li>
              <li><NavLink to="/verify" className="text-text hover:text-accent">Verify a receipt</NavLink></li>
              <li><a href={sectionHref('how')} className="text-text hover:text-accent">How it works</a></li>
            </ul>
          </div>
          <div>
            <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-muted">Project</p>
            <ul className="space-y-2 text-sm">
              <li>
                <a href={BRAND.repoUrl} className="inline-flex items-center gap-1.5 text-text hover:text-accent" rel="noreferrer" target="_blank">
                  <Github className="h-4 w-4" /> Source code
                </a>
              </li>
              <li><a href={`${BRAND.repoUrl}/tree/main/docs`} className="text-text hover:text-accent" rel="noreferrer" target="_blank">Documentation</a></li>
              <li><a href={`${BRAND.repoUrl}/blob/main/docs/SECURITY_REVIEW.md`} className="text-text hover:text-accent" rel="noreferrer" target="_blank">Security</a></li>
            </ul>
          </div>
        </div>
        <div className="border-t border-border">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-4 text-xs text-muted sm:px-6">
            <span>Research preview · detector family {BRAND.detectorFamily} · trained on research-licensed datasets</span>
            <span className="font-mono">v{__APP_VERSION__}</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

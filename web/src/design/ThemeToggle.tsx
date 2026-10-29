import React from 'react';
import { AnimatePresence, m } from 'framer-motion';
import { Monitor, Moon, Sun } from 'lucide-react';
import { usePreferences, type ThemePref } from './preferences';
import { cn } from './ui';

const ORDER: ThemePref[] = ['system', 'light', 'dark'];
const LABEL: Record<ThemePref, string> = { system: 'System theme', light: 'Light theme', dark: 'Dark theme' };

export const ThemeToggle: React.FC<{ className?: string }> = ({ className }) => {
  const { theme, setTheme } = usePreferences();
  const next = ORDER[(ORDER.indexOf(theme) + 1) % ORDER.length];
  const Icon = theme === 'light' ? Sun : theme === 'dark' ? Moon : Monitor;
  return (
    <button
      type="button"
      onClick={() => setTheme(next)}
      className={cn(
        'relative grid h-9 w-9 place-items-center overflow-hidden rounded-md text-muted transition-colors hover:bg-surface-2 hover:text-text',
        className
      )}
      aria-label={`${LABEL[theme]} (switch to ${LABEL[next].toLowerCase()})`}
      title={LABEL[theme]}
    >
      <AnimatePresence mode="wait" initial={false}>
        <m.span
          key={theme}
          initial={{ opacity: 0, rotate: -90, scale: 0.6 }}
          animate={{ opacity: 1, rotate: 0, scale: 1 }}
          exit={{ opacity: 0, rotate: 90, scale: 0.6 }}
          transition={{ duration: 0.2 }}
          className="grid place-items-center"
        >
          <Icon className="h-4 w-4" />
        </m.span>
      </AnimatePresence>
    </button>
  );
};

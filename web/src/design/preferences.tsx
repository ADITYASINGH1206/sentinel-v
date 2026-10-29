import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { MotionConfig, LazyMotion, domAnimation } from 'framer-motion';

export type ThemePref = 'light' | 'dark' | 'system';
export type MotionPref = 'system' | 'reduce' | 'full';

interface Preferences {
  theme: ThemePref;
  resolvedTheme: 'light' | 'dark';
  setTheme: (t: ThemePref) => void;
  motion: MotionPref;
  setMotion: (m: MotionPref) => void;
  /** True when animations should be minimised (user setting or OS setting). */
  reduceMotion: boolean;
}

const PreferencesContext = createContext<Preferences | null>(null);

function readStorage(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeStorage(key: string, value: string) {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    /* storage unavailable (private mode, sandbox) — preference lasts for this session only */
  }
}

function useMediaQuery(query: string): boolean {
  const get = () => (typeof window !== 'undefined' && window.matchMedia ? window.matchMedia(query).matches : false);
  const [matches, setMatches] = useState(get);
  useEffect(() => {
    if (!window.matchMedia) return;
    const mql = window.matchMedia(query);
    const onChange = () => setMatches(mql.matches);
    onChange();
    mql.addEventListener?.('change', onChange);
    return () => mql.removeEventListener?.('change', onChange);
  }, [query]);
  return matches;
}

export const PreferencesProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<ThemePref>(() => (readStorage('vf.theme') as ThemePref) || 'system');
  const [motion, setMotionState] = useState<MotionPref>(() => (readStorage('vf.motion') as MotionPref) || 'system');
  const systemDark = useMediaQuery('(prefers-color-scheme: dark)');
  const systemReduce = useMediaQuery('(prefers-reduced-motion: reduce)');

  const resolvedTheme: 'light' | 'dark' = theme === 'system' ? (systemDark ? 'dark' : 'light') : theme;
  const reduceMotion = motion === 'reduce' || (motion === 'system' && systemReduce);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle('dark', resolvedTheme === 'dark');
  }, [resolvedTheme]);

  useEffect(() => {
    document.documentElement.dataset.motion = reduceMotion ? 'reduce' : 'full';
  }, [reduceMotion]);

  const setTheme = useCallback((t: ThemePref) => {
    setThemeState(t);
    writeStorage('vf.theme', t);
  }, []);
  const setMotion = useCallback((m: MotionPref) => {
    setMotionState(m);
    writeStorage('vf.motion', m);
  }, []);

  const value = useMemo(
    () => ({ theme, resolvedTheme, setTheme, motion, setMotion, reduceMotion }),
    [theme, resolvedTheme, setTheme, motion, setMotion, reduceMotion]
  );

  return (
    <PreferencesContext.Provider value={value}>
      <LazyMotion features={domAnimation}>
        <MotionConfig reducedMotion={reduceMotion ? 'always' : 'never'}>{children}</MotionConfig>
      </LazyMotion>
    </PreferencesContext.Provider>
  );
};

const FALLBACK: Preferences = {
  theme: 'system',
  resolvedTheme: 'light',
  setTheme: () => undefined,
  motion: 'system',
  setMotion: () => undefined,
  reduceMotion: false,
};

export function usePreferences(): Preferences {
  // Components rendered in isolation (unit tests) get safe defaults.
  return useContext(PreferencesContext) ?? FALLBACK;
}

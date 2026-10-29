import { useMemo } from 'react';
import { usePreferences } from './preferences';

const NAMES = ['--accent', '--violet', '--muted', '--border', '--text', '--surface', '--band-authentic', '--band-review', '--band-manipulated', '--band-inconclusive'] as const;
type Name = (typeof NAMES)[number];

/** Resolve token colors to `rgb(...)` strings for SVG/canvas consumers (Recharts, overlays). */
export function useThemeColors(): Record<Name, string> {
  const { resolvedTheme } = usePreferences();
  return useMemo(() => {
    const out = {} as Record<Name, string>;
    const style = typeof window !== 'undefined' ? getComputedStyle(document.documentElement) : null;
    for (const n of NAMES) {
      const raw = style?.getPropertyValue(n).trim();
      out[n] = raw ? `rgb(${raw.split(/\s+/).join(', ')})` : 'rgb(120, 130, 140)';
    }
    return out;
    // resolvedTheme triggers a re-read after the <html> class changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resolvedTheme]);
}

import React, { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Monitor, Moon, Sun } from 'lucide-react';
import { PageHeader } from '../../components/console/common';
import { Card, CardHeader, Kbd, cn } from '../../design/ui';
import { usePreferences, type MotionPref, type ThemePref } from '../../design/preferences';
import { BRAND } from '../../brand';

const Choice = <T extends string>({ value, options, onChange, label }: { value: T; options: Array<{ value: T; label: string; icon?: React.ReactNode }>; onChange: (v: T) => void; label: string }) => (
  <div role="radiogroup" aria-label={label} className="grid grid-cols-3 gap-2">
    {options.map((o) => (
      <button
        key={o.value}
        type="button"
        role="radio"
        aria-checked={value === o.value}
        onClick={() => onChange(o.value)}
        className={cn(
          'flex h-10 items-center justify-center gap-2 rounded-md border text-sm transition-colors',
          value === o.value ? 'border-accent bg-accent/10 text-accent' : 'border-border text-muted hover:bg-surface-2 hover:text-text'
        )}
      >
        {o.icon}
        {o.label}
      </button>
    ))}
  </div>
);

function readDataMode(): 'auto' | 'demo' {
  try {
    return window.localStorage.getItem('vf.dataMode') === 'demo' ? 'demo' : 'auto';
  } catch {
    return 'auto';
  }
}

const Settings: React.FC = () => {
  const { theme, setTheme, motion, setMotion } = usePreferences();
  const [dataMode, setDataMode] = useState<'auto' | 'demo'>(readDataMode);
  const qc = useQueryClient();

  const changeDataMode = (m: 'auto' | 'demo') => {
    setDataMode(m);
    try {
      window.localStorage.setItem('vf.dataMode', m);
    } catch {
      /* ignore */
    }
    qc.invalidateQueries();
  };

  return (
    <>
      <PageHeader title="Settings" description="Preferences for this browser." />
      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader title="Appearance" />
          <div className="space-y-5 p-5">
            <div>
              <p className="mb-2 text-sm font-medium text-text">Theme</p>
              <Choice<ThemePref>
                label="Theme"
                value={theme}
                onChange={setTheme}
                options={[
                  { value: 'system', label: 'System', icon: <Monitor className="h-4 w-4" /> },
                  { value: 'light', label: 'Light', icon: <Sun className="h-4 w-4" /> },
                  { value: 'dark', label: 'Dark', icon: <Moon className="h-4 w-4" /> },
                ]}
              />
            </div>
            <div>
              <p className="mb-2 text-sm font-medium text-text">Motion</p>
              <Choice<MotionPref>
                label="Motion"
                value={motion}
                onChange={setMotion}
                options={[
                  { value: 'system', label: 'System' },
                  { value: 'reduce', label: 'Reduce' },
                  { value: 'full', label: 'Full' },
                ]}
              />
              <p className="mt-2 text-xs text-muted">“Reduce” turns off movement and loops; content still fades in.</p>
            </div>
          </div>
        </Card>
        <Card>
          <CardHeader title="Data source" />
          <div className="space-y-3 p-5">
            <Choice<'auto' | 'demo'>
              label="Data source"
              value={dataMode}
              onChange={changeDataMode}
              options={[
                { value: 'auto', label: 'Live API' },
                { value: 'demo', label: 'Demo data' },
              ]}
            />
            <p className="text-xs text-muted">
              Live mode calls the API and falls back to labelled demo data only where an endpoint does not exist yet. Demo mode uses generated data everywhere.
            </p>
          </div>
        </Card>
        <Card>
          <CardHeader title="Keyboard" />
          <dl className="grid grid-cols-[auto_1fr] gap-x-6 gap-y-2.5 p-5 text-sm">
            {[
              ['1 / 2 / 3', 'Review decision'],
              ['Shift + 1–5', 'Confidence'],
              ['Enter', 'Submit review'],
              ['N', 'Claim next (queue)'],
              ['Space · ← →', 'Play · step frames'],
              ['P · H', 'Peak clip · overlay'],
            ].map(([k, v]) => (
              <React.Fragment key={k}>
                <dt>
                  <Kbd>{k}</Kbd>
                </dt>
                <dd className="text-muted">{v}</dd>
              </React.Fragment>
            ))}
          </dl>
        </Card>
        <Card>
          <CardHeader title="About" />
          <dl className="space-y-2 p-5 text-sm">
            {[
              ['Product', BRAND.consoleName],
              ['Version', __APP_VERSION__],
              ['Detector family', BRAND.detectorFamily],
              ['Licence status', 'Research use'],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between gap-4">
                <dt className="text-muted">{k}</dt>
                <dd className="font-mono text-text">{v}</dd>
              </div>
            ))}
          </dl>
        </Card>
      </div>
    </>
  );
};

export default Settings;

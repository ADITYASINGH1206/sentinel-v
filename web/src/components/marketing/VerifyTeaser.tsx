import React, { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { AnimatePresence, m, useInView } from 'framer-motion';
import { ArrowRight, CheckCircle2, Circle } from 'lucide-react';
import { Card, Reveal, SectionHeading, buttonVariants, cn } from '../../design/ui';
import { usePreferences } from '../../design/preferences';

const CHECKS = [
  ['Signature', 'Ed25519 over RFC 8785 canonical JSON, against the published key'],
  ['File hash', 'SHA-256 of your copy of the video, computed in your browser'],
  ['Batch inclusion', 'Merkle proof from the receipt to its batch root'],
  ['On-chain anchor', 'The batch root recorded on an EVM testnet'],
  ['Model & policy', 'Weights, calibration and policy hashes in the public registry'],
];

export const VerifyTeaser: React.FC = () => {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: '0px 0px -25% 0px' });
  const { reduceMotion } = usePreferences();
  const [done, setDone] = useState(0);

  useEffect(() => {
    if (!inView) return;
    if (reduceMotion) {
      setDone(CHECKS.length);
      return;
    }
    let i = 0;
    const id = window.setInterval(() => {
      i += 1;
      setDone(i);
      if (i >= CHECKS.length) window.clearInterval(id);
    }, 380);
    return () => window.clearInterval(id);
  }, [inView, reduceMotion]);

  return (
    <section id="verify" aria-labelledby="verify-title" className="scroll-mt-20 border-y border-border bg-surface/50 py-24">
      <div className="mx-auto grid max-w-6xl gap-12 px-4 sm:px-6 lg:grid-cols-2 lg:items-center">
        <div>
          <SectionHeading
            id="verify-title"
            eyebrow="Verify without trusting us"
            title="Every decision comes with a receipt anyone can check"
            body="Drop a receipt and, optionally, the original video into the public verifier. The checks run in your browser — the video never leaves your machine."
          />
          <Reveal delay={0.1} className="mt-8">
            <Link to="/verify" className={cn(buttonVariants({ variant: 'primary', size: 'lg' }), 'group')}>
              Verify a receipt <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
            </Link>
          </Reveal>
        </div>
        <Reveal>
          <Card className="overflow-hidden" >
            <div ref={ref} className="flex items-center justify-between border-b border-border px-5 py-3">
              <span className="text-sm font-semibold text-text">Verification checks</span>
              <span className="font-mono text-xs text-muted">example · {done}/{CHECKS.length}</span>
            </div>
            <ul className="divide-y divide-border">
              {CHECKS.map(([name, detail], i) => {
                const ok = i < done;
                return (
                  <li key={name} className="flex items-start gap-3 px-5 py-3.5">
                    <span className="relative mt-0.5 h-5 w-5 shrink-0">
                      <AnimatePresence initial={false} mode="wait">
                        {ok ? (
                          <m.span key="ok" initial={{ scale: 0.4, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="absolute inset-0 text-band-authentic">
                            <CheckCircle2 className="h-5 w-5" aria-hidden />
                          </m.span>
                        ) : (
                          <m.span key="wait" exit={{ opacity: 0 }} className="absolute inset-0 text-border">
                            <Circle className="h-5 w-5" aria-hidden />
                          </m.span>
                        )}
                      </AnimatePresence>
                    </span>
                    <div>
                      <p className={cn('text-sm font-medium transition-colors', ok ? 'text-text' : 'text-muted')}>{name}</p>
                      <p className="text-xs text-muted">{detail}</p>
                    </div>
                  </li>
                );
              })}
            </ul>
          </Card>
        </Reveal>
      </div>
    </section>
  );
};

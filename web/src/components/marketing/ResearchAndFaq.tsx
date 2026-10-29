import React, { useState } from 'react';
import { AnimatePresence, m } from 'framer-motion';
import { BookOpen, ChevronDown, FlaskConical, TriangleAlert } from 'lucide-react';
import { Card, Reveal, SectionHeading, cn } from '../../design/ui';
import { BRAND } from '../../brand';
import { REQUIRED_DISCLAIMER } from '../../copy/forbidden';

const LIMITATIONS = [
  'Not trained on fully generated (text-to-video) content.',
  'Calibration is fitted on FF++ and DFD validation data and does not automatically transfer to other sources.',
  'No audio analysis.',
  'Trained and tested on lightly compressed (c23) video only.',
  'No demographic performance analysis yet.',
];

export const Research: React.FC = () => (
  <section id="research" aria-labelledby="research-title" className="scroll-mt-20 py-24">
    <div className="mx-auto max-w-6xl px-4 sm:px-6">
      <SectionHeading
        id="research-title"
        eyebrow="Research"
        title="Open about what it can and cannot do"
        body={`${BRAND.name} is built on the ${BRAND.detectorFamily} detector family. Both papers are in preparation; results in this product come only from generated evaluation files.`}
      />
      <div className="mt-12 grid gap-4 md:grid-cols-3">
        <Reveal>
          <Card interactive className="h-full p-6">
            <BookOpen className="h-5 w-5 text-accent" aria-hidden />
            <p className="mt-4 text-xs font-semibold uppercase tracking-wider text-muted">Paper A · model</p>
            <h3 className="mt-1 text-base font-semibold text-text">S-MSDT: semantic–forensic video deepfake detection with validation-frozen calibration</h3>
            <p className="mt-2 text-sm text-muted">In preparation.</p>
          </Card>
        </Reveal>
        <Reveal delay={0.06}>
          <Card interactive className="h-full p-6">
            <FlaskConical className="h-5 w-5 text-violet" aria-hidden />
            <p className="mt-4 text-xs font-semibold uppercase tracking-wider text-muted">Paper B · system</p>
            <h3 className="mt-1 text-base font-semibold text-text">Calibrated and auditable video deepfake screening</h3>
            <p className="mt-2 text-sm text-muted">
              In preparation.{' '}
              <a className="text-accent hover:underline" href={`${BRAND.repoUrl}/tree/main/eval`} target="_blank" rel="noreferrer">
                Evaluation harness
              </a>
            </p>
          </Card>
        </Reveal>
        <Reveal delay={0.12}>
          <Card className="h-full border-band-review/30 p-6">
            <TriangleAlert className="h-5 w-5 text-band-review" aria-hidden />
            <p className="mt-4 text-xs font-semibold uppercase tracking-wider text-muted">Known limitations</p>
            <ul className="mt-2 space-y-2 text-sm text-text">
              {LIMITATIONS.map((l) => (
                <li key={l} className="flex gap-2">
                  <span className="mt-2 h-1 w-1 shrink-0 rounded-full bg-band-review" aria-hidden />
                  {l}
                </li>
              ))}
            </ul>
          </Card>
        </Reveal>
      </div>
    </div>
  </section>
);

const FAQS: Array<{ q: string; a: React.ReactNode }> = [
  {
    q: `Does a ${BRAND.name} result settle whether a video was manipulated?`,
    a: (
      <>
        No. {REQUIRED_DISCLAIMER} Results come as one of four bands — likely authentic, needs review, likely manipulated, or inconclusive — and
        the thresholds come from your policy.
      </>
    ),
  },
  {
    q: 'What does the score mean?',
    a: 'The score is calibrated on held-out validation data for an even mix of authentic and manipulated videos. The console also shows it re-weighted for the prevalence configured in your policy, which is usually much lower.',
  },
  {
    q: "What can't it detect?",
    a: `It looks for manipulated faces (identity swaps and expression re-enactment). It is not trained on fully generated video, it ignores audio, and it returns "inconclusive" when no usable face is found.`,
  },
  {
    q: 'Where are my videos stored, and for how long?',
    a: 'Media is kept for 30 days and evidence maps for 180 days by default; receipts contain only hashes and are kept indefinitely. Operators can change these limits or erase media on request.',
  },
  {
    q: 'How do I check a receipt without trusting the operator?',
    a: 'Open the public verifier and drop in the receipt and, optionally, your copy of the video. Signature and file-hash checks run entirely in your browser.',
  },
  {
    q: 'Can I self-host it?',
    a: 'Yes. The repository ships Docker Compose files for a single GPU node, and a mock engine for running the console without model weights.',
  },
  {
    q: 'Can I use it commercially?',
    a: 'Not yet. The models are trained on datasets released for research use, so deployments currently run in research-use mode until licensing is confirmed.',
  },
];

export const Faq: React.FC = () => {
  const [open, setOpen] = useState<number | null>(0);
  return (
    <section id="faq" aria-labelledby="faq-title" className="scroll-mt-20 border-t border-border bg-surface/50 py-24">
      <div className="mx-auto max-w-3xl px-4 sm:px-6">
        <SectionHeading id="faq-title" eyebrow="FAQ" title="Questions people ask first" center />
        <div className="mt-10 divide-y divide-border rounded-md border border-border bg-surface">
          {FAQS.map((f, i) => {
            const isOpen = open === i;
            return (
              <div key={f.q}>
                <h3>
                  <button
                    type="button"
                    aria-expanded={isOpen}
                    aria-controls={`faq-panel-${i}`}
                    id={`faq-button-${i}`}
                    onClick={() => setOpen(isOpen ? null : i)}
                    className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left text-sm font-medium text-text hover:bg-surface-2"
                  >
                    {f.q}
                    <ChevronDown className={cn('h-4 w-4 shrink-0 text-muted transition-transform duration-200', isOpen && 'rotate-180')} aria-hidden />
                  </button>
                </h3>
                <AnimatePresence initial={false}>
                  {isOpen && (
                    <m.div
                      id={`faq-panel-${i}`}
                      role="region"
                      aria-labelledby={`faq-button-${i}`}
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2, ease: [0.2, 0, 0, 1] }}
                      className="overflow-hidden"
                    >
                      <p className="px-5 pb-5 text-sm leading-relaxed text-muted">{f.a}</p>
                    </m.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};

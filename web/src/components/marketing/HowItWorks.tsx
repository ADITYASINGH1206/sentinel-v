import React, { useRef } from 'react';
import { m, useInView } from 'framer-motion';
import { FileVideo, ScanFace, Layers, Gauge, FileSignature } from 'lucide-react';
import { SectionHeading } from '../../design/ui';

const STEPS = [
  { icon: FileVideo, title: 'Upload or link a video', body: 'Files or URLs are hashed with SHA-256 on arrival; duplicates reuse earlier results.' },
  { icon: ScanFace, title: 'Faces detected and tracked', body: 'Up to four face tracks are aligned and cut into short clips the same way as in training.' },
  { icon: Layers, title: 'A two-stage cascade screens', body: 'A fast single-frame model exits clear cases early; the rest go to the temporal model.' },
  { icon: Gauge, title: 'Calibrated score and evidence', body: 'You get a calibrated score, a decision band from your policy, and a patch-evidence map.' },
  { icon: FileSignature, title: 'A signed receipt', body: 'Hashes of the video, model, calibration and policy are signed so anyone can verify them.' },
];

export const HowItWorks: React.FC = () => {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: '0px 0px -20% 0px' });

  return (
    <section id="how" aria-labelledby="how-title" className="scroll-mt-20 py-24">
      <div className="mx-auto max-w-6xl px-4 sm:px-6">
        <SectionHeading
          id="how-title"
          eyebrow="How it works"
          title="From upload to a verifiable decision in five steps"
          body="The serving pipeline is built to match the research evaluation step for step, and a parity check guards it, so a score means what the calibration says it means."
        />
        <div ref={ref} className="relative mt-14">
          {/* connector line (desktop): grows left-to-right when the section enters the viewport */}
          <div className="pointer-events-none absolute left-[10%] right-[10%] top-6 hidden h-px bg-border lg:block" aria-hidden>
            <m.div
              className="h-full origin-left bg-gradient-to-r from-accent via-accent to-violet"
              initial={{ scaleX: 0 }}
              animate={{ scaleX: inView ? 1 : 0 }}
              transition={{ duration: 1.2, ease: [0.3, 0, 0, 1] }}
            />
          </div>
          <m.ol
            className="grid gap-8 lg:grid-cols-5 lg:gap-6"
            initial="hidden"
            animate={inView ? 'show' : 'hidden'}
            variants={{ hidden: {}, show: { transition: { staggerChildren: 0.09 } } }}
          >
            {STEPS.map((s, i) => (
              <m.li
                key={s.title}
                variants={{ hidden: { opacity: 0, y: 14 }, show: { opacity: 1, y: 0, transition: { duration: 0.35, ease: [0.2, 0, 0, 1] } } }}
                className="relative flex gap-4 lg:flex-col lg:items-center lg:text-center"
              >
                {i < STEPS.length - 1 && <span className="absolute left-6 top-14 h-[calc(100%-1rem)] w-px bg-border lg:hidden" aria-hidden />}
                <span className="relative z-10 grid h-12 w-12 shrink-0 place-items-center rounded-full border border-accent/30 bg-surface text-accent shadow-1">
                  <s.icon className="h-5 w-5" aria-hidden />
                  <span className="absolute -right-1 -top-1 grid h-5 w-5 place-items-center rounded-full bg-accent font-mono text-[10px] font-semibold text-accent-contrast">
                    {i + 1}
                  </span>
                </span>
                <div>
                  <h3 className="text-sm font-semibold text-text">{s.title}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-muted">{s.body}</p>
                </div>
              </m.li>
            ))}
          </m.ol>
        </div>
      </div>
    </section>
  );
};

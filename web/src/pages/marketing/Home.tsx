import React, { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { m } from 'framer-motion';
import { ArrowRight, Eye, FileCheck2, Scale, Users } from 'lucide-react';
import { ScanHero } from '../../components/marketing/ScanHero';
import { HowItWorks } from '../../components/marketing/HowItWorks';
import { FeatureBento } from '../../components/marketing/FeatureBento';
import { BaseRateCalculator } from '../../components/marketing/BaseRateCalculator';
import { VerifyTeaser } from '../../components/marketing/VerifyTeaser';
import { Faq, Research } from '../../components/marketing/ResearchAndFaq';
import { buttonVariants, cn } from '../../design/ui';
import { BRAND } from '../../brand';

const PRINCIPLES = [
  { icon: Scale, label: 'Calibrated on held-out validation data' },
  { icon: Eye, label: 'Evidence for every decision' },
  { icon: FileCheck2, label: 'Signed, verifiable receipts' },
  { icon: Users, label: 'Human review by design' },
];

const heroItem = {
  hidden: { opacity: 0, y: 14 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: [0.2, 0, 0, 1] } },
};

const Home: React.FC = () => {
  useEffect(() => {
    document.title = `${BRAND.name} — calibrated video deepfake screening`;
  }, []);

  return (
    <>
      <section aria-labelledby="hero-title" className="relative -mt-16 overflow-hidden pb-24 pt-32 sm:pt-36">
        <div className="hero-wash absolute inset-0 -z-10" aria-hidden />
        <div className="grid-bg absolute inset-0 -z-10 opacity-30" aria-hidden />
        <div className="absolute -top-48 left-1/2 -z-10 h-[460px] w-[820px] -translate-x-1/2 animate-drift rounded-full bg-[radial-gradient(closest-side,rgb(var(--accent)/0.22),transparent)] blur-3xl" aria-hidden />
        <div className="mx-auto grid max-w-6xl items-center gap-16 px-4 sm:px-6 lg:grid-cols-[1.05fr_1fr]">
          <m.div initial="hidden" animate="show" variants={{ hidden: {}, show: { transition: { staggerChildren: 0.08 } } }}>
            <m.p variants={heroItem} className="inline-flex items-center gap-2 rounded-full border border-border bg-surface/80 px-3 py-1 text-xs font-medium text-muted backdrop-blur">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-accent opacity-60 motion-reduce:hidden" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-accent" />
              </span>
              Video deepfake screening · research preview
            </m.p>
            <m.h1 variants={heroItem} id="hero-title" className="mt-6 text-5xl leading-[1.04] text-text sm:text-6xl lg:text-[68px]">
              See where a video may have been altered — <span className="italic text-accent">and how sure we really are.</span>
            </m.h1>
            <m.p variants={heroItem} className="mt-6 max-w-xl text-lg leading-relaxed text-muted">
              {BRAND.name} screens faces in video with the {BRAND.detectorFamily} detector family. It returns a calibrated score, an evidence map, a
              decision band you control, and a signed receipt anyone can verify.
            </m.p>
            <m.div variants={heroItem} className="mt-8 flex flex-wrap items-center gap-3">
              <Link to="/app" className={cn(buttonVariants({ size: 'lg' }), 'group')}>
                Open console <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-0.5" />
              </Link>
              <a href="#how" className={buttonVariants({ variant: 'secondary', size: 'lg' })}>
                How it works
              </a>
            </m.div>
          </m.div>
          <m.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.6, ease: [0.2, 0, 0, 1], delay: 0.15 }}>
            <ScanHero />
          </m.div>
        </div>

        <m.ul
          className="mx-auto mt-24 grid max-w-6xl gap-3 px-4 sm:grid-cols-2 sm:px-6 lg:grid-cols-4"
          initial="hidden"
          whileInView="show"
          viewport={{ once: true }}
          variants={{ hidden: {}, show: { transition: { staggerChildren: 0.06 } } }}
        >
          {PRINCIPLES.map((p) => (
            <m.li key={p.label} variants={heroItem} className="flex items-center gap-3 rounded-md border border-border bg-surface/70 px-4 py-3 text-sm text-text backdrop-blur">
              <p.icon className="h-4 w-4 shrink-0 text-accent" aria-hidden />
              {p.label}
            </m.li>
          ))}
        </m.ul>
      </section>

      <HowItWorks />
      <FeatureBento />
      <BaseRateCalculator />
      <VerifyTeaser />
      <Research />
      <Faq />

      <section aria-labelledby="cta-title" className="py-24">
        <div className="mx-auto max-w-6xl px-4 sm:px-6">
          <div className="relative overflow-hidden rounded-lg border border-accent/25 bg-gradient-to-br from-accent/15 via-surface to-violet/10 px-6 py-14 text-center sm:px-12">
            <div className="grid-bg absolute inset-0 opacity-40" aria-hidden />
            <div className="relative">
              <h2 id="cta-title" className="text-3xl font-semibold tracking-tight text-text sm:text-4xl">
                Screen a video in your console
              </h2>
              <p className="mx-auto mt-4 max-w-xl text-muted">
                Run it locally with the mock engine in minutes, or connect a GPU worker with the S-MSDT bundle.
              </p>
              <div className="mt-8 flex flex-wrap justify-center gap-3">
                <Link to="/app" className={buttonVariants({ size: 'lg' })}>
                  Open console
                </Link>
                <a href={BRAND.repoUrl} target="_blank" rel="noreferrer" className={buttonVariants({ variant: 'secondary', size: 'lg' })}>
                  View source
                </a>
              </div>
            </div>
          </div>
        </div>
      </section>
    </>
  );
};

export default Home;

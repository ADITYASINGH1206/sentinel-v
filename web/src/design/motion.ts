/**
 * Motion tokens (docs/design/motion.md). Animate only opacity/transform/pathLength.
 * Reduced motion is handled globally by <MotionConfig> in PreferencesProvider.
 */
export const dur = { instant: 0.08, fast: 0.14, base: 0.2, slow: 0.32, page: 0.24 } as const;

export const ease = {
  standard: [0.2, 0, 0, 1] as [number, number, number, number],
  emphasized: [0.3, 0, 0, 1] as [number, number, number, number],
  exit: [0.4, 0, 1, 1] as [number, number, number, number],
};

export const fadeUp = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: dur.slow, ease: ease.standard } },
};

export const fadeIn = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { duration: dur.base, ease: ease.standard } },
};

export const stagger = (step = 0.05, delay = 0) => ({
  hidden: {},
  show: { transition: { staggerChildren: step, delayChildren: delay } },
});

export const pageTransition = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: { duration: dur.page, ease: ease.standard } },
  exit: { opacity: 0, y: -4, transition: { duration: dur.fast, ease: ease.exit } },
};

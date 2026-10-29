import { describe, it, expect } from 'vitest';
import { FORBIDDEN_WORDS, REQUIRED_DISCLAIMER, validateCopy } from '../copy/forbidden';

describe('Copy Compliance and Anti-Deception Guardrails (SPEC §14.13)', () => {
  it('rejects bare FAKE and REAL keywords', () => {
    expect(validateCopy('This video is completely FAKE').valid).toBe(false);
    expect(validateCopy('This is a REAL video').valid).toBe(false);
  });

  it('rejects deceptive confidence claims', () => {
    expect(validateCopy('We are 100% sure this video is manipulated').valid).toBe(false);
    expect(validateCopy('This output is guaranteed accurate').valid).toBe(false);
    expect(validateCopy('AI-certified authentic content').valid).toBe(false);
  });

  it('allows approved decision band labels', () => {
    expect(validateCopy('Likely authentic').valid).toBe(true);
    expect(validateCopy('Needs review').valid).toBe(true);
    expect(validateCopy('Likely manipulated').valid).toBe(true);
    expect(validateCopy('Inconclusive').valid).toBe(true);
  });

  it('permits proof only within the exact mandatory disclaimer', () => {
    expect(validateCopy(REQUIRED_DISCLAIMER).valid).toBe(true);
    expect(validateCopy('This cryptographic receipt is absolute proof of deepfake.').valid).toBe(false);
  });
});


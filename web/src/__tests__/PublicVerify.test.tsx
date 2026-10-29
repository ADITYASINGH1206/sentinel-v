import React from 'react';
import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { PublicVerify } from '../pages/verify/PublicVerifyPage';

describe('PublicVerify Component (SPEC §10)', () => {
  it('renders initial verification state with all 5 steps', () => {
    render(<PublicVerify />);

    expect(screen.getByText('Public Receipt Verifier')).toBeDefined();
    expect(screen.getByText('ZERO-TRUST CLIENT VERIFICATION')).toBeDefined();
    expect(screen.getByText('Zero-Trust Verification Checklist')).toBeDefined();

    // 5 checks
    expect(screen.getByText('Ed25519 Digital Signature')).toBeDefined();
    expect(screen.getByText('Content Hash Integrity (SHA-256)')).toBeDefined();
    expect(screen.getByText('RFC 6962 Merkle Batch Inclusion')).toBeDefined();
    expect(screen.getByText('EVM On-Chain Anchor')).toBeDefined();
    expect(screen.getByText('Model Weights & Policy Registry')).toBeDefined();

    // Mandatory disclaimer
    expect(screen.getByText(/Screening aid/)).toBeDefined();
  });

  it('loads sample receipt and updates verification statuses', async () => {
    render(<PublicVerify />);

    const loadSampleBtn = screen.getByRole('button', { name: /Load Sample Receipt/i });
    fireEvent.click(loadSampleBtn);

    // Should display loaded receipt ID and results
    expect(screen.getByText('rcpt_demo_public_8832')).toBeDefined();
    expect(screen.getByText('Likely authentic')).toBeDefined();
    expect(screen.getByText('Decision Band:')).toBeDefined();

    // Signature check status
    await waitFor(() => {
      expect(
        screen.getByText(/Cryptographically valid Ed25519 digital signature/)
      ).toBeDefined();
    });
  });

  it('displays textarea for manual receipt input', () => {
    render(<PublicVerify />);

    const textarea = screen.getByPlaceholderText(/Paste detection receipt JSON here/i);
    expect(textarea).toBeDefined();

    // Entering invalid JSON shows error message
    fireEvent.change(textarea, { target: { value: 'invalid-json' } });
    expect(screen.getAllByText(/Invalid JSON format in receipt file/i).length).toBeGreaterThan(0);
  });
});

import React, { useCallback, useEffect, useState } from 'react';
import { AnimatePresence, m } from 'framer-motion';
import {
  ShieldCheck,
  ShieldAlert,
  FileCheck2,
  Upload,
  CheckCircle2,
  XCircle,
  HelpCircle,
  MinusCircle,
  Hash,
  Copy,
  Check,
  RefreshCw,
  Loader2,
} from 'lucide-react';
import { BandChip, DecisionBand } from '../../components/BandChip';
import { ScoreReadout } from '../../components/ScoreReadout';
import { REQUIRED_DISCLAIMER } from '../../copy/forbidden';
import { Badge, Button, Card, cn } from '../../design/ui';
import {
  canonicalizeJson,
  computeFileSha256,
  sha256Bytes,
  bytesToHex,
  verifyClientMerkleProof,
  verifyEd25519Signature,
} from '../../utils/verifier';
import sampleReceipt from '../../content/demo-receipt.json';

export interface VerificationCheck {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'verifying' | 'pass' | 'fail' | 'skipped';
  detail: string;
}

/** Signed sample receipt (historical issuer name) for trying the verifier without a server. */
const SAMPLE_DEMO_RECEIPT = sampleReceipt as Record<string, unknown>;

const INITIAL_CHECKS: VerificationCheck[] = [
  {
    id: 'signature',
    name: 'Ed25519 Digital Signature',
    description: 'Checks the signature over the RFC 8785 canonical JSON of the receipt',
    status: 'pending',
    detail: 'Awaiting receipt input',
  },
  {
    id: 'file_hash',
    name: 'Content Hash Integrity (SHA-256)',
    description: 'Compares the SHA-256 of your copy of the video with the receipt',
    status: 'pending',
    detail: 'Add the video file to check it (optional)',
  },
  {
    id: 'merkle_proof',
    name: 'RFC 6962 Merkle Batch Inclusion',
    description: 'Recomputes the inclusion path from this receipt to its batch root',
    status: 'pending',
    detail: 'Verifies leaf-to-root audit path',
  },
  {
    id: 'chain_anchor',
    name: 'EVM On-Chain Anchor',
    description: 'Looks for the batch root anchored on an EVM testnet',
    status: 'pending',
    detail: 'Reads the ReceiptAnchor anchor record',
  },
  {
    id: 'model_registry',
    name: 'Model Weights & Policy Registry',
    description: 'Checks the model and policy recorded in the receipt',
    status: 'pending',
    detail: 'Checks registered model bundle hashes',
  },
];

type KeySet = { keys?: Array<{ kid?: string; key_id?: string; x?: string; public_key_b64?: string }> };

async function lookupPublishedKey(keyId: string | undefined): Promise<string | null> {
  if (!keyId) return null;
  try {
    const res = await fetch('/.well-known/sv-keys.json', { headers: { Accept: 'application/json' } });
    if (!res.ok) return null;
    const body = (await res.json()) as KeySet;
    const k = body.keys?.find((x) => x.kid === keyId || x.key_id === keyId);
    return k?.x ?? k?.public_key_b64 ?? null;
  } catch {
    return null;
  }
}

const STATUS_STYLE: Record<VerificationCheck['status'], { icon: typeof CheckCircle2; className: string; badge: string }> = {
  pass: { icon: CheckCircle2, className: 'text-band-authentic', badge: 'border-band-authentic/30 bg-band-authentic/10 text-band-authentic' },
  fail: { icon: XCircle, className: 'text-band-manipulated', badge: 'border-band-manipulated/30 bg-band-manipulated/10 text-band-manipulated' },
  skipped: { icon: MinusCircle, className: 'text-muted', badge: 'border-border bg-surface-2 text-muted' },
  verifying: { icon: Loader2, className: 'animate-spin text-accent', badge: 'border-accent/30 bg-accent/10 text-accent' },
  pending: { icon: HelpCircle, className: 'text-border', badge: 'border-border bg-surface-2 text-muted' },
};

export const PublicVerify: React.FC = () => {
  const [receiptJson, setReceiptJson] = useState<string>('');
  const [parsedReceipt, setParsedReceipt] = useState<Record<string, unknown> | null>(null);
  const [mediaFile, setMediaFile] = useState<File | null>(null);
  const [mediaSha256, setMediaSha256] = useState<string | null>(null);
  const [hashProgress, setHashProgress] = useState<number | null>(null);
  const [copied, setCopied] = useState(false);
  const [checks, setChecks] = useState<VerificationCheck[]>(INITIAL_CHECKS);

  const parseAndVerify = useCallback(
    async (jsonStr: string, file: File | null = mediaFile, computedHash: string | null = mediaSha256) => {
      let receipt: Record<string, unknown>;
      try {
        receipt = JSON.parse(jsonStr);
        setParsedReceipt(receipt);
      } catch {
        setParsedReceipt(null);
        setChecks((prev) => prev.map((c) => ({ ...c, status: 'fail', detail: 'Invalid JSON format in receipt file' })));
        return;
      }

      const update = (i: number, patch: Partial<VerificationCheck>) =>
        setChecks((prev) => prev.map((c, idx) => (idx === i ? { ...c, ...patch } : c)));
      setChecks(INITIAL_CHECKS.map((c) => ({ ...c, status: 'verifying', detail: 'Checking…' })));

      // 1. Signature — only "pass" when a public key actually verified it.
      const issuer = receipt.issuer as Record<string, unknown> | undefined;
      const sig = receipt.signature as Record<string, unknown> | undefined;
      if (!sig || !sig.value) {
        update(0, { status: 'fail', detail: 'Receipt contains no signature block' });
      } else {
        let pubKey = typeof issuer?.public_key === 'string' ? (issuer.public_key as string) : null;
        let keySource = 'key embedded in the receipt';
        if (!pubKey) {
          pubKey = await lookupPublishedKey(issuer?.key_id as string | undefined);
          keySource = 'published key from /.well-known/sv-keys.json';
        }
        if (!pubKey) {
          update(0, { status: 'skipped', detail: `Public key ${String(issuer?.key_id ?? '')} is not available, so the signature was not checked.` });
        } else {
          const ok = verifyEd25519Signature(receipt, pubKey);
          update(0, {
            status: ok ? 'pass' : 'fail',
            detail: ok
              ? `Cryptographically valid Ed25519 digital signature verified in your browser (${keySource})`
              : 'Ed25519 signature verification failed. The receipt was altered or signed with another key.',
          });
        }
      }

      // 2. Media file hash
      const expected = (receipt.content as Record<string, unknown> | undefined)?.sha256 as string | undefined;
      if (file || computedHash) {
        const hash = computedHash || (file ? await computeFileSha256(file) : '');
        const match = Boolean(expected) && hash.toLowerCase() === (expected || '').toLowerCase();
        update(1, {
          status: match ? 'pass' : 'fail',
          detail: match ? `SHA-256 match confirmed: ${hash.substring(0, 16)}…` : `SHA-256 mismatch: expected ${expected?.substring(0, 12)}…, got ${hash.substring(0, 12)}…`,
        });
      } else {
        update(1, { status: 'skipped', detail: 'No video provided. Content hash not checked.' });
      }

      // 3. Merkle inclusion — only "pass" when a proof reproduces the root.
      const merkle = receipt.merkle as Record<string, unknown> | undefined;
      if (merkle && merkle.root && Array.isArray(merkle.proof) && merkle.proof.length > 0) {
        const sansMerkle = { ...receipt };
        delete sansMerkle.merkle;
        delete sansMerkle.anchor;
        const receiptHash = bytesToHex(await sha256Bytes(new TextEncoder().encode(canonicalizeJson(sansMerkle))));
        const ok = await verifyClientMerkleProof(receiptHash, merkle.proof as Array<{ position: 'left' | 'right'; data: string }>, merkle.root as string);
        update(2, {
          status: ok ? 'pass' : 'fail',
          detail: ok ? `Inclusion verified against batch root ${String(merkle.root).substring(0, 16)}…` : 'The inclusion path does not reproduce the batch root',
        });
      } else if (merkle && merkle.root) {
        update(2, { status: 'skipped', detail: `Batch root ${String(merkle.root).substring(0, 16)}… is listed, but no inclusion proof was provided.` });
      } else {
        update(2, { status: 'skipped', detail: 'Receipt is standalone; Merkle batching not applied.' });
      }

      // 4. Chain anchor — the browser does not query a chain yet, so this is informational.
      const anchor = receipt.anchor as Record<string, unknown> | undefined;
      update(3, {
        status: 'skipped',
        detail: anchor?.tx_hash
          ? `Anchor recorded in tx ${String(anchor.tx_hash).substring(0, 16)}… on chain ${String(anchor.chain_id ?? '?')}. Look it up on a block explorer; this page does not query the chain yet.`
          : 'On-chain anchoring disabled or pending the next batch.',
      });

      // 5. Model & policy — recorded values; registry comparison needs the API.
      const model = receipt.model as Record<string, unknown> | undefined;
      const models = receipt.models as Array<Record<string, unknown>> | undefined;
      const policy = receipt.policy as Record<string, unknown> | undefined;
      const modelLabel = model?.bundle_id
        ? `${model.bundle_id} (weights ${String(model.weights_sha256 ?? '').substring(0, 12)}…)`
        : models?.length
          ? models.map((x) => `${x.model_id} (${String(x.weights_sha256 ?? '').substring(0, 8)}…)`).join(', ')
          : null;
      if (!modelLabel) {
        update(4, { status: 'fail', detail: 'Missing required model weights or policy specification.' });
      } else {
        update(4, {
          status: 'skipped',
          detail: `Recorded: model ${modelLabel} under policy ${String(policy?.policy_id ?? '—')} v${String(policy?.policy_version ?? policy?.version ?? '—')}. Registry comparison is not available offline.`,
        });
      }
    },
    [mediaFile, mediaSha256]
  );

  // ?receipt=<id> prefill from the API
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get('receipt');
    if (!id) return;
    fetch(`/v1/receipts/${encodeURIComponent(id)}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`HTTP ${r.status}`))))
      .then((body) => {
        const s = JSON.stringify(body, null, 2);
        setReceiptJson(s);
        parseAndVerify(s, null, null);
      })
      .catch(() => undefined);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleReceiptUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const content = event.target?.result as string;
      setReceiptJson(content);
      parseAndVerify(content, mediaFile);
    };
    reader.readAsText(file);
  };

  const handleMediaUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setMediaFile(file);
    setHashProgress(0);
    const hash = await computeFileSha256(file, setHashProgress);
    setHashProgress(null);
    setMediaSha256(hash);
    if (receiptJson) parseAndVerify(receiptJson, file, hash);
  };

  const loadDemoReceipt = () => {
    const demoStr = JSON.stringify(SAMPLE_DEMO_RECEIPT, null, 2);
    setReceiptJson(demoStr);
    parseAndVerify(demoStr, mediaFile, mediaSha256);
  };

  const copyReceipt = () => {
    if (!receiptJson) return;
    navigator.clipboard?.writeText(receiptJson).catch(() => undefined);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 2000);
  };

  const anyFail = checks.some((c) => c.status === 'fail');
  const anyPass = checks.some((c) => c.status === 'pass');
  const settled = checks.every((c) => c.status !== 'verifying' && c.status !== 'pending');
  const allPassed = settled && !anyFail && anyPass;

  const resultData = parsedReceipt?.result as Record<string, unknown> | undefined;
  const rawBand = resultData?.decision as string | undefined;
  const decisionBand: DecisionBand =
    rawBand === 'likely_authentic' || rawBand === 'needs_review' || rawBand === 'likely_manipulated' || rawBand === 'inconclusive' ? rawBand : 'inconclusive';
  const pBal = typeof resultData?.p_bal === 'number' ? resultData.p_bal : null;
  const pPrior = typeof resultData?.p_prior === 'number' ? resultData.p_prior : undefined;
  const policy = parsedReceipt?.policy as Record<string, unknown> | undefined;
  const prevalence = typeof policy?.prior_prevalence === 'number' ? policy.prior_prevalence : 0.01;
  const humanReview = (parsedReceipt?.review ?? parsedReceipt?.human_review) as Record<string, unknown> | undefined;
  const passCount = checks.filter((c) => c.status === 'pass').length;

  return (
    <div className="mx-auto max-w-6xl px-4 pb-24 pt-10 sm:px-6">
      <header className="mb-8 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <h1 className="text-3xl font-semibold tracking-tight text-text">Public Receipt Verifier</h1>
            <Badge tone="success" className="font-mono">ZERO-TRUST CLIENT VERIFICATION</Badge>
          </div>
          <p className="max-w-2xl text-sm text-muted">
            Check a detection receipt's signature, your copy of the video, and its batch inclusion directly in your browser. The video never leaves your
            machine.
          </p>
        </div>
        <Button variant="secondary" onClick={loadDemoReceipt}>
          <RefreshCw className="h-4 w-4 text-accent" />
          Load Sample Receipt
        </Button>
      </header>

      <div className="grid gap-6 lg:grid-cols-12">
        <div className="flex flex-col gap-6 lg:col-span-7">
          <div className="grid gap-4 sm:grid-cols-2">
            <Card className="flex flex-col justify-between p-4">
              <div>
                <div className="mb-2 flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-sm font-semibold text-text">
                    <FileCheck2 className="h-4 w-4 text-accent" /> Detection receipt (.json)
                  </span>
                  {parsedReceipt && <Badge tone="success">Loaded</Badge>}
                </div>
                <p className="mb-3 text-xs text-muted">A signed receipt exported from a case page.</p>
              </div>
              <label className="flex cursor-pointer flex-col items-center justify-center gap-1.5 rounded-md border border-dashed border-border bg-surface-2/50 p-4 transition-colors hover:border-accent hover:bg-accent/5">
                <Upload className="h-4 w-4 text-muted" />
                <span className="text-xs font-medium text-muted">Select receipt JSON</span>
                <input type="file" accept=".json,application/json" onChange={handleReceiptUpload} className="sr-only" />
              </label>
            </Card>
            <Card className="flex flex-col justify-between p-4">
              <div>
                <div className="mb-2 flex items-center justify-between gap-2">
                  <span className="flex items-center gap-1.5 text-sm font-semibold text-text">
                    <Hash className="h-4 w-4 text-violet" /> Video file (optional)
                  </span>
                  {mediaFile && <Badge className="max-w-[110px] truncate">{mediaFile.name}</Badge>}
                </div>
                <p className="mb-3 text-xs text-muted">Hashed in your browser in chunks; never uploaded.</p>
              </div>
              <label className="relative flex cursor-pointer flex-col items-center justify-center gap-1.5 overflow-hidden rounded-md border border-dashed border-border bg-surface-2/50 p-4 transition-colors hover:border-accent hover:bg-accent/5">
                <Upload className="h-4 w-4 text-muted" />
                <span className="text-xs font-medium text-muted">{hashProgress != null ? `Hashing… ${Math.round(hashProgress * 100)}%` : 'Select video file'}</span>
                {hashProgress != null && <span className="absolute bottom-0 left-0 h-0.5 bg-accent transition-[width]" style={{ width: `${hashProgress * 100}%` }} />}
                <input type="file" accept="video/*,.mp4,.webm,.mkv,.mov" onChange={handleMediaUpload} className="sr-only" />
              </label>
            </Card>
          </div>

          <Card className="overflow-hidden">
            <div className="flex items-center justify-between border-b border-border px-5 py-3">
              <span className="text-sm font-semibold text-text">Zero-Trust Verification Checklist</span>
              <span className="font-mono text-xs text-muted">
                {passCount}/{checks.length} verified
              </span>
            </div>
            <ul className="divide-y divide-border">
              {checks.map((check, index) => {
                const st = STATUS_STYLE[check.status];
                return (
                  <li key={check.id} className="flex items-start gap-3 p-4 text-sm">
                    <span className="mt-0.5 font-mono text-xs text-muted">{index + 1}.</span>
                    <span className="relative mt-0.5 h-4 w-4 shrink-0">
                      <AnimatePresence mode="wait" initial={false}>
                        <m.span key={check.status} initial={{ scale: 0.5, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.5, opacity: 0 }} transition={{ duration: 0.15 }} className="absolute inset-0">
                          <st.icon className={cn('h-4 w-4', st.className)} aria-hidden />
                        </m.span>
                      </AnimatePresence>
                    </span>
                    <div className="min-w-0 flex-1">
                      <div className="mb-0.5 flex items-center justify-between gap-2">
                        <span className="font-semibold text-text">{check.name}</span>
                        <span className={cn('rounded-full border px-2 py-0.5 font-mono text-[10px] font-semibold uppercase', st.badge)}>{check.status}</span>
                      </div>
                      <p className="mb-1.5 text-xs text-muted">{check.description}</p>
                      <p className="break-words rounded border border-border bg-bg px-2 py-1 font-mono text-[11px] text-text">{check.detail}</p>
                    </div>
                  </li>
                );
              })}
            </ul>
          </Card>
        </div>

        <div className="flex flex-col gap-6 lg:col-span-5">
          <m.div layout>
            <Card
              className={cn(
                'flex flex-col gap-4 p-5 transition-colors duration-300',
                allPassed ? 'border-band-authentic/40 bg-band-authentic/5' : parsedReceipt && anyFail ? 'border-band-manipulated/40 bg-band-manipulated/5' : ''
              )}
            >
              <div className="flex items-center gap-3">
                {allPassed ? (
                  <ShieldCheck className="h-8 w-8 shrink-0 text-band-authentic" />
                ) : parsedReceipt && anyFail ? (
                  <ShieldAlert className="h-8 w-8 shrink-0 text-band-manipulated" />
                ) : (
                  <HelpCircle className="h-8 w-8 shrink-0 text-muted" />
                )}
                <div>
                  <h2 className="text-sm font-semibold text-text">
                    {allPassed ? 'No integrity problems found' : parsedReceipt && anyFail ? 'Verification warning' : parsedReceipt ? 'Checking…' : 'Awaiting receipt'}
                  </h2>
                  <p className="text-xs text-muted">
                    {allPassed
                      ? 'Every check that could run passed. Skipped checks are listed on the left.'
                      : parsedReceipt && anyFail
                        ? 'One or more checks failed. The receipt or the file may have been changed.'
                        : 'Upload or paste a detection receipt to verify it.'}
                  </p>
                </div>
              </div>

              {parsedReceipt && (
                <div className="flex flex-col gap-3 border-t border-border pt-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-muted">Decision Band:</span>
                    <BandChip band={decisionBand} size="sm" />
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-xs text-muted">Receipt ID:</span>
                    <span className="truncate font-mono text-xs font-semibold text-accent">{String(parsedReceipt.receipt_id || 'unknown')}</span>
                  </div>
                  {humanReview && (
                    <div className="flex flex-col gap-1 rounded-md border border-band-review/30 bg-band-review/10 p-2 text-xs">
                      <span className="font-semibold text-text">Superseded by a human review ({String(humanReview.decision ?? humanReview.human_decision ?? '—')})</span>
                      <span className="text-muted">Reviewer role: {String(humanReview.reviewer_role ?? 'not recorded')}</span>
                    </div>
                  )}
                  {pBal != null && <ScoreReadout p_bal={pBal} p_prior={pPrior} prior_prevalence={prevalence} size="md" />}
                </div>
              )}
            </Card>
          </m.div>

          <Card className="flex min-h-[300px] flex-1 flex-col overflow-hidden">
            <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
              <span className="text-sm font-semibold text-text">Canonical receipt JSON</span>
              <button type="button" onClick={copyReceipt} disabled={!receiptJson} className="flex items-center gap-1 text-xs text-muted transition-colors hover:text-text disabled:opacity-40">
                {copied ? <Check className="h-3.5 w-3.5 text-band-authentic" /> : <Copy className="h-3.5 w-3.5" />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>
            <textarea
              value={receiptJson}
              onChange={(e) => {
                setReceiptJson(e.target.value);
                if (e.target.value.trim()) parseAndVerify(e.target.value);
              }}
              placeholder="Paste detection receipt JSON here or upload file above..."
              aria-label="Receipt JSON"
              className="w-full flex-1 resize-none border-none bg-bg p-4 font-mono text-[11px] text-text focus:outline-none"
              rows={14}
            />
          </Card>

          <p className="text-xs italic leading-relaxed text-muted">{REQUIRED_DISCLAIMER}</p>
        </div>
      </div>
    </div>
  );
};

export default PublicVerify;

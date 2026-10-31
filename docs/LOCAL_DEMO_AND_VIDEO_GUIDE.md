# VeriFrame (S-MSDT): Lightweight Frontend Demo & Video Recording Guide

This guide explains how to run and present the **VeriFrame** reviewer console with **zero external dependencies**:
- ❌ **No Docker required**
- ❌ **No GPU or Python environment required**
- ❌ **No databases or Redis required**
- ❌ **No smart contracts or blockchain fees**
- ✅ **100% browser-powered with built-in deterministic demo data, video playback, face tracking, patch heatmaps, and cryptographic receipts!**

---

## 1. Quick Setup (Takes 2 Minutes)

### Step 1: Clone or Pull the Repo
On your friend's laptop or PC, open the terminal:
```bash
git clone https://github.com/ADITYASINGH1206/veriframe.git
cd veriframe/web
```
*(If the repo is already cloned, just run `git checkout main && git pull origin main && cd web`)*.

### Step 2: Install and Start the Frontend
```bash
# Install dependencies
npm install

# Start local development server
npm run dev
```

The application is live at:
👉 **[https://veriframe-ai.vercel.app](https://veriframe-ai.vercel.app)**  
*(Or run locally at `http://localhost:5173`)*.

*(Because the backend is not running, the application automatically activates **Demo Mode**, loading 11 full pre-computed cases, sample video files, and interactive heatmaps directly in the browser).*

---

## 2. (Optional) Deploying a Live Link via Vercel (Free, 60 Seconds)

If you want a live, publicly accessible `https://...vercel.app` link for evaluators:
```bash
cd web
npx vercel
```
1. Follow the interactive prompts (Press `Enter` to accept defaults).
2. You will receive a live URL instantly (e.g. `https://veriframe.vercel.app`) that anyone can open on mobile or desktop without running any code!

---

## 3. Video Recording Script & Walkthrough (2 to 3 Minutes)

Use **OBS Studio**, **QuickTime Screen Recording** (Mac: `Cmd + Shift + 5`), or **Loom** to record full screen at 1080p.

### ⏱️ Scene 1: The Problem & Hero Overview (0:00 – 0:35)
- **What to show on screen:** Open `http://localhost:5173`. Scroll down the marketing home page through the architecture diagram and comparative table.
- **What to say:**
  > *"Hello everyone. Today we are presenting VeriFrame, an auditable, calibrated video deepfake screening platform powered by the S-MSDT detector family. Standard deepfake detectors suffer from two major flaws: they overfit to specific training boundaries, and they output uncalibrated binary 'fake percentages' that cause high false alarm rates in real-world media screening. VeriFrame solves this by pairing a parameter-efficient vision foundation backbone with validation-frozen Platt calibration, spatial evidence heatmaps, and tamper-proof cryptographic receipts."*

### ⏱️ Scene 2: The Reviewer Workspace & Queue (0:35 – 1:05)
- **What to show on screen:** Click the **"Open Review Console"** button in the header (or navigate to `/app`). Show the **Review Queue** table with multiple cases.
- **What to say:**
  > *"This is the analyst review workspace. Unlike opaque black-box classifiers, VeriFrame organizes uploaded videos into risk bands: 'Likely Authentic', 'Needs Review', and 'Likely Manipulated'. Each case displays calibrated probabilities adjusted for real-world base rates, preventing alert fatigue for trust-and-safety analysts."*

### ⏱️ Scene 3: Deep-Dive Analysis & Evidence Heatmaps (1:05 – 1:55)
- **What to show on screen:** Click on any case marked **"Needs Review"** or **"Likely Manipulated"** (e.g., case `case-1006` or `case-1008`).
  1. Click **Play** on the video player. Point out the bounding box tracking the subject's face.
  2. Drag the **Clip Scrubber Timeline** across the 8 temporal segments.
  3. Toggle the **"Patch Heatmap Overlay"** switch on the video player.
- **What to say:**
  > *"Here in the Case Detail view, the reviewer can inspect the exact evidence. The S-MSDT engine extracts facial tracks and divides the video into 8 temporal chunks. By scrubbing through the timeline, the analyst sees a spatial patch heatmap projected directly onto the video frames. This highlights whether the model is detecting perimeter blending seams from face-swaps or temporal flickering around the mouth from neural reenactments."*

### ⏱️ Scene 4: Calibration & Decision Policies (1:55 – 2:25)
- **What to show on screen:** Highlight the **Scores & Policy** card on the right-hand side. Click between the policy dropdown options (e.g. `Strict Low False-Positive Rate` vs. `Evidence Desk`).
- **What to say:**
  > *"On the right panel, we show our calibrated score. We use Platt scaling parameters fitted on validation data rather than raw model logits. Furthermore, our policy engine applies prevalence correction for low base-rates (such as 1% real-world fake prevalence), ensuring that high-stakes moderation actions are backed by mathematically honest precision estimates."*

### ⏱️ Scene 5: Cryptographic Receipt & Conclusion (2:25 – 3:00)
- **What to show on screen:** Scroll to the **Detection Receipt & Audit** section at the bottom. Point out the SHA-256 hashes and digital signature.
- **What to say:**
  > *"Finally, every decision produces an immutable Detection Receipt. It cryptographically binds the video content hash, model weights hash, calibration version, and evidence array with an Ed25519 digital signature. This gives newsrooms and legal teams complete auditability without trusting any central operator. In conclusion, VeriFrame bridges the gap between deep learning research and practical, auditable forensic screening. Thank you."*

---

## 4. Key Questions Evaluators Might Ask (Cheatsheet)

1. **Q: Where is the model running during this demo?**
   - *A: "The web console has a self-contained client-side demo mode with pre-computed calibration profiles and synthetic evidence tensors for zero-footprint evaluations, while our backend repository contains the full PyTorch inference engine with Celery workers for deployment on GPU clusters."*
2. **Q: Why are there no smart contracts deployed?**
   - *A: "Smart contract anchoring on EVM chains is designed as an optional batch layer for multi-organization notarization. The core cryptographic trust comes from local Ed25519 signatures and SHA-256 Merkle hashes, which are fully verified off-chain without gas costs."*
3. **Q: Why use an 8-clip temporal design?**
   - *A: "Single-frame detectors miss expression reenactments like NeuralTextures where facial boundaries don't change. Our 8-frame clips allow the TemporalDiff operator to isolate inter-frame motion jitter."*


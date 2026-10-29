"""Generate the original, synthetic demo video used by the console's DEMO DATA mode.

The clip shows an abstract geometric "face" (no real person) on a soft gradient, with a
slow head bob and a mouth that opens and closes. It exists only so the evidence player has
something to play when no API is connected.

Usage (from repo root):
    python3 web/scripts/make_demo_video.py web/public/demo/demo-subject.mp4
    (also writes web/public/demo/demo-subject.webm)

Requires: Pillow, numpy, ffmpeg on PATH.
"""

from __future__ import annotations

import math
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H, FPS, SECONDS = 640, 360, 24, 18


def background(t: float) -> Image.Image:
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    cx = W * (0.5 + 0.08 * math.sin(t * 0.25))
    cy = H * (0.42 + 0.05 * math.cos(t * 0.2))
    d = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2) / max(W, H)
    base = np.stack(
        [
            18 + 30 * (1 - d) + 6 * np.sin(xx / 90 + t * 0.3),
            27 + 50 * (1 - d),
            41 + 70 * (1 - d),
        ],
        axis=-1,
    )
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), "RGB")


def frame(i: int) -> Image.Image:
    t = i / FPS
    img = background(t)
    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx = W / 2 + 10 * math.sin(t * 0.7)
    cy = H / 2 + 6 * math.sin(t * 1.1)
    hw, hh = 78, 100
    # neck + shoulders
    d.rounded_rectangle(
        [cx - 26, cy + hh - 18, cx + 26, cy + hh + 40], radius=12, fill=(150, 160, 178, 255)
    )
    d.ellipse([cx - 150, cy + hh + 22, cx + 150, cy + hh + 160], fill=(64, 92, 120, 255))
    # head
    d.ellipse([cx - hw, cy - hh, cx + hw, cy + hh], fill=(198, 206, 220, 255))
    # hair cap
    d.chord(
        [cx - hw - 4, cy - hh - 8, cx + hw + 4, cy + hh * 0.2],
        start=180,
        end=360,
        fill=(52, 60, 78, 255),
    )
    # eyes (blink every ~4 s)
    blink = abs(math.sin(t * math.pi / 4.0)) > 0.985
    for ex in (-30, 30):
        if blink:
            d.line([cx + ex - 12, cy - 12, cx + ex + 12, cy - 12], fill=(40, 46, 60, 255), width=4)
        else:
            d.ellipse([cx + ex - 12, cy - 20, cx + ex + 12, cy - 4], fill=(245, 247, 250, 255))
            d.ellipse([cx + ex - 5, cy - 16, cx + ex + 5, cy - 6], fill=(30, 36, 50, 255))
    # nose
    d.line([cx, cy - 4, cx - 6, cy + 22, cx + 4, cy + 26], fill=(150, 158, 175, 255), width=3)
    # mouth (opens and closes; slightly irregular in the middle of the clip)
    open_amt = 6 + 10 * max(0.0, math.sin(t * 3.2))
    if 7.5 < t < 11.0:
        open_amt += 5 * math.sin(t * 17)
    d.ellipse(
        [cx - 26, cy + 48 - open_amt / 2, cx + 26, cy + 48 + open_amt / 2], fill=(120, 60, 72, 255)
    )
    layer = layer.filter(ImageFilter.GaussianBlur(0.6))
    img.paste(layer, (0, 0), layer)
    return img


def main(out: str) -> None:
    proc = subprocess.Popen(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "rawvideo",
            "-pix_fmt",
            "rgb24",
            "-s",
            f"{W}x{H}",
            "-r",
            str(FPS),
            "-i",
            "-",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-crf",
            "30",
            "-preset",
            "slow",
            "-movflags",
            "+faststart",
            out,
        ],
        stdin=subprocess.PIPE,
    )
    assert proc.stdin is not None
    for i in range(FPS * SECONDS):
        proc.stdin.write(frame(i).tobytes())
    proc.stdin.close()
    proc.wait()
    # WebM/VP9 copy for browsers without H.264 (e.g. open-source Chromium builds).
    webm = out.rsplit(".", 1)[0] + ".webm"
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            out,
            "-c:v",
            "libvpx-vp9",
            "-b:v",
            "0",
            "-crf",
            "40",
            "-row-mt",
            "1",
            "-deadline",
            "good",
            "-an",
            webm,
        ],
        check=True,
    )


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "web/public/demo/demo-subject.mp4")

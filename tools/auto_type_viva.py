#!/usr/bin/env python3
import sys
import time
import subprocess

ANSWERS = {
    1: "We address deepfake generalization failure and uncalibrated false alarms. Unlike standard CNNs that overfit to specific forgery boundaries, S-MSDT freezes a 304M CLIP ViT-L/14 backbone and trains only ~96k LayerNorm parameters with an inter-frame TemporalDiff operator, delivering robust zero-shot detection across unseen manipulation techniques.",

    2: "Our system uses FastAPI for async endpoints, Celery with Redis for decoupled GPU video inference, and PostgreSQL for relational audit tracking. Video files and spatial heatmaps are stored in MinIO S3. This microservice architecture guarantees non-blocking request handling, bounded memory limits, and tamper-proof verification.",

    3: "During Stage B training, NeuralTextures accuracy collapsed to 0.626 AUC due to PyTorch worker threads freezing identical random seeds and starving reenactment batches. We implemented a deterministic chunked sampler with process-unique hash seeding and restored missing spatial masks, successfully recovering accuracy to 0.823 AUC.",

    4: "We validated the model across 80/80 passing automated test suites. S-MSDTv2 achieved a 0.938 FaceForensics++ c23 macro AUC and 0.875 zero-shot AUC on Celeb-DF v2. Platt calibration yielded a 0.184 ECE with 47.1% true positive rate at a strict 1% false positive limit.",

    5: "Current limits include single-worker GPU queuing bottlenecks and focus on face-tracks rather than synthetic audio. To scale for production, we will deploy Celery workers on Kubernetes with KEDA queue autoscaling, and convert the PyTorch model to ONNX TensorRT with FP16 quantization to reduce latency by 60%."
}

def main():
    if len(sys.argv) < 2 or not sys.argv[1].isdigit():
        print("\nUsage: python3 tools/auto_type_viva.py <1-5>")
        print("Example: python3 tools/auto_type_viva.py 1\n")
        sys.exit(1)

    q = int(sys.argv[1])
    if q not in ANSWERS:
        print("Please enter a number between 1 and 5.")
        sys.exit(1)

    text = ANSWERS[q]

    print(f"\n==========================================")
    print(f"  VIVA AUTO-TYPER: QUESTION {q}")
    print(f"==========================================")
    print("👉 SWITCH TO YOUR BROWSER AND CLICK INSIDE THE ANSWER BOX NOW!")
    for i in range(4, 0, -1):
        print(f"⏳ Typing starts in {i} seconds...")
        time.sleep(1)

    print("⚡ TYPING NOW...")
    
    # Run AppleScript keystroke
    clean_text = text.replace('\\', '\\\\').replace('"', '\\"')
    apple_script = f'''
    tell application "System Events"
        keystroke "{clean_text}"
    end tell
    '''
    res = subprocess.run(["osascript", "-e", apple_script], capture_output=True, text=True)
    if res.returncode == 0:
        print(f"\n✅ Question {q} successfully typed into your browser box!\n")
    else:
        if "1002" in res.stderr:
            print("\n⚠️ macOS requires Accessibility permission for the app running this terminal!")
            print("To enable:")
            print("1. In the System Settings window that just opened, find your Terminal app (or VS Code).")
            print("2. Toggle it ON.")
            print("3. Run the script again!\n")
        else:
            print(f"Error: {res.stderr}")

if __name__ == "__main__":
    main()


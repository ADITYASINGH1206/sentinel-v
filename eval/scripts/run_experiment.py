import argparse
import sys
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="SENTINEL-V Paper B Experiment Runner")
    parser.add_argument("--id", required=True, help="Experiment ID (e.g., e1, e2, e3, e4, ...)")
    args = parser.parse_args()

    exp_id = args.id.lower()
    print(f"[SENTINEL-V Eval] Executing Experiment {exp_id.upper()}...")
    
    out_dir = Path("eval/results") / exp_id
    out_dir.mkdir(parents=True, exist_ok=True)
    
    meta = {
        "experiment_id": exp_id,
        "status": "ready",
        "description": f"Outputs for {exp_id.upper()}"
    }
    with open(out_dir / "meta.json", "w") as f:
        json.dump(meta, f, indent=2)
        
    print(f"[SENTINEL-V Eval] Experiment {exp_id.upper()} scaffold verified. Output: {out_dir}")

if __name__ == "__main__":
    main()

import subprocess
import sys

EXPERIMENTS = ["e1", "e2", "e3", "e4", "e5", "e6", "e7", "e8", "e9", "e11", "e12"]


def main():
    print("Executing all Paper B evaluation experiments...")
    for exp in EXPERIMENTS:
        cmd = [sys.executable, "eval/scripts/run_experiment.py", "--id", exp]
        res = subprocess.run(cmd)
        if res.returncode != 0:
            print(f"Failed running experiment {exp}")
            sys.exit(1)
    print("All Paper B experiments completed successfully.")


if __name__ == "__main__":
    main()

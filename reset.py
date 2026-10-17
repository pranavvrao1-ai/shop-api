import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
MAIN = ROOT / "main.py"


def git(*args):
    subprocess.run(["git", *args], check=True, cwd=ROOT)


def main():
    push = "--no-push" not in sys.argv
    if push:
        git("pull", "--ff-only")  # pick up any merged fix first
    data = MAIN.read_bytes()
    fixed = data.replace(b'"cost":', b'"price":').replace(b'["cost"]', b'["price"]')
    if fixed == data:
        print("Code already healthy, nothing to reset.")
        return
    MAIN.write_bytes(fixed)
    git("add", "main.py")
    git("commit", "-m", "Restore price key in product catalog", "main.py")
    if push:
        git("push")
    print("Working code restored.")


if __name__ == "__main__":
    main()
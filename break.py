import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
MAIN = ROOT / "main.py"


def git(*args):
    subprocess.run(["git", *args], check=True, cwd=ROOT)


def main():
    push = "--no-push" not in sys.argv
    data = MAIN.read_bytes()
    if b'"price":' not in data:
        print("Nothing to break: no \"price\" keys found (already broken?).")
        return
    if push:
        git("pull", "--ff-only")
        data = MAIN.read_bytes()
    # Only the dict keys have a colon after "price"; checkout's ["price"] does not.
    MAIN.write_bytes(data.replace(b'"price":', b'"cost":'))
    git("add", "main.py")
    git("commit", "-m", "Rename price to cost in product catalog", "main.py")
    if push:
        git("push")
    print("Bug committed. /checkout will now raise KeyError: 'price'.")


if __name__ == "__main__":
    main()
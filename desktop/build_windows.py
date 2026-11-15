"""Build the Windows app with PyInstaller installed in the active build venv."""
import argparse
from pathlib import Path
import subprocess
import sys

root = Path(__file__).parent.resolve()
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--dist", type=Path, default=root / "dist")
args = parser.parse_args()
dist = args.dist.resolve()
if (dist / "USAFE Connect").exists():
    raise SystemExit("Choose a new --dist folder to preserve the existing package.")
if not (root / "runtime/verified-files.json").is_file():
    raise SystemExit("Prepare the verified runtime first with prepare_runtime.py.")
subprocess.run([
    sys.executable, "-m", "PyInstaller", "--onedir", "--windowed", "--noupx",
    "--name", "USAFE Connect", "--icon", str(root / "assets/usafe.ico"),
    "--add-data", str(root / "runtime") + ":runtime", "--add-data", str(root / "assets") + ":assets",
    "--distpath", str(dist), "--workpath", str(root / "build"),
    "--specpath", str(root / "build"), str(root / "connect_app.py"),
], cwd=root, check=True)

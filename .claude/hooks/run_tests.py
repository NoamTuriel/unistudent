"""PostToolUse hook: re-run the test suite after a Python file under plugins/ is edited."""
import json
import os
import subprocess
import sys

data = json.load(sys.stdin)
path = (data.get("tool_input") or {}).get("file_path") or ""
root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
rel = os.path.relpath(path, root).replace(os.sep, "/") if path else ""

if not (rel.startswith("plugins/") and rel.endswith(".py")):
    sys.exit(0)

result = subprocess.run(
    [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-q"],
    cwd=root, capture_output=True, text=True,
)
if result.returncode != 0:
    sys.stderr.write("Tests failed after editing %s:\n%s%s" % (rel, result.stdout, result.stderr))
    sys.exit(2)

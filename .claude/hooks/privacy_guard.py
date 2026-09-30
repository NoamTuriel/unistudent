"""PreToolUse hook: block `git commit` / `git push` when the change carries personal info.

Scans the lines about to be committed (staged diff) or pushed (commits the remote lacks) for
emails, IP addresses and phone numbers, and the file list for .scratch/ and docs/review-* paths.
See "Privacy" in CLAUDE.md. Exit code 2 blocks the command and shows the reasons to Claude.
"""
import json
import os
import re
import subprocess
import sys

data = json.load(sys.stdin)
command = (data.get("tool_input") or {}).get("command") or ""
root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

pushing = re.search(r"\bgit\s+push\b", command)
committing = re.search(r"\bgit\s+commit\b", command)
if not (pushing or committing):
    sys.exit(0)


def git(*args):
    r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    return r.stdout if r.returncode == 0 else None


if pushing:
    base = git("rev-parse", "--abbrev-ref", "@{u}") and "@{u}" or "origin/main"
    diff = git("diff", "--unified=0", base + "..HEAD") or ""
    names = (git("diff", "--name-only", base + "..HEAD") or "").splitlines()
else:
    diff = git("diff", "--cached", "--unified=0") or ""
    names = (git("diff", "--cached", "--name-only") or "").splitlines()

SAFE_EMAIL = re.compile(r"(noreply|no-reply|@example\.(com|org)|@users\.noreply\.github\.com)", re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
IPV4 = re.compile(r"(?<![\d.])(?:(?:25[0-5]|2[0-4]\d|1?\d?\d)\.){3}(?:25[0-5]|2[0-4]\d|1?\d?\d)(?![\d.])")
SAFE_IP = {"127.0.0.1", "0.0.0.0", "255.255.255.255"}
PHONE = re.compile(r"(?<![\w.])(?:\+\d{1,3}[\s-]?)?\(?0?\d{1,3}\)?[\s-]\d{3}[\s-]?\d{4}(?![\w.])")

problems = []
for name in names:
    if name.startswith(".scratch/") or name.startswith("docs/review-"):
        problems.append("private path in the change: " + name)

current = ""
for line in diff.splitlines():
    if line.startswith("+++ "):
        current = line[6:] if line.startswith("+++ b/") else line[4:]
        continue
    if not line.startswith("+"):
        continue
    text = line[1:]
    for m in EMAIL.findall(text):
        if not SAFE_EMAIL.search(m):
            problems.append("%s: email %s" % (current, m))
    for m in IPV4.findall(text):
        if m not in SAFE_IP:
            problems.append("%s: IP address %s" % (current, m))
    for m in PHONE.findall(text):
        problems.append("%s: possible phone number %s" % (current, m.strip()))

if problems:
    sys.stderr.write(
        "Privacy guard blocked this command: the repo is public (see CLAUDE.md).\n"
        + "\n".join(sorted(set(problems))[:20])
        + "\nRemove it, or ask the user before proceeding.\n"
    )
    sys.exit(2)

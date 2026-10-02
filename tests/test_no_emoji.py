"""The hazard sign is the only emoji tracked in the repo (ADR 0009)."""
import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2705\u274C\u2713\u2714\u2728\u2B50\u2753\u2757]")
HISTORY = {"docs/spec/v1.md"}  # the first spec is kept as it was written


class NoEmoji(unittest.TestCase):
    def test_no_tracked_file_has_an_emoji_but_the_hazard_sign(self):
        try:
            files = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True).split("\n")
        except (OSError, subprocess.CalledProcessError):
            self.skipTest("not a git checkout")
        found = []
        for name in files:
            if not name or name in HISTORY or name.endswith((".png", ".svg", ".pdf")):
                continue
            try:
                text = (ROOT / name).read_text("utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            if EMOJI.search(text):
                found.append(name)
        self.assertEqual(found, [])


if __name__ == "__main__":
    unittest.main()

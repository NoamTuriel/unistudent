"""Skills are portable Agent Skills: valid frontmatter, and the shared conventions block kept identical."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "plugins" / "unistudent" / "scripts" / "unistudent" / "skills"
ALL = sorted(ROOT.glob("plugins/*/skills/*/SKILL.md")) + sorted(CORE.glob("*/SKILL.md"))
BLOCK = re.compile(r"<!-- conventions:.*?<!-- /conventions -->", re.S)


class Skills(unittest.TestCase):
    def test_every_skill_has_the_open_standard_frontmatter(self):
        self.assertGreaterEqual(len(ALL), 10)
        for skill in ALL:
            text = skill.read_text("utf-8")
            front = text.split("---")[1]
            name = re.search(r"(?m)^name:\s*\"?([^\"\n]+)", front).group(1).strip()
            description = re.search(r"(?m)^description:\s*(.+)$", front).group(1).strip().strip('"')
            self.assertRegex(name, r"^[a-z0-9-]{1,64}$", skill)
            self.assertEqual(name, skill.parent.name, skill)
            self.assertLessEqual(len(description), 1024, skill)

    def test_core_skills_share_one_conventions_block(self):
        blocks = {BLOCK.search(s.read_text("utf-8")).group(0) for s in CORE.glob("*/SKILL.md")}
        self.assertEqual(len(blocks), 1)

    def test_skills_name_no_client_specific_tools(self):
        for skill in ALL:
            text = BLOCK.sub("", skill.read_text("utf-8"))
            for word in ("AskUserQuestion", "Skill tool", "Glob for"):
                self.assertNotIn(word, text, skill)


if __name__ == "__main__":
    unittest.main()

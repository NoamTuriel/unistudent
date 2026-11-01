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


class TranscriptionAndGraphRules(unittest.TestCase):
    """Ticket 17: the student picks recordings by number before any run, and graphs go through the tool first."""
    SKILLS = CORE

    def test_course_recordings_shows_a_numbered_list_before_the_first_transcription(self):
        text = (self.SKILLS / "course-recordings" / "SKILL.md").read_text("utf-8")
        self.assertIn("numbered list", text)
        self.assertIn("full path", text)
        self.assertIn('"All" is not an answer', text)
        self.assertLess(text.index("numbered list"), text.index("recordings approve"))
        self.assertLess(text.index("recordings approve"), text.index("recordings transcribe"))
        self.assertIn("Sit back and relax", text)

    def test_setup_transcribes_nothing_and_asks_per_recording(self):
        text = (self.SKILLS / "course-setup" / "SKILL.md").read_text("utf-8")
        self.assertIn("ask me per recording", text)
        self.assertNotIn("recordings transcribe", text)

    def test_graph_instructions_name_the_mcp_tool_before_any_install_request(self):
        text = (CORE / "reference" / "study-pack.md").read_text("utf-8") if (CORE / "reference").exists() else \
            (CORE.parent / "reference" / "study-pack.md").read_text("utf-8")
        self.assertLess(text.index("MCP tool `graph` first"), text.index("how to add matplotlib"))
        self.assertIn("Never ask the student to install anything before the MCP tool has been tried", text)

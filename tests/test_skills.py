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

    RULES = (CORE.parent / "reference" / "study-pack.md").read_text("utf-8")

    def test_graph_instructions_name_the_mcp_tool_and_never_an_install(self):
        self.assertIn("MCP tool `graph` first", self.RULES)
        self.assertIn("The student is never told to install anything", self.RULES)
        self.assertLess(self.RULES.index("MCP tool `graph` first"), self.RULES.index("never told to install"))
        self.assertNotIn("pip install", self.RULES)
        self.assertIn("not a graph or a flow is a slide link plus one line in words", self.RULES)

    def test_the_roadmap_rule_holds_the_one_discovery_sentence(self):
        sentence = "UniStudent draws graphs and flowcharts on request"
        roadmap = self.RULES.split("## Roadmap page")[1].split("\n## ")[0]
        self.assertIn(sentence, roadmap)
        self.assertEqual(self.RULES.count(sentence), 1)
        for skill in ALL:
            self.assertNotIn(sentence, skill.read_text("utf-8"), skill)

    def test_no_skill_names_the_removed_picture_commands(self):
        for doc in ALL + [CORE.parent / "reference" / "study-pack.md"] + sorted((CORE.parent / "agents").glob("*.md")):
            text = doc.read_text("utf-8")
            for gone in ("us tools", "us draw", "tools status"):
                self.assertNotIn(gone, text, doc)

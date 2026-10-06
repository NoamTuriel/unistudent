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


class FormFollowsTheCourse(unittest.TestCase):
    """Ticket 26: a concept takes the form its source uses, recorded per topic as the unit's Presentation."""
    AGENTS = CORE.parent / "agents"

    def test_the_unit_writer_writes_the_presentation_section_with_the_kind_words(self):
        text = (self.AGENTS / "wiki-unit-writer.md").read_text("utf-8")
        self.assertIn("`## Presentation`", text)
        for kind in ("table", "steps", "flowchart", "graph", "picture", "circuit", "molecule", "3D model"):
            self.assertIn(f"`{kind}`", text)

    def test_the_rules_hold_the_form_sentence_and_the_checklist(self):
        concepts = TranscriptionAndGraphRules.RULES.split("## Concepts (walkthrough)")[1].split("\n## ")[0]
        self.assertIn("A concept is presented in the form its source uses", concepts)
        self.assertIn("coverage checklist", concepts)
        for part in ("what it is", "why it is so", "formula", "memory tip"):
            self.assertIn(part, concepts.lower())

    def test_the_pack_writer_opens_the_page_the_presentation_line_names(self):
        text = (self.AGENTS / "study-pack-writer.md").read_text("utf-8")
        self.assertIn("Presentation", text)
        self.assertIn("copy its form", text)


class UnattendedBuild(unittest.TestCase):
    """Ticket 28: a build the student starts and walks away from: it never asks, and it resumes."""
    SKILL = (CORE / "study-pack" / "SKILL.md").read_text("utf-8")

    def test_no_step_asks_the_student_during_a_build(self):
        build = self.SKILL[self.SKILL.index("## 3."):self.SKILL.index("## 7.")]
        writer = (CORE.parent / "agents" / "study-pack-writer.md").read_text("utf-8")
        for text in (build, writer):
            self.assertIsNone(re.search(r"(?i)\bask|interview|\bconfirm", text))

    def test_the_skill_names_the_resume_rules(self):
        for rule in ("pages_present", "only when the request named it", "one line", "lessons_without_roadmap",
                     "us wiki build"):
            self.assertIn(rule, self.SKILL)
        self.assertLess(self.SKILL.index("lessons_without_roadmap"), self.SKILL.index("study-pack-writer"))

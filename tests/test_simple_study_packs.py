"""Ticket 18: `us check` keeps Study packs simple, and the rules say so."""
import re
import unittest
from pathlib import Path

from helpers import CourseTestCase, folders, run_json, write

ROOT = Path(__file__).resolve().parents[1]
GENERIC = ROOT / "plugins" / "unistudent" / "scripts" / "unistudent" / "reference" / "study-pack.md"
ECONOMICS = ROOT / "plugins" / "economics" / "skills" / "economics" / "SKILL.md"
MACRO = ROOT / "plugins" / "economics" / "skills" / "macro" / "SKILL.md"

TOPIC = "## Topic 1\n\n### Money — כסף\n\n✅ Money is 1/r.\n\n"


class PackShape(CourseTestCase):
    def setUp(self):
        super().setUp()
        self.course = self.tmp / "Macro"
        own = self.tmp / "own"
        write(own / "Unit 4" / "slides.txt", "money multiplier")
        run_json("setup", self.course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")
        self.pack = folders(self.course).study / "Unit 4"
        self.slides = next(folders(self.course).material.rglob("slides*"))

    def kinds(self, name, text):
        write(self.pack / name, text)
        return [p["kind"] for p in run_json("check", self.pack / name, "--course", self.course)["problems"]]

    def test_a_topic_with_its_closing_lines_passes(self):
        closing = f"In the lectures: [lecture 3, 00:12:47]({self.slides.as_uri()}#t=767)\n\nFrom: [slides]({self.slides.as_uri()})\n"
        self.assertEqual(self.kinds("4.2 Walkthrough.md", TOPIC + closing), [])

    def test_a_topic_without_a_from_line_fails(self):
        self.assertIn("topic-missing-from-line", self.kinds("4.2 Walkthrough.md", TOPIC))

    def test_a_missing_file_or_a_link_into_the_hidden_folder_still_fails(self):
        gone = self.slides.with_name("gone.pdf").as_uri()
        self.assertIn("broken-link", self.kinds("4.2 Walkthrough.md", TOPIC + f"From: [x]({gone})\n"))
        hidden = (folders(self.course).wiki / "index.md").as_uri()
        self.assertIn("link-into-hidden", self.kinds("4.2 Walkthrough.md", TOPIC + f"From: [x]({hidden})\n"))

    def test_a_practice_page_with_stages_tags_or_graphs_fails(self):
        self.assertEqual(self.kinds("4.3 Practice.md", f"| Topic | Questions |\n\n## Money\n\n- [Q1]({self.slides.as_uri()}): the multiplier\n"), [])
        self.assertIn("practice-stage", self.kinds("4.3 Practice.md", "## Stage 1\n\n- Q1\n"))
        self.assertIn("practice-tag", self.kinds("4.3 Practice.md", "## Money\n\n- Q1 #unit-04/t01-money\n"))
        self.assertIn("practice-graph", self.kinds("4.3 Practice.md", "![curve](graphs/a.png)\n"))

    def test_a_separate_short_practice_page_fails(self):
        self.assertIn("short-practice-page", self.kinds("4.3b Short practice.md", "- Q1\n"))


class Rules(unittest.TestCase):
    def test_generic_rules_bend_to_the_subject_and_close_each_topic(self):
        text = GENERIC.read_text("utf-8")
        for needle in ("In the lectures", "From:", "How to answer", "Short version", "a part with nothing to say is not written"):
            self.assertIn(needle, text)
        self.assertNotRegex(text, r"3b|practice-short|Practice stages")

    def test_economics_skills_follow_the_same_rules(self):
        economics, macro = ECONOMICS.read_text("utf-8"), MACRO.read_text("utf-8")
        self.assertNotRegex(economics, r"(?i)always these five parts")
        self.assertIn("How to answer", economics)
        self.assertNotRegex(macro, r"3b|practice-short")
        self.assertNotIn("Accepted reasoning", macro)


if __name__ == "__main__":
    unittest.main()

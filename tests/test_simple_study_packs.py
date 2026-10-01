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

    def test_sources_folded_into_a_callout_pass_and_a_pack_needs_no_labels(self):
        text = "## נושא\n\n### כסף — Money\n\nהכסף הוא מה שמקובל לשלם בו.\n\n> [!note]- מקורות\n> בהרצאות: [שיעור 3, 00:12:47](" + self.slides.as_uri() + "#t=767)\n>\n> מתוך: [השקפים](" + self.slides.as_uri() + ")\n"
        write(self.pack / "4.2 Walkthrough.md", text)
        self.assertEqual(run_json("check", self.pack / "4.2 Walkthrough.md", "--labels", "--course", self.course)["problems"], [])

    def test_a_wikilink_to_a_numbered_page_resolves(self):
        write(self.pack / "4.3 Practice.md", "- [x](" + self.slides.as_uri() + ")\n")
        write(self.pack / "4.1 Roadmap.md", "## Start\n\n1. [[4.3 Practice]]\n2. [[4.9 Missing]]\n")
        problems = run_json("check", self.pack / "4.1 Roadmap.md", "--course", self.course)["problems"]
        self.assertEqual([p["link"] for p in problems if p["kind"] == "broken-link"], ["[[4.9 Missing]]"])

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


class Labels(PackShape):
    def test_closing_lines_and_practice_notes_need_no_label(self):
        write(self.pack / "4.2 Walkthrough.md", TOPIC + "In the lectures: lecture three recording at twelve minutes\n\nFrom: slides.pdf, the multiplier chapter\n")
        write(self.pack / "4.3 Practice.md", f"- [Q3]({self.slides.as_uri()}): applying the multiplier to a bank deposit\n")
        for name in ("4.2 Walkthrough.md", "4.3 Practice.md"):
            result = run_json("check", self.pack / name, "--labels", "--course", self.course)
            self.assertNotIn("unlabeled", [p["kind"] for p in result["problems"]], name)


class Rules(unittest.TestCase):
    def test_generic_rules_bend_to_the_subject_and_close_each_topic(self):
        text = GENERIC.read_text("utf-8")
        for needle in ("In the recordings", "From:", "How to answer", "Short version", "a part with nothing to say is not written", "folded", "no grounding labels"):
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

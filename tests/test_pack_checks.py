"""Ticket 30: `us check` finds what code can check in a Study pack: notation, quotes, the writer's return."""
import unittest
from pathlib import Path

from helpers import CourseTestCase, folders, run_json, write

UNIT_PAGE = ("\n## Notation\n\n- Y: output\n- $Y_d$: disposable income\n- C: consumption. Sources: [slides](../sources/unit-04/solutions.md#page-7)\n"
             "\n## Assumptions\n\n1. Prices are fixed.\n2. No foreign trade.\n")
SOLUTION = "Answer: income rises,\nso consumption rises too (assumption 1)."


class PackAgainstTheUnit(CourseTestCase):
    def setUp(self):
        super().setUp()
        own = self.tmp / "own"
        write(own / "Unit 4" / "solutions.txt", SOLUTION)

    def make(self, language):
        self.course = self.tmp / language
        run_json("setup", self.course, "--name", "Macro", "--language", language,
                 "--import", self.tmp / "own", "--tier", "official")
        run_json("wiki", "build", "--course", self.course)
        unit_page = folders(self.course).wiki / "units" / "unit-04.md"
        unit_page.write_text(unit_page.read_text("utf-8") + UNIT_PAGE, "utf-8")
        return folders(self.course).study

    def problems(self, page, text, language="en"):
        pack = self.make(language) / ("Unit 4" if language == "en" else "יחידה 4")
        write(pack / page, text)
        return [(p["kind"], p.get("text")) for p in run_json("check", pack, "--course", self.course)["problems"]]

    def test_a_symbol_missing_from_the_notation_is_a_notation_problem(self):
        self.assertEqual(self.problems("4.2 Walkthrough.md", "Spending is $Y = C + Z$ (assumption 2).\n"),
                         [("notation", "Z")])

    def test_latex_commands_and_braced_subscripts_are_not_symbols(self):
        page = "$\\Delta Y = \\frac{1}{1-C} \\cdot Y_{d}$, $\\text{GDP}$, $Y \\to Z$\n"
        self.assertEqual(self.problems("4.2 Walkthrough.md", page), [("notation", "Z")])

    def test_an_assumption_number_the_unit_page_does_not_list_is_a_notation_problem(self):
        self.assertEqual(self.problems("4.2 Walkthrough.md", "By assumption 7, $Y = C$.\n"),
                         [("notation", "assumption 7")])

    def test_assumption_words_without_a_numbered_reference_are_not_checked(self):
        self.assertEqual(self.problems("4.2 Walkthrough.md", "Under these assumptions, in 2008 $Y = C$.\n"), [])

    def test_an_obsidian_sources_callout_closes_a_topic(self):
        page = "## Topic\n\n### Sub\n\nText.\n\n> [!note]- Sources\n> - **From:** the slides\n"
        self.assertEqual(self.problems("4.2 Walkthrough.md", page), [])

    def test_in_a_hebrew_pack_a_concept_headings_english_name_and_the_roadmap_are_not_checked(self):
        self.assertEqual(self.problems("4.2 Walkthrough.md", "### מכפיל — Rate of interest\n\nבהנחה ש-Y עולה.\n", "he"), [])
        pack = folders(self.course).study / "יחידה 4"
        write(pack / "מפת הקלטות.md", "## Zoom lesson.mp4\n\n- IS-LM\n")
        self.assertEqual([p["kind"] for p in run_json("check", pack, "--course", self.course)["problems"]], [])

    def test_in_a_hebrew_pack_a_latin_symbol_in_the_prose_is_checked(self):
        self.assertEqual(self.problems("4.2 Walkthrough.md", "כאשר Y עולה גם C עולה, ו-MPC קבוע.\n", "he"),
                         [("notation", "MPC")])

    def test_a_say_it_quote_found_in_the_source_passes_however_it_is_wrapped(self):
        block = '**How to answer**\n\n- **Model answer:** "Income rises, so consumption rises too."\n'
        self.assertEqual(self.problems("4.2 Walkthrough.md", block), [])

    def test_a_say_it_quote_absent_from_the_source_is_a_quote_problem(self):
        block = ('- **Model answer:** "income rises"\n- **Say it:** "prices never move",\n  "so consumption rises"\n'
                 '- **Prove it:** "not checked here"\n')
        self.assertEqual(self.problems("4.2 Walkthrough.md", block), [("quote", "prices never move")])

    def test_a_hebrew_say_it_label_is_found_too(self):
        own = self.tmp / "own" / "Unit 4" / "solutions.txt"
        own.write_text("התשובה: ההכנסה עולה.", "utf-8")
        self.assertEqual(self.problems("4.2 Walkthrough.md", '- **ככה אומרים:** "ההכנסה עולה", "המחירים יורדים"\n', "he"),
                         [("quote", "המחירים יורדים")])


class WriterReturn(CourseTestCase):
    def setUp(self):
        super().setUp()
        self.course = self.tmp / "Macro"
        write(self.tmp / "own" / "Unit 4" / "slides.txt", "money")
        run_json("setup", self.course, "--name", "Macro", "--language", "en", "--import", self.tmp / "own",
                 "--tier", "official")
        self.pack = folders(self.course).study / "Unit 4"
        write(self.pack / "4.1 Roadmap.md", "# Roadmap\n")

    def problems(self, text):
        write(self.course / ".unistudent" / "writer-returns" / "Unit 4.md", text)
        return [(p["kind"], p.get("text")) for p in run_json("check", self.pack, "--course", self.course)["problems"]]

    def test_page_list_then_known_gaps_passes(self):
        self.assertEqual(self.problems("- 4.1 Roadmap: the unit at a glance\n- 4.2 Walkthrough: five topics\n\n"
                                       "Known gaps:\n- picture · 4.2 Walkthrough · flowchart: the cause chain on slide 12\n"
                                       "- question · 4.3 Practice · question 7 has no solution in the material\n"), [])
        self.assertEqual(self.problems("- 4.1 Roadmap: the unit\nKnown gaps: none\n"), [])

    def test_a_malformed_return_is_a_return_problem(self):
        self.assertEqual(self.problems("I wrote the pack. Notes: the graph was hard.\n"),
                         [("return", "no `Known gaps:` line")])
        self.assertEqual(self.problems("- 4.1 Roadmap: the unit\nKnown gaps:\n- the graph was hard\n"),
                         [("return", "- the graph was hard")])


class WriterInstructions(unittest.TestCase):
    def test_the_writer_returns_pages_then_known_gaps_with_picture_kinds(self):
        agents = Path(__file__).resolve().parents[1] / "plugins" / "unistudent" / "scripts" / "unistudent" / "agents"
        writer = (agents / "study-pack-writer.md").read_text("utf-8")
        for words in ("Known gaps:", "<kind> · <page> · <what's missing>", "`picture`", "Presentation kind word"):
            self.assertIn(words, writer)


if __name__ == "__main__":
    unittest.main()

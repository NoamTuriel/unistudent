"""Seam 3: answers and pages → every unmarked paragraph cites, warnings need no source, citations resolve.

The model's answers themselves are produced by the eval runner (evals/grounding);
these tests pin down the grader it uses, against hand-written answers.
"""
import json
import unittest

from helpers import CourseTestCase, can_read_pdfs, make_pdf, run, run_json, write

GOOD = """## The money multiplier

The money multiplier is 1/r, where r is the reserve ratio.
Sources: [slides p.1](.unistudent/wiki/sources/unit-04/slides.md#page-1)

- A higher reserve ratio lowers the multiplier. Sources: [slides p.2](.unistudent/wiki/sources/unit-04/slides.md#page-2)

| r | multiplier |
|---|---|
| 0.1 | 10 |

[Recording](.unistudent/wiki/index.md)
"""


class GroundingRule(CourseTestCase):
    def setUp(self):
        super().setUp()
        own = self.tmp / "own"
        make_pdf(own / "Unit 4" / "slides.pdf", ["Money multiplier is 1 over r", "Higher r lowers it"])
        self.course = self.tmp / "Macro"
        run("setup", self.course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")
        run_json("wiki", "build", "--course", self.course)

    def check(self, text):
        answer = write(self.course / "answer.md", text)
        return run_json("check", "--course", self.course, answer, "--labels")

    def kinds(self, text):
        return sorted(p["kind"] for p in self.check(text)["problems"])

    def test_a_well_grounded_answer_has_no_problems(self):
        if not can_read_pdfs():
            self.skipTest("no PDF tool installed (pdftotext or pypdf)")
        report = self.check(GOOD)
        self.assertEqual(report["problems"], [])
        self.assertEqual([p["warning"] for p in report["paragraphs"]], [False])

    def test_unmarked_prose_needs_a_citation_that_resolves(self):
        self.assertEqual(self.kinds("The multiplier is 1/r.\n"), ["no-citation"])
        self.assertEqual(self.kinds("The multiplier is 1/r. Sources: [s](.unistudent/wiki/sources/unit-04/nope.md)\n"),
                         ["broken-link"])
        self.assertEqual(self.kinds("The multiplier is 1/r. Sources: [s](.unistudent/wiki/sources/unit-04/slides.md#page-9)\n"),
                         ["broken-anchor"])

    def test_a_sources_block_and_an_introduced_list_belong_to_the_paragraph_before(self):
        if not can_read_pdfs():
            self.skipTest("no PDF tool installed (pdftotext or pypdf)")
        text = ("The course solves this in five steps:\n1. Change in reserves.\n2. Excess reserves.\n\n"
                "Sources: [slides](.unistudent/wiki/sources/unit-04/slides.md#page-1)\n")
        self.assertEqual(self.kinds(text), [])

    def test_a_list_right_after_a_cited_paragraph_shares_its_citation(self):
        if not can_read_pdfs():
            self.skipTest("no PDF tool installed (pdftotext or pypdf)")
        text = ("The course teaches five steps. Sources: [s](.unistudent/wiki/sources/unit-04/slides.md#page-1)\n\n"
                "1. Change in reserves.\n2. Excess reserves.\n")
        self.assertEqual(self.kinds(text), [])

    def test_a_follow_on_paragraph_without_a_source_is_flagged(self):
        if not can_read_pdfs():
            self.skipTest("no PDF tool installed (pdftotext or pypdf)")
        text = ("In this course the multiplier is 1/r. Sources: [s](.unistudent/wiki/sources/unit-04/slides.md#page-1)\n\n"
                "Outside this course the textbook formula includes the currency ratio.\n")
        self.assertEqual(self.kinds(text), ["no-citation"])

    def test_a_closing_inbox_suggestion_needs_no_source(self):
        text = ("⚠️ Not from your course material (general knowledge): the IS-LM model.\n\n"
                "If you have notes on it, drop them into `1-inbox/` and run `/unistudent:course-add`.\n")
        self.assertEqual(self.kinds(text), [])

    def test_my_own_explanation_of_course_material_is_unmarked_and_cites_what_it_explains(self):
        if not can_read_pdfs():
            self.skipTest("no PDF tool installed (pdftotext or pypdf)")
        text = ("Think of a piggy bank that lends out most of each coin: every loan comes back as a new "
                "deposit. Sources: [slides](.unistudent/wiki/sources/unit-04/slides.md#page-1)\n")
        self.assertEqual(self.check(text)["problems"], [])
        self.assertEqual(self.kinds("Think of a piggy bank that lends out most of each coin it receives.\n"),
                         ["no-citation"])

    def test_a_warning_paragraph_needs_no_source(self):
        text = ("⚠️ Not from your course material (general knowledge): this is how the IS-LM model works.\n\n"
                "⚠️ לא מתוך חומר הקורס (ידע כללי): כך עובד מודל ה-IS-LM בספרי לימוד.\n")
        report = self.check(text)
        self.assertEqual(report["problems"], [])
        self.assertTrue(all(p["warning"] for p in report["paragraphs"]))

    def test_a_leftover_old_label_neither_passes_nor_fails_a_paragraph_by_itself(self):
        cited = "\u2705 The multiplier is 1/r. Sources: [s](.unistudent/wiki/sources/unit-04/slides.md#page-1)\n"
        if can_read_pdfs():
            self.assertEqual(self.kinds(cited), [])
        self.assertEqual(self.kinds("\u2705 The multiplier is 1/r and nothing else.\n"), ["no-citation"])

    def test_grading_a_case(self):
        if not can_read_pdfs():
            self.skipTest("no PDF tool installed (pdftotext or pypdf)")
        case = {"id": "multiplier", "question": "What is the money multiplier?",
                "must_not_warn": True,
                "must_cite": ["sources/unit-04/slides.md"]}
        case_file = write(self.tmp / "case.json", json.dumps(case))
        good = write(self.course / "good.md", GOOD)
        self.assertTrue(run_json("eval-grade", "--course", self.course, case_file, good)["passed"])

        bad = write(self.course / "bad.md", "⚠️ Not from your course material (general knowledge): it is 1/(r+c).\n")
        result = run_json("eval-grade", "--course", self.course, case_file, bad)
        self.assertFalse(result["passed"])
        self.assertEqual(sorted(result["failures"]),
                         ["forbidden warning", "missing citation sources/unit-04/slides.md"])

    def test_cross_course_case_requires_naming_the_other_course(self):
        case = {"id": "other-course", "must_warn": True, "must_mention": ["other course"]}
        case_file = write(self.tmp / "case.json", json.dumps(case))
        ok = write(self.course / "ok.md", "⚠️ Not from this course (from your other course, Micro): elasticity is a measure of response.\n")
        vague = write(self.course / "vague.md", "⚠️ Not from your course material (general knowledge): elasticity is a measure of response.\n")
        self.assertTrue(run_json("eval-grade", "--course", self.course, case_file, ok)["passed"])
        self.assertFalse(run_json("eval-grade", "--course", self.course, case_file, vague)["passed"])


if __name__ == "__main__":
    unittest.main()

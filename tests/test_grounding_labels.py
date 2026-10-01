"""Seam 3: answers and pages → correct grounding labels and valid citations.

The model's answers themselves are produced by the eval runner (evals/grounding);
these tests pin down the grader it uses, against hand-written answers.
"""
import json
import unittest

from helpers import CourseTestCase, can_read_pdfs, make_pdf, run, run_json, write

GOOD = """## The money multiplier

✅ The money multiplier is 1/r, where r is the reserve ratio.
Sources: [slides p.1](.unistudent/wiki/sources/unit-04/slides.md#page-1)

- ✅ A higher reserve ratio lowers the multiplier. Sources: [slides p.2](.unistudent/wiki/sources/unit-04/slides.md#page-2)

| r | multiplier |
|---|---|
| 0.1 | 10 |

🎬 [Recording](.unistudent/wiki/index.md)
"""


class GroundingLabels(CourseTestCase):
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
        self.assertEqual([p["label"] for p in report["paragraphs"]], ["✅", "✅"])

    def test_every_paragraph_needs_exactly_one_label(self):
        self.assertEqual(self.kinds("The multiplier is 1/r.\n"), ["unlabeled"])
        self.assertEqual(self.kinds("✅ ⚠️ The multiplier is 1/r. Sources: [s](.unistudent/wiki/index.md)\n"), ["several-labels"])

    def test_course_material_labels_need_a_citation_that_resolves(self):
        self.assertEqual(self.kinds("✅ The multiplier is 1/r.\n"), ["no-citation"])
        self.assertEqual(self.kinds("✅ The multiplier is 1/r. Sources: [s](.unistudent/wiki/sources/unit-04/nope.md)\n"),
                         ["broken-link"])
        self.assertEqual(self.kinds("✅ The multiplier is 1/r. Sources: [s](.unistudent/wiki/sources/unit-04/slides.md#page-9)\n"),
                         ["broken-anchor"])

    def test_a_sources_block_and_an_introduced_list_belong_to_the_paragraph_before(self):
        if not can_read_pdfs():
            self.skipTest("no PDF tool installed (pdftotext or pypdf)")
        text = ("✅ The course solves this in five steps:\n1. Change in reserves.\n2. Excess reserves.\n\n"
                "Sources: [slides](.unistudent/wiki/sources/unit-04/slides.md#page-1)\n")
        self.assertEqual(self.kinds(text), [])

    def test_a_list_right_after_a_labelled_paragraph_shares_its_label(self):
        if not can_read_pdfs():
            self.skipTest("no PDF tool installed (pdftotext or pypdf)")
        text = ("✅ The course teaches five steps. Sources: [s](.unistudent/wiki/sources/unit-04/slides.md#page-1)\n\n"
                "1. Change in reserves.\n2. Excess reserves.\n")
        self.assertEqual(self.kinds(text), [])

    def test_a_follow_on_paragraph_without_a_label_is_flagged(self):
        if not can_read_pdfs():
            self.skipTest("no PDF tool installed (pdftotext or pypdf)")
        text = ("❌ In this course the multiplier is 1/r. Sources: [s](.unistudent/wiki/sources/unit-04/slides.md#page-1)\n\n"
                "Outside this course the textbook formula includes the currency ratio.\n")
        self.assertEqual(self.kinds(text), ["unlabeled"])

    def test_a_closing_inbox_suggestion_needs_no_label(self):
        text = ("⚠️ The course material doesn't cover the IS-LM model.\n\n"
                "If you have notes on it, drop them into `inbox/` and run `/unistudent:course-add`.\n")
        self.assertEqual(self.kinds(text), [])

    def test_my_own_explanation_of_course_material_is_its_own_label_and_cites_what_it_explains(self):
        if not can_read_pdfs():
            self.skipTest("no PDF tool installed (pdftotext or pypdf)")
        text = ("💡 Think of a piggy bank that lends out most of each coin: every loan comes back as a new "
                "deposit. Sources: [slides](.unistudent/wiki/sources/unit-04/slides.md#page-1)\n")
        report = self.check(text)
        self.assertEqual(report["problems"], [])
        self.assertEqual([p["label"] for p in report["paragraphs"]], ["💡"])
        self.assertEqual(self.kinds("💡 Think of a piggy bank that lends out most of each coin it receives.\n"),
                         ["no-citation"])

    def test_outside_and_conflict_labels_need_no_citation(self):
        if not can_read_pdfs():
            self.skipTest("no PDF tool installed (pdftotext or pypdf)")
        text = ("⚠️ The course material doesn't cover the IS-LM model; this is general knowledge.\n\n"
                "❌ In this course the multiplier is 1/r. Sources: [s](.unistudent/wiki/sources/unit-04/slides.md#page-1) "
                "Textbooks often add a currency-drain term.\n")
        self.assertEqual(self.kinds(text), [])

    def test_grading_a_case(self):
        if not can_read_pdfs():
            self.skipTest("no PDF tool installed (pdftotext or pypdf)")
        case = {"id": "multiplier", "question": "What is the money multiplier?",
                "must_include_labels": ["✅"], "must_not_include_labels": ["⚠️"],
                "must_cite": ["sources/unit-04/slides.md"]}
        case_file = write(self.tmp / "case.json", json.dumps(case))
        good = write(self.course / "good.md", GOOD)
        self.assertTrue(run_json("eval-grade", "--course", self.course, case_file, good)["passed"])

        bad = write(self.course / "bad.md", "⚠️ Generally it is 1/(r+c).\n")
        result = run_json("eval-grade", "--course", self.course, case_file, bad)
        self.assertFalse(result["passed"])
        self.assertEqual(sorted(result["failures"]),
                         ["forbidden label ⚠️", "missing citation sources/unit-04/slides.md", "missing label ✅"])

    def test_cross_course_case_requires_naming_the_other_course(self):
        case = {"id": "other-course", "must_include_labels": ["⚠️"], "must_mention": ["other course"]}
        case_file = write(self.tmp / "case.json", json.dumps(case))
        ok = write(self.course / "ok.md", "⚠️ From your other course (Micro), not this one: elasticity is ...\n")
        vague = write(self.course / "vague.md", "⚠️ Elasticity is ...\n")
        self.assertTrue(run_json("eval-grade", "--course", self.course, case_file, ok)["passed"])
        self.assertFalse(run_json("eval-grade", "--course", self.course, case_file, vague)["passed"])


if __name__ == "__main__":
    unittest.main()

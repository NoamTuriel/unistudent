"""The Before-the-test page: merge the indexers' rows, build the page, and `us check` reads its links."""
import json
import shutil
import unittest

from helpers import CourseTestCase, folders, make_pdf, run_json, write


def row(exam, q, sol, **kw):
    return {"exam": exam, "part": "A", "q": q, "qpages": [q + 1], "solpages": sol, "unit": 4, "topic": "multiplier",
            "skill": "compute the multiplier", "style": "calc", "points": 5, "confidence": "high", **kw}


class BeforeTest(CourseTestCase):
    def setUp(self):
        super().setUp()
        self.course = self.tmp / "Macro"
        own = self.tmp / "own"
        make_pdf(own / "Unit 4" / "exam one.pdf", ["intro", "q1", "sol1", "q2", "sol2"])
        make_pdf(own / "Unit 4" / "exam two.pdf", ["intro", "q1"])
        run_json("setup", self.course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")
        scratch = self.course / ".unistudent" / "before-test"
        write(scratch / "a.json", json.dumps([row("exam one", 1, [3]), row("exam one", 3, [4])]))
        write(scratch / "b.json", json.dumps([row("exam two", 1, [])]))
        self.scratch = scratch

    def build(self, fmt):
        merged = run_json("before-test", "merge", self.scratch / "a.json", self.scratch / "b.json", "--course", self.course)
        self.assertIn("Merged 3", merged["summary"])
        write(self.scratch / "clusters.json", json.dumps([{"unit": 4, "title": "Multiplier", "hint": "master it", "ids": [1, 0]}]))
        return run_json("before-test", "build", "--format", fmt, "--course", self.course)

    def test_markdown_page_orders_clusters_hides_and_passes_check(self):
        result = self.build("obsidian")
        page = folders(self.course).study / "Before the test.md"
        text = page.read_text("utf-8")
        self.assertIn("> [!example]- Multiplier (2)", text)
        self.assertLess(text.index("exam one, Question 3"), text.index("exam one, Question 1"))  # cluster order kept
        self.assertIn("exam two, Question 1", text)  # unclustered rows are not dropped
        self.assertIn("no solution in the files", text)
        self.assertIn("includes the handwritten answer", text)  # answer on the question's own page
        self.assertEqual(run_json("check", page, "--course", self.course)["problems"], [])
        if shutil.which("pdfseparate"):
            self.assertTrue((folders(self.course).study / "Before the test - Question pages" / "exam one - 2.pdf").exists())
        else:
            self.assertFalse(result["single_page_copies"])

    def test_html_page_links_are_checked(self):
        self.build("html")
        page = folders(self.course).study / "Before the test.html"
        self.assertIn('href="file://', page.read_text("utf-8"))
        self.assertEqual(run_json("check", page, "--course", self.course)["problems"], [])
        page.write_text(page.read_text("utf-8") + '<a href="file:///nope/missing.pdf">x</a>', "utf-8")
        self.assertIn("broken-link", [p["kind"] for p in run_json("check", page, "--course", self.course)["problems"]])

    def test_a_row_missing_a_field_is_refused(self):
        write(self.scratch / "bad.json", json.dumps([{"exam": "exam one"}]))
        with self.assertRaises(Exception):
            run_json("before-test", "merge", self.scratch / "bad.json", "--course", self.course)


if __name__ == "__main__":
    unittest.main()

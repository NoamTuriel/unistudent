"""Generated university fallback (ticket 01): interview once, reuse the cached file after that."""
import unittest

from helpers import CourseTestCase, run, run_json


class UniversityFallback(CourseTestCase):
    def test_no_generated_fallback_yet(self):
        status = run_json("university", "status", "--university", "Bar-Ilan")
        self.assertFalse(status["generated"])
        self.assertIsNone(status["content"])

    def test_a_confirmed_interview_writes_a_reference_file(self):
        saved = run_json("university", "save", "--university", "Bar-Ilan",
                         "--url", "https://biu.example/moodle",
                         "--organizing", "Everything", "by", "week", "in", "one", "folder.")
        content = (self.home / "generated" / "bar-ilan" / "site.md").read_text("utf-8")
        self.assertEqual(saved["path"], str(self.home / "generated" / "bar-ilan" / "site.md"))
        self.assertIn("biu.example/moodle", content)
        self.assertIn("Everything by week", content)
        # Never holds study-pack rules: only site access and organization notes.
        self.assertNotIn("study pack", content.lower())

    def test_a_second_run_reuses_the_generated_file_with_no_re_interview(self):
        run_json("university", "save", "--university", "Bar-Ilan",
                 "--url", "https://biu.example/moodle", "--organizing", "By week.")
        status = run_json("university", "status", "--university", "Bar-Ilan")
        self.assertTrue(status["generated"])
        self.assertIn("biu.example/moodle", status["content"])

    def test_reuse_survives_spelling_case_and_spacing_drift(self):
        run_json("university", "save", "--university", "Bar-Ilan",
                 "--url", "https://biu.example/moodle", "--organizing", "By week.")
        status = run_json("university", "status", "--university", "bar ilan")
        self.assertTrue(status["generated"])

    def test_save_needs_both_url_and_organizing(self):
        code, out = run("university", "save", "--university", "Bar-Ilan", "--json")
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()

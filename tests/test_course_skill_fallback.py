"""Generated course/subject fallback (ticket 02): reuses ticket 01's interview-generate-persist mechanism."""
import unittest

from helpers import CourseTestCase, run, run_json


class CourseSkillFallback(CourseTestCase):
    def test_no_generated_fallback_yet(self):
        status = run_json("course-skill", "status", "--field", "biology", "--course-name", "Genetics 101")
        self.assertFalse(status["generated"])
        self.assertIsNone(status["content"])

    def test_a_confirmed_interview_writes_a_rules_file(self):
        saved = run_json("course-skill", "save", "--field", "biology", "--course-name", "Genetics 101",
                         "--emphasis", "Punnett", "squares", "and", "pedigree", "charts",
                         "--summarize", "Short", "bullet", "points", "per", "topic.")
        content = (self.home / "generated" / "biology" / "genetics-101.md").read_text("utf-8")
        self.assertEqual(saved["path"], str(self.home / "generated" / "biology" / "genetics-101.md"))
        self.assertIn("Punnett squares", content)
        self.assertIn("Short bullet points", content)
        # Never holds university/site-access notes: only study-pack content.
        self.assertNotIn("moodle", content.lower())
        self.assertNotIn("http", content.lower())

    def test_a_second_build_reuses_the_generated_file_with_no_re_interview(self):
        run_json("course-skill", "save", "--field", "biology", "--course-name", "Genetics 101",
                 "--emphasis", "Punnett squares.", "--summarize", "Short bullets.")
        status = run_json("course-skill", "status", "--field", "biology", "--course-name", "Genetics 101")
        self.assertTrue(status["generated"])
        self.assertIn("Punnett squares", status["content"])

    def test_save_needs_both_emphasis_and_summarize(self):
        code, out = run("course-skill", "save", "--field", "biology", "--course-name", "Genetics 101", "--json")
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()

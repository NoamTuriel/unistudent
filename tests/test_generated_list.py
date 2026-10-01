"""`us generated list` (ticket 09): see every saved university and course fallback."""
import unittest

from helpers import CourseTestCase, run_json


class GeneratedList(CourseTestCase):
    def test_nothing_generated_is_an_empty_list(self):
        self.assertEqual(run_json("generated")["generated"], [])

    def test_one_of_each_kind_both_appear(self):
        run_json("university", "save", "--university", "Bar-Ilan", "--url", "https://biu.example", "--organizing", "By week.")
        run_json("course-skill", "save", "--field", "biology", "--course-name", "Cells",
                 "--emphasis", "Diagrams.", "--summarize", "Briefly.")
        entries = run_json("generated")["generated"]
        self.assertEqual(sorted(e["kind"] for e in entries), ["course", "university"])
        self.assertTrue(all(e["path"] and e["preview"] for e in entries))


if __name__ == "__main__":
    unittest.main()

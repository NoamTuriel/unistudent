"""`us generated list` (ticket 09): see every saved university fallback."""
import unittest
from pathlib import Path

from helpers import CourseTestCase, run_json


class GeneratedList(CourseTestCase):
    def test_nothing_generated_is_an_empty_list(self):
        self.assertEqual(run_json("generated")["generated"], [])

    def test_universities_only_and_old_course_rules_are_left_out(self):
        saved = run_json("university", "save", "--university", "Bar-Ilan", "--url", "https://biu.example", "--organizing", "By week.")
        old_course_rules = Path(saved["path"]).parents[1] / "biology" / "cells.md"  # written before ADR 0011
        old_course_rules.parent.mkdir(parents=True)
        old_course_rules.write_text("# biology — Cells: generated study-pack rules\n", "utf-8")
        entries = run_json("generated")["generated"]
        self.assertEqual([e["kind"] for e in entries], ["university"])
        self.assertTrue(all(e["path"] and e["preview"] for e in entries))


if __name__ == "__main__":
    unittest.main()

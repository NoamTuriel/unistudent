"""Coverage (ticket 13): the Wiki says which files it read, which it couldn't, and which were skipped."""
import unittest
from unittest import mock

from helpers import CourseTestCase, run, run_json, write
from unistudent.convert import Conversion


class Coverage(CourseTestCase):
    def setUp(self):
        super().setUp()
        own = self.tmp / "own"
        write(own / "Unit 1" / "notes.txt", "The multiplier is 1/(1-c) and it is used in every chapter of this course.")
        write(own / "Unit 1" / "broken.txt", "x")
        write(own / "Unit 1" / "diagram.png")
        write(own / "Unit 1" / "lecture 1.mp4", b"\x00" * 64)
        write(own / "Unit 1" / "data.xyz")
        self.course = self.tmp / "Macro"
        run("setup", self.course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")

    def coverage(self):
        result = run_json("wiki", "coverage", "--course", self.course)
        return {r["path"]: r for r in result["files"]}, result

    def build_with_one_unreadable_file(self):
        real = __import__("unistudent.wiki", fromlist=["convert"]).convert

        def convert(path):
            if path.name == "broken.txt":
                return Conversion([], "none", ["could not be opened"])
            return real(path)

        with mock.patch("unistudent.wiki.convert", convert):
            return run_json("wiki", "build", "--course", self.course)

    def test_every_file_is_analyzed_failed_skipped_or_pending(self):
        self.build_with_one_unreadable_file()
        files, result = self.coverage()
        self.assertEqual(files["Unit 1/notes.txt"]["status"], "analyzed")
        self.assertEqual(files["Unit 1/broken.txt"]["status"], "failed")
        self.assertIn("could not be opened", files["Unit 1/broken.txt"]["why"])
        self.assertEqual(files["Unit 1/diagram.png"]["status"], "skipped")
        self.assertEqual(files["Unit 1/data.xyz"]["status"], "skipped")
        self.assertEqual(files["Unit 1/lecture 1.mp4"]["status"], "pending")
        self.assertEqual(sum(result["counts"].values()), len(files))

    def test_before_a_build_documents_are_pending(self):
        files, _ = self.coverage()
        self.assertEqual(files["Unit 1/notes.txt"]["status"], "pending")

    def test_a_recording_the_student_chose_not_to_process_is_skipped_with_that_reason(self):
        run_json("context", "--course", self.course, "--recording-level", "1")
        files, _ = self.coverage()
        self.assertEqual(files["Unit 1/lecture 1.mp4"]["status"], "skipped")
        self.assertIn("you chose", files["Unit 1/lecture 1.mp4"]["why"])

    def test_the_wiki_gets_a_coverage_page_that_passes_the_check_and_warns_the_ai(self):
        self.build_with_one_unreadable_file()
        page = (self.course / "wiki" / "coverage.md").read_text("utf-8")
        self.assertIn("## Failed (1)", page)
        self.assertIn("NOT in the Wiki", page)
        self.assertIn("coverage.md", (self.course / "wiki" / "index.md").read_text("utf-8"))
        self.assertEqual(run_json("wiki", "check", "--course", self.course)["problems"], [])

    def test_the_build_summary_carries_the_coverage_counts(self):
        result = self.build_with_one_unreadable_file()
        self.assertEqual(result["coverage"]["failed"], 1)
        self.assertIn("1 failed", result["summary"])


if __name__ == "__main__":
    unittest.main()

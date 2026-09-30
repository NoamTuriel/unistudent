"""Seam 1 (core side): the inbox, and working with several course folders."""
import os
import unittest

from helpers import CourseTestCase, make_pdf, run, run_json, write


class Inbox(CourseTestCase):
    def setUp(self):
        super().setUp()
        self.course = self.tmp / "Macro"
        run("setup", self.course, "--name", "Macro", "--language", "en")

    def test_inbox_files_move_into_raw_once_with_origin_and_tier(self):
        make_pdf(self.course / "inbox" / "Unit 3 friend summary.pdf", ["Unit 3 summary"])
        write(self.course / "inbox" / "photo of notes.jpg", b"\xff\xd8jpeg")
        result = run_json("add", "--course", self.course)

        self.assertEqual(sorted(result["added"]), ["inbox/Unit 3 friend summary.pdf", "inbox/photo of notes.jpg"])
        self.assertEqual(list((self.course / "inbox").iterdir()), [])
        files = run_json("manifest", "--course", self.course)["files"]
        entry = files["inbox/Unit 3 friend summary.pdf"]
        self.assertEqual((entry["origin"], entry["tier"], entry["unit"]), ("inbox", "added", 3))
        self.assertTrue((self.course / "raw" / "inbox" / "Unit 3 friend summary.pdf").is_file())
        self.assertTrue((self.course / "materials" / "Unit 3" / "Unit 3 friend summary.pdf").exists())
        self.assertEqual(result["unsorted"], ["inbox/photo of notes.jpg"])
        # The Wiki is updated in the same step.
        self.assertTrue((self.course / "wiki" / "sources" / "unit-03" / "Unit 3 friend summary.md").exists())

    def test_files_can_be_marked_official(self):
        make_pdf(self.course / "inbox" / "lecturer notes unit 2.pdf", ["Unit 2"])
        run_json("add", "--course", self.course, "--official", "lecturer notes unit 2.pdf")
        entry = run_json("manifest", "--course", self.course)["files"]["inbox/lecturer notes unit 2.pdf"]
        self.assertEqual(entry["tier"], "official")

    def test_same_name_twice_keeps_both(self):
        make_pdf(self.course / "inbox" / "summary.pdf", ["first"])
        run_json("add", "--course", self.course)
        make_pdf(self.course / "inbox" / "summary.pdf", ["second version"])
        result = run_json("add", "--course", self.course)
        self.assertEqual(result["added"], ["inbox/summary (2).pdf"])
        self.assertEqual(len(run_json("manifest", "--course", self.course)["files"]), 2)

    def test_empty_inbox_says_so(self):
        result = run_json("add", "--course", self.course)
        self.assertEqual(result["added"], [])


class SeveralCourses(CourseTestCase):
    def test_list_switch_and_detect_the_current_course(self):
        macro = self.tmp / "Macro"
        stats = self.tmp / "Statistics"
        run("setup", macro, "--name", "Macro")
        run("setup", stats, "--name", "Statistics")

        names = [c["name"] for c in run_json("courses", "list")["courses"]]
        self.assertEqual(names, ["Macro", "Statistics"])
        self.assertEqual(run_json("courses", "current")["name"], "Statistics")  # last set up is active

        run_json("courses", "switch", "Macro")
        self.assertEqual(run_json("courses", "current")["name"], "Macro")

        # Inside a course folder, the folder wins over the Registry.
        cwd = os.getcwd()
        os.chdir(stats / "wiki")
        try:
            self.assertEqual(run_json("courses", "current")["name"], "Statistics")
        finally:
            os.chdir(cwd)

    def test_current_says_how_the_course_was_found_and_lists_the_others(self):
        run("setup", self.tmp / "Macro", "--name", "Macro")
        run("setup", self.tmp / "Statistics", "--name", "Statistics")
        current = run_json("courses", "current")
        self.assertEqual((current["name"], current["found_by"]), ("Statistics", "last active"))
        self.assertEqual(sorted(c["name"] for c in current["courses"]), ["Macro", "Statistics"])
        self.assertIn("ask", current["summary"])  # outside a folder: the request decides, else ask
        cwd = os.getcwd()
        os.chdir(self.tmp / "Macro")
        try:
            inside = run_json("courses", "current")
        finally:
            os.chdir(cwd)
        self.assertEqual((inside["name"], inside["found_by"]), ("Macro", "course folder"))

    def test_each_course_has_its_own_wiki_and_manifest(self):
        macro = self.tmp / "Macro"
        stats = self.tmp / "Statistics"
        run("setup", macro, "--name", "Macro", "--language", "en")
        run("setup", stats, "--name", "Statistics", "--language", "en")
        make_pdf(macro / "inbox" / "Unit 1 macro.pdf", ["Macro unit 1"])
        run_json("add", "--course", macro)
        self.assertEqual(run_json("manifest", "--course", stats)["files"], {})
        self.assertFalse(list((stats / "wiki").rglob("Unit 1 macro.md")))

    def test_unknown_course_is_an_error(self):
        run("setup", self.tmp / "Macro", "--name", "Macro")
        code, out = run("courses", "switch", "Physics")
        self.assertEqual(code, 1)
        self.assertIn("No course named Physics", out)


if __name__ == "__main__":
    unittest.main()

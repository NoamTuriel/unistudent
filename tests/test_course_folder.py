"""Seam 1 (core side): a student's own folder → course folder with Raw, Manifest and readable layout."""
import json
import os
import unittest
from pathlib import Path

from helpers import CourseTestCase, run, run_json, write


class CourseFromOwnFolder(CourseTestCase):
    def make_own_folder(self):
        own = self.tmp / "own"
        write(own / "יחידה 1 - מבוא" / "שאלות עם תשובות.pdf", b"%PDF unit1")
        write(own / "שקפים" / "שיעור 2 - יחידה 2.pdf", b"%PDF unit2")
        write(own / "מבחנים לדוגמא" / "מבחן 2024.pdf", b"%PDF exam")
        write(own / "הקלטות" / "01 - מפגש מספר 1.mp4", b"\x00" * 2048)
        return own

    def test_setup_creates_course_folder_and_registers_it(self):
        own = self.make_own_folder()
        course = self.tmp / "Macro"
        code, out = run("setup", course, "--name", "מבוא למקרו-כלכלה", "--import", own, "--tier", "official")
        self.assertEqual(code, 0, out)

        settings = json.loads((course / ".unistudent" / "settings.json").read_text("utf-8"))
        self.assertEqual(settings["course_name"], "מבוא למקרו-כלכלה")
        registry = run_json("courses", "list")
        self.assertEqual([c["path"] for c in registry["courses"]], [str(course.resolve())])
        self.assertTrue((course / "CLAUDE.md").exists())
        self.assertTrue((course / "README.md").exists())
        self.assertTrue((course / "inbox").is_dir())

    def test_every_imported_file_is_in_manifest_once_and_never_copied(self):
        own = self.make_own_folder()
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--import", own, "--tier", "official")

        manifest = run_json("manifest", "--course", course)
        entries = manifest["files"]
        self.assertEqual(len(entries), 4)
        for rel, entry in entries.items():
            self.assertEqual(entry["origin"], "student-folder")
            self.assertEqual(entry["tier"], "official")
            original = Path(entry["source_path"])
            self.assertTrue(original.exists())
            # Raw points at the original: same file on disk, no second copy.
            self.assertTrue(os.path.samefile(course / "raw" / rel, original))
            self.assertTrue((course / "raw" / rel).is_symlink())

    def test_files_with_clear_unit_evidence_are_sorted_and_the_rest_are_unsorted(self):
        own = self.make_own_folder()
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--import", own, "--tier", "official")

        unit1 = course / "materials" / "Unit 1" / "שאלות עם תשובות.pdf"
        unit2 = course / "materials" / "Unit 2" / "שיעור 2 - יחידה 2.pdf"
        self.assertTrue(os.path.samefile(unit1, own / "יחידה 1 - מבוא" / "שאלות עם תשובות.pdf"))
        self.assertTrue(os.path.samefile(unit2, own / "שקפים" / "שיעור 2 - יחידה 2.pdf"))

        unsorted = run_json("unsorted", "--course", course)["files"]
        self.assertEqual(sorted(unsorted), sorted(["מבחנים לדוגמא/מבחן 2024.pdf", "הקלטות/01 - מפגש מספר 1.mp4"]))

    def test_answers_to_the_unsorted_question_are_applied_and_remembered(self):
        own = self.make_own_folder()
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--import", own, "--tier", "official")

        code, out = run("assign", "--course", course, "מבחנים לדוגמא/מבחן 2024.pdf", "general")
        self.assertEqual(code, 0, out)
        code, out = run("assign", "--course", course, "הקלטות/01 - מפגש מספר 1.mp4", "1")
        self.assertEqual(code, 0, out)

        self.assertEqual(run_json("unsorted", "--course", course)["files"], [])
        self.assertTrue((course / "materials" / "General" / "מבחן 2024.pdf").exists())
        self.assertTrue((course / "materials" / "Unit 1" / "01 - מפגש מספר 1.mp4").exists())

        # Re-importing never asks again.
        run("import", "--course", course, own, "--tier", "official")
        self.assertEqual(run_json("unsorted", "--course", course)["files"], [])

    def test_setup_is_idempotent(self):
        own = self.make_own_folder()
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--import", own, "--tier", "official")
        first = run_json("manifest", "--course", course)
        code, out = run("setup", course, "--name", "Macro", "--import", own, "--tier", "official")
        self.assertEqual(code, 0, out)
        self.assertEqual(run_json("manifest", "--course", course), first)
        self.assertEqual(len(run_json("courses", "list")["courses"]), 1)

    def test_index_page_fallback_when_links_cannot_be_made(self):
        own = self.make_own_folder()
        course = self.tmp / "Macro"
        os.environ["UNISTUDENT_LINK_MODE"] = "index"
        try:
            run("setup", course, "--name", "Macro", "--import", own, "--tier", "official")
        finally:
            del os.environ["UNISTUDENT_LINK_MODE"]
        index = (course / "materials" / "Unit 1" / "INDEX.md").read_text("utf-8")
        self.assertIn("שאלות עם תשובות.pdf", index)
        self.assertFalse((course / "materials" / "Unit 1" / "שאלות עם תשובות.pdf").exists())
        # Manifest still knows every file.
        self.assertEqual(len(run_json("manifest", "--course", course)["files"]), 4)


if __name__ == "__main__":
    unittest.main()

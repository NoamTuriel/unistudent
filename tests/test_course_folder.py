"""Seam 1 (core side): a student's own folder → course folder with the Material folder and Manifest."""
import json
import unittest

from helpers import CourseTestCase, folders, run, run_json, write


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
        self.assertTrue(folders(course).inbox.is_dir())

    def test_a_course_folder_with_retired_settings_still_loads(self):
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--language", "en")
        path = course / ".unistudent" / "settings.json"
        settings = json.loads(path.read_text("utf-8"))
        settings.update({"origin_mode": "site", "lecturer": "x", "recording_segments": [], "sort_patterns": []})
        path.write_text(json.dumps(settings), "utf-8")

        run_json("import", self.make_own_folder(), "--course", course)
        units = {rel: e["unit"] for rel, e in run_json("manifest", "--course", course)["files"].items()}
        self.assertEqual(units["added/Unit 1/שאלות עם תשובות.pdf"], 1)
        self.assertEqual(units["added/Unit 2/שיעור 2 - יחידה 2.pdf"], 2)

    def test_every_imported_file_is_in_the_manifest_once_and_copied_not_moved(self):
        own = self.make_own_folder()
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")

        entries = run_json("manifest", "--course", course)["files"]
        self.assertEqual(len(entries), 4)
        material = folders(course).material
        for rel, entry in entries.items():
            self.assertEqual(entry["origin"], "student-folder")
            self.assertEqual(entry["tier"], "official")
            self.assertTrue((material / rel).is_file())
            self.assertFalse((material / rel).is_symlink())
        self.assertEqual(len(list((own).rglob("*.*"))), 4)  # the originals are all still there

    def test_files_with_clear_unit_evidence_are_sorted_and_the_rest_are_unsorted(self):
        own = self.make_own_folder()
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")

        material = folders(course).material / "official"
        self.assertTrue((material / "Unit 1" / "שאלות עם תשובות.pdf").is_file())
        self.assertTrue((material / "Unit 2" / "שיעור 2 - יחידה 2.pdf").is_file())

        unsorted = run_json("unsorted", "--course", course)["files"]
        self.assertEqual(sorted(unsorted), sorted(["official/Unsorted/מבחן 2024.pdf", "official/Unsorted/01 - מפגש מספר 1.mp4"]))

    def test_answers_to_the_unsorted_question_are_applied_and_remembered(self):
        own = self.make_own_folder()
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")

        code, out = run("assign", "--course", course, "official/Unsorted/מבחן 2024.pdf", "general")
        self.assertEqual(code, 0, out)
        code, out = run("assign", "--course", course, "official/Unsorted/01 - מפגש מספר 1.mp4", "1")
        self.assertEqual(code, 0, out)

        self.assertEqual(run_json("unsorted", "--course", course)["files"], [])
        material = folders(course).material / "official"
        self.assertTrue((material / "General" / "מבחן 2024.pdf").exists())
        self.assertTrue((material / "Unit 1" / "01 - מפגש מספר 1.mp4").exists())

        # Re-importing never asks again, and never copies a file twice.
        again = run_json("import", "--course", course, own, "--tier", "official")
        self.assertEqual((again["imported"], again["unsorted"]), ([], []))

    def test_setup_is_idempotent(self):
        own = self.make_own_folder()
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")
        first = run_json("manifest", "--course", course)
        code, out = run("setup", course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")
        self.assertEqual(code, 0, out)
        self.assertEqual(run_json("manifest", "--course", course), first)
        self.assertEqual(len(run_json("courses", "list")["courses"]), 1)


if __name__ == "__main__":
    unittest.main()

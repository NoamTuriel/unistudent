"""Student preferences (course folder, seam 1) and study-pack change detection (Wiki, seam 2)."""
import unittest

from helpers import CourseTestCase, folders, make_pdf, run, run_json, write


class Preferences(CourseTestCase):
    def test_course_and_general_preferences_are_separate_files_and_course_comes_last(self):
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro")
        run_json("prefs", "add", "--course", course, "--scope", "course", "--text", "Walkthroughs: max 3 bullets per concept")
        run_json("prefs", "add", "--course", course, "--scope", "general", "--text", "Explain things simpler")

        self.assertIn("max 3 bullets", (course / "course-preferences.md").read_text("utf-8"))
        self.assertIn("Explain things simpler", (self.home / "general-preferences.md").read_text("utf-8"))
        shown = run_json("prefs", "show", "--course", course)
        # Order = precedence: later wins.
        self.assertEqual([p["scope"] for p in shown["files"]], ["general", "course"])
        self.assertIn("simpler", shown["files"][0]["content"])

    def test_general_preferences_reach_every_course(self):
        run("setup", self.tmp / "Macro", "--name", "Macro")
        run("setup", self.tmp / "Stats", "--name", "Stats")
        run_json("prefs", "add", "--course", self.tmp / "Macro", "--scope", "general", "--text", "Hebrew terms with English in brackets")
        shown = run_json("prefs", "show", "--course", self.tmp / "Stats")
        self.assertIn("English in brackets", shown["files"][0]["content"])


class StudyPackChanges(CourseTestCase):
    def test_new_material_for_a_unit_with_a_study_pack_is_reported(self):
        own = self.tmp / "own"
        make_pdf(own / "Unit 4" / "slides.pdf", ["multiplier"])
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")
        run_json("wiki", "build", "--course", course)
        run_json("study", "mark-built", "--course", course, "--unit", "4")
        self.assertEqual(run_json("study", "changes", "--course", course, "--unit", "4")["new"], [])

        make_pdf(folders(course).inbox / "Unit 4 extra questions.pdf", ["more questions"])
        run_json("add", "--course", course)
        changes = run_json("study", "changes", "--course", course, "--unit", "4")
        self.assertEqual(changes["new"], ["sources/unit-04/Unit 4 extra questions.md"])
        self.assertEqual(changes["changed"], [])
        # Other units are not affected.
        self.assertEqual(run_json("study", "changes", "--course", course, "--unit", "5")["new"], [])

    def test_a_unit_without_a_study_pack_has_no_baseline(self):
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro")
        self.assertFalse(run_json("study", "changes", "--course", course, "--unit", "1")["has_study_pack"])

    def test_a_partial_pack_reports_the_pages_present_and_asking_creates_no_study_vault(self):
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--language", "en")
        vault = folders(course).study
        self.assertEqual(run_json("study", "changes", "--course", course, "--unit", "4")["pages_present"], [])
        self.assertFalse(vault.exists())
        write(vault / "Unit 4" / "4.1 Roadmap.md", "# Roadmap\n")
        write(vault / "Unit 4" / "4.3 Practice.md", "# Practice\n")
        write(vault / "Unit 4" / "Recordings roadmap.md", "# Recordings roadmap\n")
        write(vault / "Unit 5" / "5.2 Walkthrough.md", "# Walkthrough\n")
        self.assertEqual(run_json("study", "changes", "--course", course, "--unit", "4")["pages_present"],
                         ["roadmap", "practice"])


if __name__ == "__main__":
    unittest.main()

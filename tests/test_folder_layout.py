"""Seam 1 and 2: the three visible folders, the hidden folder, location-is-truth, and the move from the old layout."""
import json
import os
import shutil
import unittest
from pathlib import Path

from helpers import CourseTestCase, folders, make_pdf, mock_env, run, run_json, write

OLD_NAMES = {"raw", "materials", "wiki", "study", "inbox"}


def top_level(course):
    return sorted(p.name for p in Path(course).iterdir() if p.is_dir())


class VisibleFolders(CourseTestCase):
    def test_setup_in_english_makes_exactly_three_numbered_folders_and_a_hidden_one(self):
        course = self.tmp / "Macro"
        run_json("setup", course, "--name", "Macro", "--language", "en")
        self.assertEqual(top_level(course), [".unistudent", "1-inbox", "2-course-material", "3-Macro-study-from-here"])
        self.assertFalse(OLD_NAMES & set(top_level(course)))
        self.assertTrue((course / "README.md").exists())

    def test_setup_in_hebrew_names_every_folder_in_hebrew_with_the_course_name_in_the_vault(self):
        course = self.tmp / "Macro"
        run_json("setup", course, "--name", "מקרו", "--language", "he")
        self.assertEqual(top_level(course), [".unistudent", "1-קבצים-חדשים", "2-חומרי-הקורס", "3-מקרו-ללמוד-מכאן"])
        write(course / "1-קבצים-חדשים" / "Unit 3 notes.txt", "money")
        run_json("add", "--course", course)
        self.assertTrue((course / "2-חומרי-הקורס" / "נוסף" / "יחידה 3" / "Unit 3 notes.txt").is_file())

    def test_the_closing_suggestion_to_use_the_hebrew_inbox_needs_no_label(self):
        course = self.tmp / "Macro"
        run_json("setup", course, "--name", "Macro", "--language", "he")
        page = write(course / "answer.md", "⚠️ The course material doesn't cover it.\n\nDrop notes into `1-קבצים-חדשים/` and run course-add.\n")
        self.assertEqual(run_json("check", page, "--labels", "--course", course)["problems"], [])

    def test_a_language_with_no_table_falls_back_to_english_names(self):
        course = self.tmp / "Macro"
        run_json("setup", course, "--name", "Macro", "--language", "fr")
        self.assertEqual(top_level(course), [".unistudent", "1-inbox", "2-course-material", "3-Macro-study-from-here"])

    def test_the_wiki_and_everything_else_live_in_the_hidden_folder(self):
        course = self.tmp / "Macro"
        run_json("setup", course, "--name", "Macro", "--language", "en")
        write(course / "1-inbox" / "Unit 1 notes.txt", "money text")
        run_json("add", "--course", course)
        hidden = course / ".unistudent"
        for name in ("settings.json", "manifest.json", "wiki"):
            self.assertTrue((hidden / name).exists(), name)
        self.assertTrue((hidden / "wiki" / "sources" / "unit-01" / "Unit 1 notes.md").exists())
        self.assertEqual(top_level(course), [".unistudent", "1-inbox", "2-course-material", "3-Macro-study-from-here"])

    def test_setup_tells_the_student_where_the_three_folders_are(self):
        result = run_json("setup", self.tmp / "Macro", "--name", "Macro", "--language", "en")
        self.assertEqual((result["inbox"], result["material"], result["study"]),
                         ("1-inbox", "2-course-material", "3-Macro-study-from-here"))

    def test_the_students_readme_names_the_real_folders(self):
        course = self.tmp / "Macro"
        run_json("setup", course, "--name", "Macro", "--language", "en")
        text = (course / "README.md").read_text("utf-8")
        for name in ("1-inbox", "2-course-material", "3-Macro-study-from-here"):
            self.assertIn(name, text)
        self.assertNotIn("raw/", text)
        self.assertIn(".unistudent/wiki", (course / "AGENTS.md").read_text("utf-8"))


class MaterialFolder(CourseTestCase):
    def setUp(self):
        super().setUp()
        self.course = self.tmp / "Macro"
        run_json("setup", self.course, "--name", "Macro", "--language", "en")
        self.f = folders(self.course)
        self.m = self.f.material

    def manifest(self):
        return run_json("manifest", "--course", self.course)["files"]

    def test_inbox_files_are_moved_into_added_by_unit_and_the_inbox_is_empty(self):
        make_pdf(self.f.inbox / "Unit 3 friend summary.pdf", ["Unit 3 summary"])
        write(self.f.inbox / "photo.jpg", b"\xff\xd8jpeg")
        result = run_json("add", "--course", self.course)
        self.assertTrue((self.m / "added" / "Unit 3" / "Unit 3 friend summary.pdf").is_file())
        self.assertTrue((self.m / "added" / "Unsorted" / "photo.jpg").is_file())
        self.assertEqual(list(self.f.inbox.iterdir()), [])
        self.assertEqual(result["unsorted"], ["added/Unsorted/photo.jpg"])
        self.assertEqual(self.manifest()["added/Unit 3/Unit 3 friend summary.pdf"]["origin"], "inbox")

    def test_official_files_go_to_the_official_folder(self):
        write(self.f.inbox / "lecturer unit 2.txt", "x unit 2")
        run_json("add", "--course", self.course, "--official", "lecturer unit 2.txt")
        self.assertTrue((self.m / "official" / "Unit 2" / "lecturer unit 2.txt").is_file())

    def test_an_own_folder_is_copied_and_the_originals_are_left_alone(self):
        own = self.tmp / "own"
        write(own / "Unit 1 - intro" / "slides.txt", "slides text")
        run_json("import", own, "--course", self.course, "--tier", "official")
        self.assertEqual((own / "Unit 1 - intro" / "slides.txt").read_text("utf-8"), "slides text")
        copy = self.m / "official" / "Unit 1" / "slides.txt"
        self.assertEqual(copy.read_text("utf-8"), "slides text")
        self.assertFalse(copy.is_symlink())
        self.assertFalse(os.path.samefile(copy, own / "Unit 1 - intro" / "slides.txt"))
        again = run_json("import", own, "--course", self.course, "--tier", "official")
        self.assertEqual(again["imported"], [])  # copied once

    def test_nothing_in_the_course_folder_is_a_link(self):
        own = self.tmp / "own"
        write(own / "Unit 1" / "a.txt", "a")
        run_json("import", own, "--course", self.course)
        for dirpath, dirs, files in os.walk(self.course):
            for name in dirs + files:
                self.assertFalse((Path(dirpath) / name).is_symlink(), name)

    def test_moving_a_file_between_official_and_added_changes_its_trust_after_a_build(self):
        write(self.f.inbox / "Unit 4 notes.txt", "money multiplier")
        run_json("add", "--course", self.course)
        self.assertEqual(self.manifest()["added/Unit 4/Unit 4 notes.txt"]["tier"], "added")
        (self.m / "official" / "Unit 4").mkdir(parents=True)
        shutil.move(str(self.m / "added" / "Unit 4" / "Unit 4 notes.txt"), str(self.m / "official" / "Unit 4" / "Unit 4 notes.txt"))
        run_json("wiki", "build", "--course", self.course)
        files = self.manifest()
        self.assertEqual(list(files), ["official/Unit 4/Unit 4 notes.txt"])
        self.assertEqual(files["official/Unit 4/Unit 4 notes.txt"]["tier"], "official")
        self.assertEqual(files["official/Unit 4/Unit 4 notes.txt"]["origin"], "inbox")  # origin survives the move
        page = (self.f.wiki / "sources" / "unit-04" / "Unit 4 notes.md").read_text("utf-8")
        self.assertIn("tier: official", page)
        self.assertIn("source: official/Unit 4/Unit 4 notes.txt", page)

    def test_a_renamed_file_is_followed_by_its_fingerprint_and_keeps_where_it_came_from(self):
        write(self.f.inbox / "Unit 4 notes.txt", "money multiplier")
        run_json("add", "--course", self.course, "--describe", "Unit 4 notes.txt=friend's summary")
        old = self.m / "added" / "Unit 4" / "Unit 4 notes.txt"
        old.rename(old.with_name("my renamed notes.txt"))
        run_json("wiki", "build", "--course", self.course)
        entry = self.manifest()["added/Unit 4/my renamed notes.txt"]
        self.assertEqual(entry["origin_note"], "friend's summary")
        self.assertFalse((self.f.wiki / "sources" / "unit-04" / "Unit 4 notes.md").exists())
        self.assertTrue((self.f.wiki / "sources" / "unit-04" / "my renamed notes.md").exists())

    def test_moving_a_file_to_another_unit_moves_its_wiki_page_too(self):
        write(self.f.inbox / "Unit 4 notes.txt", "money multiplier")
        run_json("add", "--course", self.course)
        (self.m / "added" / "Unit 5").mkdir()
        shutil.move(str(self.m / "added" / "Unit 4" / "Unit 4 notes.txt"), str(self.m / "added" / "Unit 5" / "Unit 4 notes.txt"))
        run_json("wiki", "build", "--course", self.course)
        self.assertEqual(self.manifest()["added/Unit 5/Unit 4 notes.txt"]["unit"], 5)
        self.assertTrue((self.f.wiki / "sources" / "unit-05" / "Unit 4 notes.md").exists())
        self.assertFalse((self.f.wiki / "sources" / "unit-04" / "Unit 4 notes.md").exists())

    def test_deleting_a_file_removes_it_from_the_manifest_and_the_wiki(self):
        write(self.f.inbox / "Unit 4 notes.txt", "money multiplier")
        run_json("add", "--course", self.course)
        (self.m / "added" / "Unit 4" / "Unit 4 notes.txt").unlink()
        run_json("wiki", "build", "--course", self.course)
        self.assertEqual(self.manifest(), {})
        self.assertFalse((self.f.wiki / "sources" / "unit-04" / "Unit 4 notes.md").exists())

    def test_a_file_the_student_drops_straight_into_the_material_folder_is_added_and_sorted(self):
        write(self.m / "Unit 2 extra.txt", "elasticity")
        write(self.m / "mystery.txt", "no clue")
        run_json("wiki", "build", "--course", self.course)
        files = self.manifest()
        self.assertEqual(files["added/Unit 2/Unit 2 extra.txt"]["tier"], "added")
        self.assertEqual(files["added/Unit 2/Unit 2 extra.txt"]["origin"], "material-folder")
        self.assertIn("added/Unsorted/mystery.txt", run_json("unsorted", "--course", self.course)["files"])
        self.assertTrue((self.m / "added" / "Unit 2" / "Unit 2 extra.txt").is_file())

    def test_assign_moves_the_file_into_its_unit_folder(self):
        write(self.f.inbox / "photo.txt", "words")
        run_json("add", "--course", self.course)
        run_json("assign", "added/Unsorted/photo.txt", "general", "--course", self.course)
        self.assertTrue((self.m / "added" / "General" / "photo.txt").is_file())
        self.assertEqual(run_json("unsorted", "--course", self.course)["files"], [])


class RecordingRoadmap(CourseTestCase):
    def test_a_roadmap_per_unit_appears_in_the_study_vault(self):
        course = self.tmp / "Macro"
        own = self.tmp / "own"
        write(own / "Unit 4" / "session 5.mp4", b"\x00" * 4096)
        run_json("setup", course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")
        f = folders(course)
        with mock_env(UNISTUDENT_STT_BACKEND="fake"):
            run_json("recordings", "transcribe", "--course", course, "official/Unit 4/session 5.mp4")
        rec = f.wiki / "recordings" / "session 5"
        write(rec / "toc.md", "| 00:12:47 | exam question | [00:12:47](transcript.md#001230) |\n")
        write(rec / "summary.md", "Sources: [transcript](transcript.md)\n\n## Announcements\n\nHomework due Sunday.\n")
        run_json("wiki", "build", "--course", course)
        roadmap = (f.study / "Unit 4" / "Recordings roadmap.md").read_text("utf-8")
        self.assertIn("Homework due Sunday.", roadmap)
        self.assertIn("00:12:47", roadmap)
        self.assertIn("2-course-material/official/Unit 4/session 5.mp4", roadmap)
        self.assertEqual(run_json("check", f.study / "Unit 4", "--labels", "--course", course)["problems"], [])
        self.assertEqual(sorted(p.name for p in f.study.iterdir()), ["Unit 4"])


def make_old_course(root, own):
    """A course folder as versions before 0.4 made it: raw (a link and a real file), materials, wiki, study."""
    write(own / "Unit 4" / "slides.txt", "money multiplier")
    write(root / "raw" / "inbox" / "notes.txt", "my own notes")
    (root / "raw" / "Unit 4").mkdir(parents=True, exist_ok=True)
    try:
        os.symlink(own / "Unit 4" / "slides.txt", root / "raw" / "Unit 4" / "slides.txt")
    except OSError:  # no symlinks here (Windows without rights): a real file does as well
        shutil.copy(own / "Unit 4" / "slides.txt", root / "raw" / "Unit 4" / "slides.txt")
    state = root / ".unistudent"
    write(state / "settings.json", json.dumps({"course_name": "Old", "language": "en"}))
    entry = {"origin": "student-folder", "tier": "official", "unit": 4, "fingerprint": "x", "size": 1,
             "source_path": str(own / "Unit 4" / "slides.txt")}
    write(state / "manifest.json", json.dumps({"files": {
        "Unit 4/slides.txt": entry,
        "inbox/notes.txt": {**entry, "origin": "inbox", "tier": "added", "unit": None, "source_path": "x"}}}))
    write(state / "wiki.json", json.dumps({"Unit 4/slides.txt": {"page": "sources/unit-04/slides.md", "fingerprint": "x"}}))
    write(state / "materials.json", json.dumps(["Unit 4/slides.txt"]))
    write(root / "materials" / "Unit 4" / "slides.txt", "link stand-in")
    write(root / "wiki" / "index.md", "# Wiki\n")
    write(root / "wiki" / "sources" / "unit-04" / "slides.md", "---\nsource: Unit 4/slides.txt\n---\n# slides\n")
    write(root / "study" / "Unit 4" / "4.1 Roadmap.md", "✅ x. Sources: [s](../../wiki/sources/unit-04/slides.md)\n")


class OldLayout(CourseTestCase):
    def setUp(self):
        super().setUp()
        self.course = self.tmp / "Old"
        make_old_course(self.course, self.tmp / "own")

    def test_an_old_layout_folder_still_builds_its_wiki_where_it_always_was(self):
        result = run_json("wiki", "build", "--course", self.course)
        self.assertEqual(result["pages"], 2)
        self.assertTrue((self.course / "wiki" / "sources" / "unit-04" / "slides.md").exists())
        self.assertFalse((self.course / ".unistudent" / "wiki").exists())

    def test_adding_to_an_old_layout_folder_says_to_migrate_first(self):
        code, out = run("add", "--course", self.course)
        self.assertEqual(code, 1)
        self.assertIn("migrate", out)

    def test_migrate_lists_every_move_first_and_changes_nothing_without_apply(self):
        result = run_json("migrate", "--course", self.course)
        self.assertFalse(result["applied"])
        self.assertTrue((self.course / "raw").exists())
        text = " ".join(f"{m['from']}>{m['to']}" for m in result["moves"])
        self.assertIn("official/Unit 4/slides.txt", text)
        self.assertIn("added/Unsorted/notes.txt", text)

    def test_migrate_produces_the_new_layout_and_keeps_the_work(self):
        run_json("migrate", "--course", self.course, "--apply")
        self.assertEqual(top_level(self.course), [".unistudent", "1-inbox", "2-course-material", "3-Old-study-from-here"])
        f = folders(self.course)
        self.assertEqual((f.material / "official" / "Unit 4" / "slides.txt").read_text("utf-8"), "money multiplier")
        self.assertEqual((f.material / "added" / "Unsorted" / "notes.txt").read_text("utf-8"), "my own notes")
        self.assertTrue((f.wiki / "index.md").exists())
        pack = (f.study / "Unit 4" / "4.1 Roadmap.md").read_text("utf-8")
        self.assertIn("../../.unistudent/wiki/sources/unit-04/slides.md", pack)
        self.assertIn("source: official/Unit 4/slides.txt", (f.wiki / "sources" / "unit-04" / "slides.md").read_text("utf-8"))
        # the student's own original was copied, not moved
        self.assertTrue((self.tmp / "own" / "Unit 4" / "slides.txt").exists())
        files = run_json("manifest", "--course", self.course)["files"]
        self.assertEqual(sorted(files), ["added/Unsorted/notes.txt", "official/Unit 4/slides.txt"])
        self.assertEqual(list(json.loads((self.course / ".unistudent" / "wiki.json").read_text("utf-8"))),
                         ["official/Unit 4/slides.txt"])
        self.assertEqual(run_json("wiki", "check", "--course", self.course)["problems"], [])

    def test_migrate_twice_changes_nothing_more(self):
        run_json("migrate", "--course", self.course, "--apply")
        before = sorted(str(p.relative_to(self.course)) for p in self.course.rglob("*"))
        again = run_json("migrate", "--course", self.course, "--apply")
        self.assertEqual(again["moves"], [])
        self.assertEqual(before, sorted(str(p.relative_to(self.course)) for p in self.course.rglob("*")))

    def test_migrate_refuses_when_a_target_exists_with_different_content(self):
        write(self.course / "2-course-material" / "official" / "Unit 4" / "slides.txt", "something else")
        code, out = run("migrate", "--course", self.course, "--apply")
        self.assertEqual(code, 1)
        self.assertIn("slides.txt", out)
        self.assertTrue((self.course / "raw").exists())  # nothing was moved


if __name__ == "__main__":
    unittest.main()

"""Regression tests for the review findings (data safety first), all through the `us.py` command line."""
import json
import os
import shutil
import unittest
from pathlib import Path
from unittest import mock

from helpers import CourseTestCase, folders, make_pdf, mock_env, run, run_json, write
from unistudent import material


def old_course(root, files):
    """A course folder in the old layout. files: {rel in raw: (content, tier, unit)}; real files, no links."""
    state = root / ".unistudent"
    entries = {}
    for rel, (content, tier, unit) in files.items():
        path = write(root / "raw" / rel, content)
        entries[rel] = {"origin": "inbox", "tier": tier, "unit": unit, "fingerprint": material.fingerprint(path),
                        "size": path.stat().st_size}
    write(state / "settings.json", json.dumps({"course_name": "Old", "language": "en"}))
    write(state / "manifest.json", json.dumps({"files": entries}))
    return root


class MigrationSafety(CourseTestCase):
    def test_two_old_files_whose_names_differ_only_by_case_both_survive(self):  # D1
        course = old_course(self.tmp / "Old", {
            "Unit 4/Notes.txt": ("first", "added", 4), "inbox/notes.txt": ("second", "added", 4)})
        run_json("migrate", "--course", course, "--apply")
        folder = folders(course).material / "added" / "Unit 4"
        self.assertEqual(sorted(p.read_text("utf-8") for p in folder.iterdir()), ["first", "second"])
        self.assertEqual(sorted(p.name.casefold() for p in folder.iterdir()), ["notes (2).txt", "notes.txt"])

    def test_an_inbox_file_never_replaces_a_different_file_at_its_destination(self):  # D1
        course = old_course(self.tmp / "Old", {})
        write(course / "inbox" / "a.txt", "mine")
        write(course / "1-inbox" / "a.txt", "already here")
        code, out = run("migrate", "--course", course, "--apply")
        self.assertEqual(code, 1)
        self.assertEqual((course / "inbox" / "a.txt").read_text("utf-8"), "mine")
        self.assertEqual((course / "1-inbox" / "a.txt").read_text("utf-8"), "already here")

    def test_an_interrupted_migration_is_picked_up_where_it_stopped(self):  # D4
        course = old_course(self.tmp / "Old", {"Unit 4/a.txt": ("alpha", "official", 4),
                                               "Unit 4/b.txt": ("beta", "official", 4)})
        dest = course / "2-course-material" / "official" / "Unit 4"
        dest.mkdir(parents=True)
        shutil.move(str(course / "raw" / "Unit 4" / "a.txt"), str(dest / "a.txt"))  # the first move happened, then it died
        run_json("migrate", "--course", course, "--apply")
        files = run_json("manifest", "--course", course)["files"]
        self.assertEqual(sorted(files), ["official/Unit 4/a.txt", "official/Unit 4/b.txt"])
        self.assertEqual((dest / "a.txt").read_text("utf-8"), "alpha")

    def test_the_obsidian_settings_of_the_old_study_folder_come_along(self):  # D8
        course = old_course(self.tmp / "Old", {})
        write(course / "study" / ".obsidian" / "app.json", "{}")
        result = run_json("migrate", "--course", course, "--apply")
        self.assertTrue((folders(course).study / ".obsidian" / "app.json").is_file())
        self.assertNotIn("study", result["left_behind"])


    def test_study_and_transcript_links_follow_the_files_to_their_new_places(self):  # D7
        course = old_course(self.tmp / "Old", {"Unit 4/a b.txt": ("alpha", "official", 4)})
        write(course / "wiki" / "sources" / "unit-04" / "a b.md", "---\nsource: Unit 4/a b.txt\n---\n# a b\n")
        write(course / "study" / "Unit 4" / "sub" / "p.md",
              "x [raw](<../../../raw/Unit 4/a b.txt>) y [wiki](../../../wiki/sources/unit-04/a%20b.md) z "
              "[again](../../../raw/Unit%204/a%20b.txt#top)\n")
        video = (course.resolve() / "raw" / "Unit 4" / "a b.txt").as_uri()
        write(course / "wiki" / "recordings" / "a b" / "transcript.md", f"Sources: [recording]({video})\n")
        run_json("migrate", "--course", course, "--apply")
        f = folders(course)
        page = (f.study / "Unit 4" / "sub" / "p.md").read_text("utf-8")
        self.assertIn("(<../../../2-course-material/official/Unit 4/a b.txt>)", page)
        self.assertIn("(../../../.unistudent/wiki/sources/unit-04/a%20b.md)", page)
        self.assertIn("(../../../2-course-material/official/Unit%204/a%20b.txt#top)", page)
        transcript = (f.wiki / "recordings" / "a b" / "transcript.md").read_text("utf-8")
        self.assertIn((f.material / "official" / "Unit 4" / "a b.txt").resolve().as_uri(), transcript)
        self.assertEqual(run_json("check", f.study, "--course", course)["problems"], [])


class LanguageChange(CourseTestCase):
    def test_a_language_change_onto_an_existing_folder_is_refused_and_changes_nothing(self):  # D2
        course = self.tmp / "Macro"
        run_json("setup", course, "--name", "Macro", "--language", "en")
        write(folders(course).inbox / "Unit 1 notes.txt", "money")
        run_json("add", "--course", course)
        (course / "2-חומרי-הקורס").mkdir()
        code, out = run("setup", course, "--language", "he")
        self.assertEqual(code, 1)
        self.assertIn("2-חומרי-הקורס", out)
        settings = json.loads((course / ".unistudent" / "settings.json").read_text("utf-8"))
        self.assertEqual((settings["language"], settings["folders"]["material"]), ("en", "2-course-material"))
        self.assertEqual(list(run_json("manifest", "--course", course)["files"]), ["added/Unit 1/Unit 1 notes.txt"])
        run_json("wiki", "build", "--course", course)
        self.assertEqual(list(run_json("manifest", "--course", course)["files"]), ["added/Unit 1/Unit 1 notes.txt"])

    def test_a_language_change_renames_the_inner_folders_too(self):  # D2
        course = self.tmp / "Macro"
        run_json("setup", course, "--name", "Macro", "--language", "en")
        write(folders(course).inbox / "Unit 3 notes.txt", "money")
        run_json("add", "--course", course)
        run_json("setup", course, "--language", "he")
        self.assertTrue((course / "2-חומרי-הקורס" / "נוסף" / "יחידה 3" / "Unit 3 notes.txt").is_file())
        self.assertEqual(list(run_json("manifest", "--course", course)["files"]), ["נוסף/יחידה 3/Unit 3 notes.txt"])


class ScanSafety(CourseTestCase):
    def setUp(self):
        super().setUp()
        self.course = self.tmp / "Macro"
        run_json("setup", self.course, "--name", "Macro", "--language", "en")
        self.f = folders(self.course)
        write(self.f.inbox / "Unit 1 a.txt", "alpha")
        write(self.f.inbox / "Unit 1 b.txt", "beta")
        run_json("add", "--course", self.course)

    def files(self):
        return sorted(run_json("manifest", "--course", self.course)["files"])

    def test_an_emptied_material_folder_does_not_wipe_the_manifest_or_the_wiki(self):  # D3
        for p in list((self.f.material / "added" / "Unit 1").iterdir()):
            p.unlink()
        code, out = run("wiki", "build", "--course", self.course)
        self.assertEqual(code, 1)
        self.assertIn("Material folder", out)
        self.assertEqual(len(self.files()), 2)
        self.assertTrue((self.f.wiki / "sources" / "unit-01" / "Unit 1 a.md").exists())

    def test_a_missing_material_folder_does_not_wipe_anything(self):  # D3
        shutil.rmtree(self.f.material)
        code, _ = run("wiki", "build", "--course", self.course)
        self.assertEqual(code, 1)
        self.assertEqual(len(self.files()), 2)

    def test_an_icloud_placeholder_counts_as_present(self):  # D3
        folder = self.f.material / "added" / "Unit 1"
        (folder / "Unit 1 a.txt").unlink()
        write(folder / ".Unit 1 a.txt.icloud", "")
        run_json("wiki", "build", "--course", self.course)
        self.assertEqual(len(self.files()), 2)

    def test_a_new_file_in_a_subfolder_the_student_made_stays_there(self):  # D8
        write(self.f.material / "added" / "Week 1" / "x.txt", "week one")
        run_json("wiki", "build", "--course", self.course)
        self.assertTrue((self.f.material / "added" / "Week 1" / "x.txt").is_file())
        self.assertIn("added/Week 1/x.txt", self.files())

    def test_identical_files_that_move_keep_their_own_notes(self):  # D8
        run_json("add", "--course", self.course)
        for unit, note in ((4, "from A"), (5, "from B")):
            write(self.f.inbox / f"Unit {unit} same.txt", "same content")
            run_json("add", "--course", self.course, "--describe", f"Unit {unit} same.txt={note}")
        m = self.f.material / "added"
        (m / "Unit 6").mkdir()
        (m / "Unit 4" / "Unit 4 same.txt").rename(m / "Unit 6" / "d.txt")
        (m / "Unit 5" / "Unit 5 same.txt").rename(m / "Unit 5" / "c.txt")
        run_json("wiki", "build", "--course", self.course)
        files = run_json("manifest", "--course", self.course)["files"]
        self.assertEqual(files["added/Unit 5/c.txt"]["origin_note"], "from B")
        self.assertEqual(files["added/Unit 6/d.txt"]["origin_note"], "from A")

    def test_assign_on_an_old_layout_folder_says_to_migrate(self):  # D8, S3
        old = old_course(self.tmp / "Old", {"Unit 4/a.txt": ("alpha", "official", None)})
        for argv in (("assign", "Unit 4/a.txt", "4"), ("unsorted",), ("wiki", "build"), ("add",)):
            code, out = run(*argv, "--course", old)
            self.assertEqual(code, 1, argv)
            self.assertIn("us migrate --apply", out, argv)
            self.assertNotIn("Errno", out, argv)
        code, out = run("setup", old)
        self.assertIn("us migrate --apply", out)


class ReplaceSafety(CourseTestCase):
    def setUp(self):
        super().setUp()
        self.course = self.tmp / "Macro"
        run("setup", self.course, "--name", "Macro", "--language", "en", "--university", "openu")
        self.staged = self.tmp / "staged"

    def ingest(self, name, content):
        write(self.staged / name, content)
        item = {"url": "https://example.edu/f/1", "file": name, "name": name, "section": "Unit 1"}
        path = write(self.tmp / "listing.json", json.dumps({"items": [item]}))
        return run("ingest", "--course", self.course, path, self.staged, "--json")

    def test_a_failed_update_keeps_the_old_copy(self):  # D5
        self.ingest("notes.txt", "version one")
        old = folders(self.course).material / "official" / "Unit 1" / "notes.txt"
        with mock.patch.object(material.shutil, "move", side_effect=OSError("disk full")):
            code, _ = self.ingest("notes.txt", "version two")
        self.assertEqual(code, 1)
        self.assertEqual(old.read_text("utf-8"), "version one")

    def test_an_update_with_another_extension_keeps_the_new_extension(self):  # D5
        self.ingest("notes.txt", "version one")
        self.ingest("notes.md", "version two")
        files = run_json("manifest", "--course", self.course)["files"]
        self.assertEqual(list(files), ["official/Unit 1/notes.md"])
        self.assertEqual(sorted(p.name for p in (folders(self.course).material / "official" / "Unit 1").iterdir()), ["notes.md"])


class WindowsPaths(CourseTestCase):
    def test_the_install_command_is_valid_in_powershell_when_the_python_path_has_a_space(self):  # D9
        course = self.tmp / "Macro"
        write(self.tmp / "own" / "Unit 1" / "s.mp4", b"\x00" * 64)
        run_json("setup", course, "--name", "Macro", "--language", "en", "--import", self.tmp / "own")
        for system, expected in (("Windows", '& "C:\\Program Files\\Python 3\\python.exe" -m pip install faster-whisper'),
                                 ("Linux", '"/opt/my python/bin/python" -m pip install faster-whisper')):
            exe = "C:\\Program Files\\Python 3\\python.exe" if system == "Windows" else "/opt/my python/bin/python"
            with mock_env(UNISTUDENT_STT_BACKEND="faster"), mock.patch("sys.executable", exe), \
                    mock.patch("unistudent.recordings.backend_available", return_value=False), \
                    mock.patch("importlib.util.find_spec", return_value=object()), \
                    mock.patch("unistudent.recordings.platform.system", return_value=system):
                self.assertEqual(run_json("recordings", "estimate", "--course", course)["install_run"], expected)

    def test_a_file_whose_path_would_be_too_long_for_windows_is_refused_and_stays_in_the_inbox(self):  # D9
        course = self.tmp / "Macro"
        run_json("setup", course, "--name", "Macro", "--language", "en")
        name = "Unit 1 " + "x" * 200 + ".txt"
        write(folders(course).inbox / name, "text")
        with mock.patch("unistudent.material.platform.system", return_value="Windows"):
            code, out = run("add", "--course", course)
        self.assertEqual(code, 1)
        self.assertIn("too long for Windows", out)
        self.assertTrue((folders(course).inbox / name).is_file())


if __name__ == "__main__":
    unittest.main()

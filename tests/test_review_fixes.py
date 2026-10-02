"""Regression tests for the review findings (data safety first), all through the `us.py` command line."""
import json
import os
import re
import shutil
import unittest
from pathlib import Path
from unittest import mock

from helpers import CourseTestCase, folders, make_pdf, mock_env, run, run_json, write
from unistudent import material


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
        self.assertTrue((course / "2-חומרי-הקורס" / "חומר-לא-רשמי" / "יחידה 3" / "Unit 3 notes.txt").is_file())
        self.assertEqual(list(run_json("manifest", "--course", course)["files"]), ["חומר-לא-רשמי/יחידה 3/Unit 3 notes.txt"])


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


class HebrewNames(CourseTestCase):
    def test_folders_with_the_earlier_hebrew_names_are_recognized_and_renamed(self):
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--language", "he")
        f = folders(course)
        write(f.material / "רשמי" / "יחידה 4" / "a.txt", "alpha")
        run("setup", course, "--name", "Macro", "--language", "he")
        self.assertTrue((f.material / "חומר-רשמי-של-הקורס" / "יחידה 4" / "a.txt").is_file())
        self.assertFalse((f.material / "רשמי").exists())
        self.assertIn("חומר-רשמי-של-הקורס/יחידה 4/a.txt", run_json("manifest", "--course", course)["files"])


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


class WikiFollowsMoves(CourseTestCase):
    def setUp(self):
        super().setUp()
        self.course = self.tmp / "Macro"
        run_json("setup", self.course, "--name", "Macro", "--language", "en")
        self.f = folders(self.course)

    def test_moving_a_source_rewrites_the_links_to_its_old_wiki_page(self):  # D6
        write(self.f.inbox / "Unit 4 notes.txt", "money multiplier")
        run_json("add", "--course", self.course)
        write(self.f.wiki / "glossary.md", "### multiplier\nSources: [n](<sources/unit-04/Unit 4 notes.md#page-1>)\n")
        write(self.f.wiki / "units" / "unit-04.md", "x\n\nSources: [n](<../sources/unit-04/Unit 4 notes.md#page-1>)\n")
        (self.f.material / "added" / "Unit 5").mkdir()
        shutil.move(str(self.f.material / "added" / "Unit 4" / "Unit 4 notes.txt"),
                    str(self.f.material / "added" / "Unit 5" / "Unit 4 notes.txt"))
        run_json("wiki", "build", "--course", self.course)
        self.assertIn("(<sources/unit-05/Unit 4 notes.md#page-1>)", (self.f.wiki / "glossary.md").read_text("utf-8"))
        self.assertIn("(<../sources/unit-05/Unit 4 notes.md#page-1>)", (self.f.wiki / "units" / "unit-04.md").read_text("utf-8"))
        self.assertEqual(run_json("wiki", "check", "--course", self.course)["problems"], [])

    def test_a_recording_keeps_its_wiki_folder_when_a_same_named_one_arrives(self):  # D6
        for tier, content in (("official", b"A" * 64), ("added", b"B" * 64)):
            write(self.tmp / tier / "Unit 4" / "s.mp4", content)
        run_json("import", self.tmp / "official", "--course", self.course, "--tier", "official")
        with mock_env(UNISTUDENT_STT_BACKEND="fake"):
            run_json("recordings", "approve", "--course", self.course, "official/Unit 4/s.mp4")
            run_json("recordings", "transcribe", "--course", self.course, "official/Unit 4/s.mp4")
        run_json("import", self.tmp / "added", "--course", self.course, "--tier", "added")
        rows = {r["path"]: r for r in run_json("recordings", "list", "--course", self.course)["recordings"]}
        self.assertTrue(rows["official/Unit 4/s.mp4"]["has_transcript"])
        self.assertFalse(rows["added/Unit 4/s.mp4"]["has_transcript"])
        summary = run_json("recordings", "list", "--course", self.course)["summary"]
        self.assertIn("partial  official/Unit 4/s.mp4", summary)
        self.assertIn("none  added/Unit 4/s.mp4", summary)
        # the other one is deleted: the first keeps its folder instead of taking the freed name
        (self.f.material / "added" / "Unit 4" / "s.mp4").unlink()
        run_json("wiki", "build", "--course", self.course)
        rows = {r["path"]: r for r in run_json("recordings", "list", "--course", self.course)["recordings"]}
        self.assertTrue(rows["official/Unit 4/s.mp4"]["has_transcript"])

    def test_the_transcripts_video_link_is_relative_and_follows_a_move(self):  # D7
        write(self.tmp / "own" / "Unit 4" / "s.mp4", b"\x00" * 64)
        run_json("import", self.tmp / "own", "--course", self.course, "--tier", "official")
        with mock_env(UNISTUDENT_STT_BACKEND="fake"):
            run_json("recordings", "approve", "--course", self.course, "official/Unit 4/s.mp4")
            run_json("recordings", "transcribe", "--course", self.course, "official/Unit 4/s.mp4")
        transcript = self.f.wiki / "recordings" / "s" / "transcript.md"
        self.assertNotIn("file://", transcript.read_text("utf-8"))
        (self.f.material / "official" / "Unit 5").mkdir()
        shutil.move(str(self.f.material / "official" / "Unit 4" / "s.mp4"), str(self.f.material / "official" / "Unit 5" / "s.mp4"))
        run_json("wiki", "build", "--course", self.course)
        self.assertIn("official/Unit 5/s.mp4", transcript.read_text("utf-8"))
        self.assertEqual(run_json("wiki", "check", "--course", self.course)["problems"], [])


class TrustAndCoverage(CourseTestCase):
    def test_the_grounding_rule_says_to_read_live_coverage_before_saying_something_is_missing(self):  # T1
        course = self.tmp / "Macro"
        run_json("setup", course, "--name", "Macro", "--language", "en")
        context = run_json("course-context", "--course", course)["summary"]
        self.assertIn(".unistudent/wiki/coverage.md", context)
        self.assertIn("us wiki coverage", context)
        self.assertIn("failed", context)
        self.assertIn("skipped", context)

    def test_a_short_text_file_is_not_flagged_as_needing_visual_reading(self):  # T2
        course = self.tmp / "Macro"
        run_json("setup", course, "--name", "Macro", "--language", "en")
        write(folders(course).inbox / "Unit 1 hint.md", "Exam: chapter 3.")
        built = run_json("add", "--course", course)["wiki"]
        self.assertEqual(built["needs_visual"], [])
        rows = {r["path"]: r for r in run_json("wiki", "coverage", "--course", course)["files"]}
        self.assertEqual(rows["added/Unit 1/Unit 1 hint.md"]["why"], "")


class RoadmapsAndAnnouncements(CourseTestCase):
    def setUp(self):
        super().setUp()
        self.course = self.tmp / "Macro"
        write(self.tmp / "own" / "Unit 4" / "session 5.mp4", b"\x00" * 64)
        run_json("setup", self.course, "--name", "Macro", "--language", "en", "--import", self.tmp / "own", "--tier", "official")
        self.f = folders(self.course)
        with mock_env(UNISTUDENT_STT_BACKEND="fake"):
            run_json("recordings", "approve", "--course", self.course, "official/Unit 4/session 5.mp4")
            run_json("recordings", "transcribe", "--course", self.course, "official/Unit 4/session 5.mp4")
        self.rec = self.f.wiki / "recordings" / "session 5"
        write(self.rec / "toc.md", "Sources: [transcript](transcript.md)\n\n| 00:01:00 | exam question | [00:01:00](transcript.md#000100) |\n")
        write(self.rec / "summary.md", "Sources: [transcript](transcript.md)\n\n## Announcements\n\nHomework due Sunday.\n\n"
                                       '## "This will be on the exam"\n\n- The multiplier, at 00:12:47.\n\n## Topics\n\nMoney.\n')
        self.roadmap = self.f.study / "Unit 4" / "Recordings roadmap.md"

    def test_the_roadmap_keeps_clickable_times_and_a_labelled_generated_block(self):  # T3
        run_json("wiki", "build", "--course", self.course)
        text = self.roadmap.read_text("utf-8")
        self.assertIn("[00:01:00](file://", text)
        self.assertIn("session%205.mp4#t=60)", text)
        self.assertIn("Made from", text.split("<!-- unistudent:generated:start -->")[1].split("<!-- unistudent:generated:end -->")[0])
        self.assertEqual(run_json("check", self.roadmap, "--labels", "--course", self.course)["problems"], [])

    def test_text_outside_the_generated_block_is_still_checked_for_sources(self):  # T3
        run_json("wiki", "build", "--course", self.course)
        self.roadmap.write_text(self.roadmap.read_text("utf-8") + "\nThe multiplier is always five in every economy.\n", "utf-8")
        kinds = [p["kind"] for p in run_json("check", self.roadmap, "--labels", "--course", self.course)["problems"]]
        self.assertEqual(kinds, ["no-citation"])

    def test_a_roadmap_goes_when_its_recording_loses_its_summary_or_is_deleted(self):  # T3
        run_json("wiki", "build", "--course", self.course)
        self.assertTrue(self.roadmap.exists())
        (self.rec / "summary.md").unlink()
        run_json("wiki", "build", "--course", self.course)
        self.assertFalse(self.roadmap.exists())

    def test_the_unit_page_collects_announcements_and_exam_hints(self):  # T3
        run_json("wiki", "build", "--course", self.course)
        unit = (self.f.wiki / "units" / "unit-04.md").read_text("utf-8")
        self.assertIn("Announcements", unit)
        self.assertIn("Homework due Sunday.", unit)
        self.assertIn("The multiplier, at 00:12:47.", unit)
        self.assertNotIn("Money.", unit)
        self.assertEqual(run_json("wiki", "check", "--course", self.course)["problems"], [])

    def test_the_study_pack_writer_is_told_to_surface_them(self):  # T3
        for name in ("study-pack-writer", "study-pack"):
            self.assertIn("Announcements", run_json("doc", name)["text"])


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "plugins" / "unistudent" / "scripts" / "unistudent"
SETUP_TEXT = (CORE / "skills" / "course-setup" / "SKILL.md").read_text("utf-8")


def step(number):
    return next(part for part in SETUP_TEXT.split("\n## ") if part.startswith(f"{number}."))


class SetupSkill(CourseTestCase):
    def test_the_overview_counts_the_numbered_steps_and_the_stages_match_the_cli(self):  # S4
        from unistudent.course import SETUP_STAGES
        numbered = re.findall(r"(?m)^## (\d+)\.", SETUP_TEXT)
        self.assertIn(f"Step 5 of {len(numbered) - 1}", SETUP_TEXT)  # step 0 is bookkeeping
        self.assertNotIn("fetch-and-organize", SETUP_TEXT)
        for stage in ("fetch", "sort", "recordings"):
            self.assertIn(f"--stage {stage}", SETUP_TEXT)
            self.assertIn(stage, SETUP_STAGES)
        self.assertEqual([m for m in re.findall(r"--stage ([a-z-]+)", SETUP_TEXT) if m not in SETUP_STAGES], [])

    def test_a_progress_file_from_the_old_single_step_resumes_at_analyze(self):  # S4
        write(self.home / "setup-progress" / "Macro.json", json.dumps({"stage": "fetch-and-organize", "answers": {}}))
        self.assertEqual(run_json("setup-progress", "status", "--course-name", "Macro")["next_stage"], "analyze")

    def test_the_university_is_recorded_before_the_install_stop_and_a_restart_is_explained(self):  # S2
        one = step(1)
        self.assertLess(one.index("--stage university"), one.index("us plugins recommend"))
        self.assertRegex(one, r"(?i)close and reopen|reload|restart")
        self.assertIn("run setup again", one)

    def test_fetching_with_a_generated_fallback_can_fail_without_being_an_error(self):  # S5
        five = step(5)
        self.assertIn("can't log in", five)
        self.assertIn("not an error", five)
        self.assertIn("only record how the university organizes", five)

    def test_no_skill_or_command_offers_the_removed_migrate(self):
        for skill in (CORE / "skills").glob("*/SKILL.md"):
            self.assertNotIn("us migrate", skill.read_text("utf-8"), skill)

    def test_an_empty_inbox_says_where_it_is_and_what_to_do(self):  # S6
        text = (CORE / "skills" / "course-add" / "SKILL.md").read_text("utf-8")
        self.assertRegex(text, r"Empty → tell the student where the inbox is.*run `/unistudent:course-add` again")

    def test_the_inbox_is_in_the_overview(self):  # S6
        self.assertIn("inbox", SETUP_TEXT.split("## 0.")[0])

    def test_the_install_command_is_for_advanced_users(self):  # S6
        for path in (CORE / "skills" / "course-setup" / "SKILL.md", CORE / "recordings.py", ROOT / "README.md"):
            for line in path.read_text("utf-8").splitlines():
                if "uv tool install" in line:
                    self.assertIn("advanced", line, f"{path.name}: {line[:80]}")

    def test_the_readmes_explain_wiki_and_vault(self):  # S6
        for name in ("README.en.md", "README.he.md"):
            text = (CORE / "templates" / name).read_text("utf-8")
            self.assertIn("vault", text)
            self.assertIn("Wiki", text)
        self.assertNotIn("skill", (CORE / "templates" / "README.he.md").read_text("utf-8"))
        self.assertIn("a vault is just a folder", (ROOT / "README.md").read_text("utf-8"))

    def test_no_plugin_found_still_tells_a_non_claude_student_what_to_do(self):  # S6
        out = run_json("plugins", "recommend", "--university", "Nowhere U", "--course-name", "Basket weaving")
        self.assertEqual(out["plugins"], [])
        self.assertIn("npx skills", out["summary"])

    def test_coverage_is_shown_after_sorting_and_pending_is_explained(self):  # S7
        eight = step(8)
        self.assertIn("pending", eight)
        self.assertLess(SETUP_TEXT.index("## 6."), SETUP_TEXT.index("us wiki coverage"))

    def test_the_layout_docs_say_what_is_true(self):  # H1-H3
        self.assertNotIn("links.py", (ROOT / "CLAUDE.md").read_text("utf-8"))
        self.assertNotIn("keeps working", (ROOT / "README.md").read_text("utf-8"))
        for spec in ("v1", "v2"):
            self.assertIn("superseded by ADR 0007", (ROOT / "docs" / "spec" / f"{spec}.md").read_text("utf-8")[:400])


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

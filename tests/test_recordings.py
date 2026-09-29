"""Recordings into the Wiki (seam 2), with the test speech-to-text backend."""
import os
import unittest

from helpers import CourseTestCase, mock_env, run, run_json, write


class Recordings(CourseTestCase):
    def setUp(self):
        super().setUp()
        own = self.tmp / "own"
        write(own / "Unit 4" / "session 5.mp4", b"\x00" * 4096)
        self.course = self.tmp / "Macro"
        run("setup", self.course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")
        run_json("wiki", "build", "--course", self.course)
        self._stt = mock_env(UNISTUDENT_STT_BACKEND="fake")
        self._stt.__enter__()

    def tearDown(self):
        self._stt.__exit__(None, None, None)
        super().tearDown()

    def test_estimate_lists_what_would_be_processed(self):
        est = run_json("recordings", "estimate", "--course", self.course)
        self.assertEqual(est["recordings"], 1)
        self.assertEqual(est["files"], ["Unit 4/session 5.mp4"])
        self.assertEqual(run_json("recordings", "estimate", "--course", self.course, "--unit", "5")["recordings"], 0)

    def test_transcript_has_timestamped_paragraphs_and_passes_the_wiki_check(self):
        run_json("recordings", "transcribe", "--course", self.course, "Unit 4/session 5.mp4")
        transcript = (self.course / "wiki" / "recordings" / "session 5" / "transcript.md").read_text("utf-8")
        self.assertIn("source: Unit 4/session 5.mp4", transcript)
        self.assertIn("## 00:00:00", transcript)
        self.assertIn("## 00:01:00", transcript)
        self.assertIn("[00:00:20] segment at 00:00:20", transcript)
        self.assertEqual(run_json("wiki", "check", "--course", self.course)["problems"], [])
        # Already transcribed recordings drop out of the estimate.
        self.assertEqual(run_json("recordings", "estimate", "--course", self.course)["recordings"], 0)

    def test_a_recording_counts_as_processed_once_its_summary_exists(self):
        run_json("recordings", "transcribe", "--course", self.course, "Unit 4/session 5.mp4")
        folder = self.course / "wiki" / "recordings" / "session 5"
        write(folder / "summary.md", "# Summary\n\nSources: [transcript](transcript.md)\n")
        run_json("wiki", "build", "--course", self.course)
        unit4 = (self.course / "wiki" / "units" / "unit-04.md").read_text("utf-8")
        self.assertIn("../recordings/session 5/summary.md", unit4)


class SyncedCourseFolder(CourseTestCase):
    def test_recordings_added_to_a_synced_course_folder_live_in_a_local_folder(self):
        local = self.tmp / "local recordings"
        with mock_env(UNISTUDENT_RECORDINGS_ROOT=str(local)):
            course = self.tmp / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Macro"
            result = run_json("setup", course, "--name", "Macro", "--language", "en")
            self.assertTrue(result["synced"])
            write(course / "inbox" / "Unit 2 session.mp4", b"\x00" * 2048)
            run_json("add", "--course", course)
        stored = local / "Macro" / "Unit 2 session.mp4"
        self.assertTrue(stored.is_file())
        raw = course / "raw" / "inbox" / "Unit 2 session.mp4"
        self.assertTrue(raw.is_symlink())
        self.assertTrue(os.path.samefile(raw, stored))

    def test_documents_in_a_synced_course_folder_stay_in_raw(self):
        with mock_env(UNISTUDENT_RECORDINGS_ROOT=str(self.tmp / "local")):
            course = self.tmp / "Google Drive" / "Macro"
            run_json("setup", course, "--name", "Macro", "--language", "en")
            write(course / "inbox" / "notes unit 1.txt", "unit 1 notes text here")
            run_json("add", "--course", course)
        self.assertTrue((course / "raw" / "inbox" / "notes unit 1.txt").is_file())
        self.assertFalse((course / "raw" / "inbox" / "notes unit 1.txt").is_symlink())


if __name__ == "__main__":
    unittest.main()

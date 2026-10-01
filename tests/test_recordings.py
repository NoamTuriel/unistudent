"""Recordings into the Wiki (seam 2), with the test speech-to-text backend."""
from pathlib import Path
import unittest

from helpers import CourseTestCase, file_is_released, folders, mock_env, run, run_json, write


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

    def test_transcribing_needs_the_students_approval_of_that_recording(self):
        rec = "official/Unit 4/session 5.mp4"
        code, out = run("recordings", "transcribe", "--course", self.course, rec)
        self.assertEqual(code, 1)
        self.assertIn("Not approved", out)
        self.assertEqual(run_json("recordings", "estimate", "--course", self.course)["recordings"], 1)
        run_json("recordings", "approve", "--course", self.course, rec)
        run_json("recordings", "transcribe", "--course", self.course, rec)
        self.assertEqual(run_json("recordings", "estimate", "--course", self.course)["recordings"], 0)
        # The approval is used up: transcribing again needs a new yes.
        code, out = run("recordings", "transcribe", "--course", self.course, rec)
        self.assertEqual(code, 1)
        self.assertIn("Not approved", out)

    def test_approving_something_that_is_not_a_recording_is_refused(self):
        code, out = run("recordings", "approve", "--course", self.course, "official/Unit 4/nope.mp4")
        self.assertEqual(code, 1)
        self.assertIn("Not a recording", out)

    def test_estimate_lists_what_would_be_processed(self):
        est = run_json("recordings", "estimate", "--course", self.course)
        self.assertEqual(est["recordings"], 1)
        self.assertEqual(est["files"], ["official/Unit 4/session 5.mp4"])
        self.assertEqual(run_json("recordings", "estimate", "--course", self.course, "--unit", "5")["recordings"], 0)

    def test_a_missing_engine_comes_with_the_command_that_installs_it(self):
        with mock_env(UNISTUDENT_STT_BACKEND="faster"):
            est = run_json("recordings", "estimate", "--course", self.course)
        if est["backend_installed"]:
            self.skipTest("faster-whisper is installed here")
        self.assertIn("install", est["install_run"])
        self.assertIn("faster-whisper", est["install_run"])
        self.assertIn(est["install_run"], est["install_command"])

    def test_transcript_has_timestamped_paragraphs_and_passes_the_wiki_check(self):
        run_json("recordings", "approve", "--course", self.course, "official/Unit 4/session 5.mp4")
        run_json("recordings", "transcribe", "--course", self.course, "official/Unit 4/session 5.mp4")
        transcript = (folders(self.course).wiki / "recordings" / "session 5" / "transcript.md").read_text("utf-8")
        self.assertIn("source: official/Unit 4/session 5.mp4", transcript)
        self.assertIn("## 00:00:00", transcript)
        self.assertIn("## 00:01:00", transcript)
        self.assertIn("[00:00:20] segment at 00:00:20", transcript)
        vtt = (folders(self.course).wiki / "recordings" / "session 5" / "transcript.vtt").read_text("utf-8")
        self.assertTrue(vtt.startswith("WEBVTT"))
        self.assertIn("00:00:20.000 --> 00:00:40.000", vtt)
        self.assertEqual(run_json("wiki", "check", "--course", self.course)["problems"], [])
        # Already transcribed recordings drop out of the estimate.
        self.assertEqual(run_json("recordings", "estimate", "--course", self.course)["recordings"], 0)

    def test_background_transcription_returns_at_once_and_finishes(self):
        import time
        run_json("recordings", "approve", "--course", self.course, "official/Unit 4/session 5.mp4")
        job = run_json("recordings", "transcribe", "--course", self.course, "official/Unit 4/session 5.mp4", "--background")
        self.assertTrue(job["log"].endswith(".log"))
        transcript = folders(self.course).wiki / "recordings" / "session 5" / "transcript.md"
        log = Path(job["log"])
        for _ in range(100):
            # On Windows the log file stays locked for as long as the detached process is alive:
            # wait for that too, or tearDown's cleanup races the still-running process.
            if transcript.exists() and file_is_released(log):
                break
            time.sleep(0.1)
        self.assertTrue(transcript.exists(), log.read_text("utf-8"))

    def test_a_recording_counts_as_processed_once_its_summary_exists(self):
        run_json("recordings", "approve", "--course", self.course, "official/Unit 4/session 5.mp4")
        run_json("recordings", "transcribe", "--course", self.course, "official/Unit 4/session 5.mp4")
        folder = folders(self.course).wiki / "recordings" / "session 5"
        write(folder / "summary.md", "# Summary\n\nSources: [transcript](transcript.md)\n")
        run_json("wiki", "build", "--course", self.course)
        unit4 = (folders(self.course).wiki / "units" / "unit-04.md").read_text("utf-8")
        self.assertIn("../recordings/session 5/summary.md", unit4)


class SyncedCourseFolder(CourseTestCase):
    def test_recordings_added_to_a_synced_course_folder_live_in_a_local_folder(self):
        local = self.tmp / "local recordings"
        with mock_env(UNISTUDENT_RECORDINGS_ROOT=str(local)):
            course = self.tmp / "Library" / "Mobile Documents" / "com~apple~CloudDocs" / "Macro"
            result = run_json("setup", course, "--name", "Macro", "--language", "en")
            self.assertTrue(result["synced"])
            write(folders(course).inbox / "Unit 2 session.mp4", b"\x00" * 2048)
            run_json("add", "--course", course)
            run_json("wiki", "build", "--course", course)  # a rescan must not drop a recording kept outside
        stored = local / "Macro" / "added" / "Unit 2" / "Unit 2 session.mp4"
        self.assertTrue(stored.is_file())
        self.assertFalse((folders(course).material / "added" / "Unit 2" / "Unit 2 session.mp4").exists())
        files = run_json("manifest", "--course", course)["files"]
        self.assertEqual(list(files), ["added/Unit 2/Unit 2 session.mp4"])
        self.assertEqual(files["added/Unit 2/Unit 2 session.mp4"]["stored_at"], str(stored))

    def test_documents_in_a_synced_course_folder_stay_in_the_material_folder(self):
        with mock_env(UNISTUDENT_RECORDINGS_ROOT=str(self.tmp / "local")):
            course = self.tmp / "Google Drive" / "Macro"
            run_json("setup", course, "--name", "Macro", "--language", "en")
            write(folders(course).inbox / "notes unit 1.txt", "unit 1 notes text here")
            run_json("add", "--course", course)
        self.assertTrue((folders(course).material / "added" / "Unit 1" / "notes unit 1.txt").is_file())


if __name__ == "__main__":
    unittest.main()

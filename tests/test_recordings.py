"""Recordings into the Wiki (seam 2), with the test speech-to-text backend."""
import shutil
import subprocess
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
        write(folder / "recording-summary.md", "# Summary\n\nSources: [transcript](transcript.md)\n")
        run_json("wiki", "build", "--course", self.course)
        unit4 = (folders(self.course).wiki / "units" / "unit-04.md").read_text("utf-8")
        self.assertIn("../recordings/session 5/recording-summary.md", unit4)

    def test_a_summary_an_older_version_wrote_as_summary_md_is_renamed_and_links_follow(self):
        # Claude Code refuses a subagent's new file named summary.md, so summaries are recording-summary.md now.
        run_json("recordings", "approve", "--course", self.course, "official/Unit 4/session 5.mp4")
        run_json("recordings", "transcribe", "--course", self.course, "official/Unit 4/session 5.mp4")
        wiki = folders(self.course).wiki
        write(wiki / "recordings" / "session 5" / "summary.md", "Session 5.\n\nSources: [transcript](transcript.md)\n")
        bank = wiki / "question-bank.md"
        write(bank, bank.read_text("utf-8") + "\n- Q1: [solved](<recordings/session 5/summary.md>)\n")
        self.assertTrue(run_json("recordings", "list", "--course", self.course)["recordings"][0]["processed"])
        run_json("wiki", "build", "--course", self.course)
        self.assertFalse((wiki / "recordings" / "session 5" / "summary.md").exists())
        self.assertTrue((wiki / "recordings" / "session 5" / "recording-summary.md").exists())
        self.assertIn("(<recordings/session 5/recording-summary.md>)", bank.read_text("utf-8"))
        self.assertEqual(run_json("wiki", "check", "--course", self.course)["problems"], [])

    def test_a_moved_recording_takes_its_transcript_sidecar_along_and_the_transcript_follows(self):
        rec = "official/Unit 4/session 5.mp4"
        run_json("recordings", "approve", "--course", self.course, rec)
        run_json("recordings", "transcribe", "--course", self.course, rec)
        material = folders(self.course).material
        self.assertTrue((material / "official" / "Unit 4" / "session 5.vtt").exists())
        why = {f["path"]: f["why"] for f in run_json("wiki", "coverage", "--course", self.course)["files"]}
        self.assertIn("waiting for its summary", why[rec])  # transcribed already: only the summary is missing
        moved = run_json("assign", "--course", self.course, rec, "lessons")["path"]
        self.assertTrue((material / moved).with_suffix(".vtt").exists())
        self.assertFalse((material / "official" / "Unit 4" / "session 5.vtt").exists())
        built = run_json("wiki", "build", "--course", self.course)
        self.assertEqual(built["folder"]["new"], 0)  # the sidecar is never taken as new course material
        transcript = (folders(self.course).wiki / "recordings" / "session 5" / "transcript.md").read_text("utf-8")
        self.assertIn(f"source: {moved}\nunit: lessons\n", transcript)


class TranscriptionProgress(CourseTestCase):
    def test_a_running_transcription_shows_in_the_list_and_the_box(self):
        import time
        own = self.tmp / "own"
        write(own / "Unit 4" / "session 5.mp4", b"\x00" * 4096)
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")
        rec = "official/Unit 4/session 5.mp4"
        with mock_env(UNISTUDENT_STT_BACKEND="fake", UNISTUDENT_FAKE_STT_SECONDS="3"):
            run_json("recordings", "approve", "--course", course, rec)
            job = run_json("recordings", "transcribe", "--course", course, rec, "--background")
            for _ in range(50):
                row = run_json("recordings", "list", "--course", course)["recordings"][0]
                if row["transcribing"]:
                    break
                time.sleep(0.1)
            self.assertTrue(row["state"].startswith("transcribing (started "), row)
            self.assertIn("Transcribing one now: started", run_json("fetch-plan", "status", "--course", course)["box"])
            transcript = folders(course).wiki / "recordings" / "session 5" / "transcript.md"
            for _ in range(100):
                if transcript.exists() and file_is_released(Path(job["log"])):
                    break
                time.sleep(0.1)
        row = run_json("recordings", "list", "--course", course)["recordings"][0]
        self.assertEqual((row["state"], row["transcribing"]), ("partial", False))
        self.assertNotIn("Transcribing one now", (course / "progress.txt").read_text("utf-8"))


class FasterOption(CourseTestCase):
    """A Mac with a Hebrew course can choose the faster model (about 3x, a few more misheard words); accurate stays the default."""

    def test_the_faster_model_is_offered_with_its_time_and_used_once_chosen(self):
        from unittest import mock
        own = self.tmp / "own"
        write(own / "Unit 4" / "session 5.mp4", b"\x00" * 4096)
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--language", "he", "--import", own, "--tier", "official")
        write(self.home / "benchmark.json", '{"backend": "mlx", "realtime_factor": 0.16}')
        with mock_env(UNISTUDENT_STT_BACKEND="mlx"), mock.patch("unistudent.recordings.duration", return_value=4 * 3600.0):
            accurate = run_json("recordings", "estimate", "--course", course)
            self.assertEqual(accurate["estimated_hours"], 0.64)
            self.assertLess(accurate["faster_option"]["estimated_hours"], 0.64 / 2.5)
            run_json("context", "--course", course, "--transcription", "fast")
            fast = run_json("recordings", "estimate", "--course", course)
        self.assertEqual(fast["estimated_hours"], accurate["faster_option"]["estimated_hours"])
        self.assertIsNone(fast["faster_option"])
        with mock_env(UNISTUDENT_STT_BACKEND="fake"):  # no faster model for this engine: nothing to offer
            self.assertIsNone(run_json("recordings", "estimate", "--course", course)["faster_option"])


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
class GraphicsCardWithoutItsLibraries(CourseTestCase):
    def test_missing_cuda_libraries_fall_back_to_the_processor_and_say_so(self):
        import contextlib
        import io
        import sys
        import types
        from unittest import mock

        class Model:  # faster-whisper on an NVIDIA computer without cuBLAS/cuDNN
            def __init__(self, model, device="auto", compute_type="auto"):
                self.device = device

            def transcribe(self, audio, **options):
                heard.append(audio)
                if self.device != "cpu":
                    raise RuntimeError("Library cublas64_12.dll is not found or cannot be loaded")
                return iter([types.SimpleNamespace(start=0.0, end=1.5, text=" hello")]), None

        heard = []
        own = self.tmp / "own"
        (own / "Unit 4").mkdir(parents=True)
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=duration=2", str(own / "Unit 4" / "a.m4a")],
                       check=True)
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")
        said = io.StringIO()
        with mock_env(UNISTUDENT_STT_BACKEND="faster"), \
                mock.patch.dict(sys.modules, {"faster_whisper": types.SimpleNamespace(WhisperModel=Model)}), \
                contextlib.redirect_stderr(said):
            run_json("recordings", "approve", "--course", course, "official/Unit 4/a.m4a")
            run_json("recordings", "transcribe", "--course", course, "official/Unit 4/a.m4a")
        self.assertIn("hello", (folders(course).wiki / "recordings" / "a" / "transcript.md").read_text("utf-8"))
        self.assertIn("processor", said.getvalue())
        try:
            import numpy  # noqa: F401  (installed with faster-whisper)
        except ImportError:
            return
        # The sound is decoded here, not by faster-whisper's own reader, which fails with PyAV 19.
        self.assertTrue(all(not isinstance(a, str) for a in heard))


class NoGraphicsCard(CourseTestCase):
    def test_without_an_nvidia_card_the_estimate_warns_that_the_processor_does_the_work(self):
        from unittest import mock
        own = self.tmp / "own"
        write(own / "Unit 4" / "session 5.mp4", b"\x00" * 4096)
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")
        with mock_env(UNISTUDENT_STT_BACKEND="faster"):
            with mock.patch("unistudent.recordings.has_nvidia_gpu", return_value=False):
                self.assertIn("processor", run_json("recordings", "estimate", "--course", course)["warning"])
            with mock.patch("unistudent.recordings.has_nvidia_gpu", return_value=True):
                self.assertIsNone(run_json("recordings", "estimate", "--course", course)["warning"])
        with mock_env(UNISTUDENT_STT_BACKEND="mlx"):  # a Mac's own engine uses its graphics: nothing to warn about
            self.assertIsNone(run_json("recordings", "estimate", "--course", course)["warning"])


class OldestFirst(CourseTestCase):
    """Recordings are listed and transcribed oldest first (by the date in their name), so unit 1 is usable first."""

    def test_recordings_are_listed_and_transcribed_by_recording_date(self):
        own = self.tmp / "own"
        for name in ("a lesson 2026-08-03.mp4", "b lesson 2026-07-16.mp4", "c lesson 12.10.2025.mp4"):
            write(own / "Unit 4" / name, name.encode() + b"\x00" * 4096)
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")
        oldest_first = [f"official/Unit 4/{n}" for n in ("c lesson 12.10.2025.mp4", "b lesson 2026-07-16.mp4",
                                                         "a lesson 2026-08-03.mp4")]
        listed = [r["path"] for r in run_json("recordings", "list", "--course", course)["recordings"]]
        self.assertEqual(listed, oldest_first)
        self.assertEqual(run_json("recordings", "estimate", "--course", course)["files"], oldest_first)
        with mock_env(UNISTUDENT_STT_BACKEND="fake"):
            run_json("recordings", "approve", "--course", course, *reversed(oldest_first))
            done = run_json("recordings", "transcribe", "--course", course, *reversed(oldest_first))["transcripts"]
        self.assertEqual([Path(p).parent.name for p in done], [Path(r).stem for r in oldest_first])


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not installed")
class SilenceFilter(CourseTestCase):
    def test_text_over_a_long_silence_is_dropped_from_the_transcript(self):
        # Whisper invents "Thank you." over a silent break; the test engine writes a line every 20 s, 0 to 140 s.
        own = self.tmp / "own"
        (own / "Unit 4").mkdir(parents=True)
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i",
                        "aevalsrc='if(between(t,30,130),0,0.5*sin(2*PI*440*t))':d=150:s=16000",
                        str(own / "Unit 4" / "lesson.m4a")], check=True)
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")
        with mock_env(UNISTUDENT_STT_BACKEND="fake"):
            run_json("recordings", "approve", "--course", course, "official/Unit 4/lesson.m4a")
            run_json("recordings", "transcribe", "--course", course, "official/Unit 4/lesson.m4a")
        transcript = (folders(course).wiki / "recordings" / "lesson" / "transcript.md").read_text("utf-8")
        self.assertIn("segment at 00:00:00", transcript)
        self.assertNotIn("segment at 00:01:00", transcript)  # inside the silence
        self.assertIn("segment at 00:02:20", transcript)


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

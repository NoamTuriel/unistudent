"""Token-friendly frame analysis (ticket 04): a separate, remembered opt-in with its own cost estimate."""
import json
import unittest
from pathlib import Path

from helpers import CourseTestCase, run, run_json, write

from test_recording_streams import HAS_FFMPEG, make_video


class FrameAnalysisChoice(CourseTestCase):
    def setUp(self):
        super().setUp()
        own = self.tmp / "own"
        write(own / "Unit 4" / "session 5.mp4", b"\x00" * 4096)
        self.course = self.tmp / "Macro"
        run("setup", self.course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")

    def test_frame_analysis_defaults_to_unset(self):
        est = run_json("recordings", "estimate", "--course", self.course)
        self.assertIsNone(est["frame_analysis"])

    def test_the_choice_is_remembered_per_course_like_recording_level(self):
        run_json("context", "--course", self.course, "--frame-analysis", "1")
        self.assertTrue(run_json("recordings", "estimate", "--course", self.course)["frame_analysis"])

        run_json("context", "--course", self.course, "--frame-analysis", "0")
        self.assertFalse(run_json("recordings", "estimate", "--course", self.course)["frame_analysis"])

    def test_frame_analysis_choice_does_not_affect_recording_level_or_vice_versa(self):
        run_json("context", "--course", self.course, "--recording-level", "3")
        run_json("context", "--course", self.course, "--frame-analysis", "1")
        self.assertTrue(run_json("recordings", "estimate", "--course", self.course)["frame_analysis"])
        saved = json.loads((self.course / ".unistudent" / "settings.json").read_text("utf-8"))
        self.assertEqual(saved["recording_level"], 3)
        self.assertIs(saved["frame_analysis"], True)

    def test_estimate_reports_zero_segments_when_duration_is_unknown(self):
        est = run_json("recordings", "estimate", "--course", self.course)
        self.assertEqual(est["frame_analysis_segments"], 0)


@unittest.skipUnless(HAS_FFMPEG, "ffmpeg not installed")
class FrameAnalysisEstimate(CourseTestCase):
    def test_estimate_counts_one_segment_per_minute_of_audio(self):
        own = self.tmp / "own"
        make_video(own / "Unit 4" / "session.mp4", seconds=130)
        course = self.tmp / "Macro"
        run_json("setup", course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")
        est = run_json("recordings", "estimate", "--course", course)
        # ceil(130 / 60) = 3 one-minute segments, one vision call each if frame analysis is on.
        self.assertEqual(est["frame_analysis_segments"], 3)

    def test_a_fractional_second_duration_is_not_undercounted(self):
        own = self.tmp / "own"
        # 120.5s crosses the 2-minute mark mid-second: 3 segments, not 2 (a truncate-then-divide bug undercounts).
        make_video(own / "Unit 4" / "session.mp4", seconds=120.5)
        course = self.tmp / "Macro"
        run_json("setup", course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")
        est = run_json("recordings", "estimate", "--course", course)
        self.assertEqual(est["frame_analysis_segments"], 3)


class RecordingSummarizerNeverAssumesFrameAnalysis(unittest.TestCase):
    """The gating lives in prose (the worker is an LLM agent, not code); this pins the wording down."""

    def test_the_worker_is_told_not_to_infer_the_opt_in_from_tool_availability(self):
        base = Path(__file__).resolve().parents[1] / "plugins" / "unistudent" / "scripts" / "unistudent"
        text = (base / "agents" / "recording-summarizer.md").read_text("utf-8")
        self.assertIn("never assume it's on just because a video-analysis tool happens to be installed", text)
        self.assertIn("Only if you were told it's on", text)

    def test_course_recordings_asks_frame_analysis_separately_from_recording_level(self):
        base = Path(__file__).resolve().parents[1] / "plugins" / "unistudent" / "scripts" / "unistudent"
        text = (base / "skills" / "course-recordings" / "SKILL.md").read_text("utf-8")
        self.assertIn("separate", text.lower())
        self.assertIn("--frame-analysis", text)
        self.assertIn("--recording-level", text)


if __name__ == "__main__":
    unittest.main()

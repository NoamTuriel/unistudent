"""Seam 1 (sync): recording streams in a listing → downloaded files → the Material folder."""
import json
import shutil
import subprocess
import unittest

from helpers import CourseTestCase, folders, run, run_json, write

HAS_FFMPEG = shutil.which("ffmpeg") is not None


def streams(path):
    """The kinds of stream in a media file, e.g. ["video", "audio"]."""
    return subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                           str(path)], capture_output=True, text=True).stdout.split()


def make_video(path, seconds=2):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc=duration={seconds}:size=160x120:rate=5",
                    "-f", "lavfi", "-i", f"sine=duration={seconds}", "-shortest", str(path)], check=True)
    return path


class StreamListing(CourseTestCase):
    """A course and a staged listing with one recording stream and one document."""

    def setUp(self):
        super().setUp()
        self.course = self.tmp / "Macro"
        run("setup", self.course, "--name", "Macro", "--language", "en", "--university", "openu")
        self.source = make_video(self.tmp / "cdn" / "stream.mp4")
        self.staged = self.tmp / "staged"
        self.staged.mkdir()
        self.listing = write(self.staged / "listing.json", json.dumps({"items": [
            {"url": "https://example.edu/rec/1", "name": "Session 5.mp4", "section": "Unit 4 recordings",
             "kind": "recording", "stream_url": str(self.source)},
            {"url": "https://example.edu/f/1", "name": "notes.txt", "section": "Unit 4", "file": "notes.txt"},
        ]}))
        write(self.staged / "notes.txt", "unit 4 notes")


@unittest.skipUnless(HAS_FFMPEG, "ffmpeg not installed")
class RecordingStreams(StreamListing):
    def test_streams_are_downloaded_then_ingested_like_any_file(self):
        fetched = run_json("recordings", "fetch", "--course", self.course, self.listing, self.staged)
        self.assertEqual(fetched["downloaded"], ["Session 5.mp4"])
        self.assertTrue((self.staged / "Session 5.mp4").exists())
        result = run_json("ingest", "--course", self.course, self.listing, self.staged)
        self.assertEqual(sorted(result["new"]), ["official/Unit 4/Session 5.mp4", "official/Unit 4/notes.txt"])
        self.assertEqual(result["recordings_available"], [])

    def test_audio_only_keeps_just_the_sound(self):
        run_json("recordings", "fetch", "--course", self.course, self.listing, self.staged, "--audio-only")
        self.assertEqual(streams(self.staged / "Session 5.m4a"), ["audio"])

    def test_a_failed_stream_is_reported_and_the_rest_continue(self):
        data = json.loads(self.listing.read_text("utf-8"))
        data["items"].insert(0, {"url": "https://example.edu/rec/0", "name": "Broken.mp4", "section": "Unit 4 recordings",
                                 "kind": "recording", "stream_url": str(self.tmp / "missing.m3u8")})
        self.listing.write_text(json.dumps(data), "utf-8")
        fetched = run_json("recordings", "fetch", "--course", self.course, self.listing, self.staged)
        self.assertEqual(fetched["downloaded"], ["Session 5.mp4"])
        self.assertEqual(fetched["failed"], ["Broken.mp4"])


class KeepVideoSetting(CourseTestCase):
    def test_keep_video_is_stored_and_read_like_the_other_recording_choices(self):
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--language", "en")
        self.assertIsNone(run_json("recordings", "estimate", "--course", course)["keep_video"])
        run_json("context", "--course", course, "--keep-video", "0")
        self.assertIs(run_json("recordings", "estimate", "--course", course)["keep_video"], False)
        run_json("context", "--course", course, "--keep-video", "1", "--frame-analysis", "0")
        self.assertIs(run_json("recordings", "estimate", "--course", course)["keep_video"], True)


@unittest.skipUnless(HAS_FFMPEG, "ffmpeg not installed")
class FetchFollowsTheRecordingChoices(StreamListing):
    def fetch(self, frame_analysis, keep_video):
        run_json("context", "--course", self.course, "--frame-analysis", frame_analysis, "--keep-video", keep_video)
        return run_json("recordings", "fetch", "--course", self.course, self.listing, self.staged)["downloaded"]

    def test_no_frame_analysis_and_no_video_kept_fetches_audio_only(self):
        self.assertEqual(self.fetch("0", "0"), ["Session 5.m4a"])
        self.assertEqual(streams(self.staged / "Session 5.m4a"), ["audio"])

    def test_frame_analysis_needs_the_video_even_when_it_is_not_kept(self):
        self.assertEqual(self.fetch("1", "0"), ["Session 5.mp4"])
        self.assertIn("video", streams(self.staged / "Session 5.mp4"))

    def test_a_kept_video_is_fetched_whole(self):
        self.assertEqual(self.fetch("0", "1"), ["Session 5.mp4"])

    def test_a_title_ending_in_a_dotted_date_keeps_its_year(self):
        data = json.loads(self.listing.read_text("utf-8"))
        data["items"][0]["name"] = "Lesson 3 12.10.2025"  # how the OpenU scan names a recording: title + date
        self.listing.write_text(json.dumps(data), "utf-8")
        self.assertEqual(self.fetch("0", "0"), ["Lesson 3 12.10.2025.m4a"])


@unittest.skipUnless(HAS_FFMPEG, "ffmpeg not installed")
class VideoReplacedAfterFrameAnalysis(CourseTestCase):
    def setUp(self):
        super().setUp()
        make_video(self.tmp / "own" / "Unit 4" / "session.mp4")
        self.course = self.tmp / "Macro"
        run_json("setup", self.course, "--name", "Macro", "--language", "en", "--import", self.tmp / "own",
                 "--tier", "official")
        self.recording = run_json("recordings", "list", "--course", self.course)["recordings"][0]
        self.file = folders(self.course).material / self.recording["path"]
        run_json("context", "--course", self.course, "--frame-analysis", "1", "--keep-video", "0")

    def analysis_done(self):  # what the recording-summarizer writes once its frame analysis is done
        write(folders(self.course).wiki / self.recording["wiki_folder"] / "recording-summary.md", "# Summary")

    def test_the_video_becomes_an_audio_only_copy_at_the_same_path_once_analysed(self):
        self.analysis_done()
        run_json("recordings", "audio-only", "--course", self.course, self.recording["path"])
        self.assertEqual(streams(self.file), ["audio"])  # same file name, so every time link still opens it
        self.assertEqual([r["path"] for r in run_json("recordings", "list", "--course", self.course)["recordings"]],
                         [self.recording["path"]])

    def test_a_video_replaced_by_its_sound_is_still_imported_once(self):
        self.analysis_done()
        run_json("recordings", "audio-only", "--course", self.course, self.recording["path"])
        self.assertEqual(run_json("import", "--course", self.course, self.tmp / "own", "--dry-run")["files"], 0)
        self.assertEqual(run_json("import", "--course", self.course, self.tmp / "own")["imported"], [])
        self.assertEqual(streams(self.file), ["audio"])

    def test_nothing_is_replaced_before_the_analysis_is_done(self):
        self.assertEqual(run("recordings", "audio-only", "--course", self.course, self.recording["path"])[0], 1)
        self.assertIn("video", streams(self.file))

    def test_a_video_the_student_keeps_is_never_replaced(self):
        self.analysis_done()
        run_json("context", "--course", self.course, "--keep-video", "1")
        self.assertEqual(run("recordings", "audio-only", "--course", self.course, self.recording["path"])[0], 1)
        self.assertIn("video", streams(self.file))


if __name__ == "__main__":
    unittest.main()

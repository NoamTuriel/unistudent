"""Seam 1 (sync): recording streams in a listing → downloaded files → the Material folder."""
import json
import shutil
import subprocess
import unittest

from helpers import CourseTestCase, run, run_json, write

HAS_FFMPEG = shutil.which("ffmpeg") is not None


def make_video(path, seconds=2):
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc=duration={seconds}:size=160x120:rate=5",
                    "-f", "lavfi", "-i", f"sine=duration={seconds}", "-shortest", str(path)], check=True)
    return path


@unittest.skipUnless(HAS_FFMPEG, "ffmpeg not installed")
class RecordingStreams(CourseTestCase):
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

    def test_streams_are_downloaded_then_ingested_like_any_file(self):
        fetched = run_json("recordings", "fetch", "--course", self.course, self.listing, self.staged)
        self.assertEqual(fetched["downloaded"], ["Session 5.mp4"])
        self.assertTrue((self.staged / "Session 5.mp4").exists())
        result = run_json("ingest", "--course", self.course, self.listing, self.staged)
        self.assertEqual(sorted(result["new"]), ["official/Unit 4/Session 5.mp4", "official/Unit 4/notes.txt"])
        self.assertEqual(result["recordings_available"], [])

    def test_audio_only_keeps_just_the_sound(self):
        run_json("recordings", "fetch", "--course", self.course, self.listing, self.staged, "--audio-only")
        audio = self.staged / "Session 5.m4a"
        self.assertTrue(audio.exists())
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0",
                                str(audio)], capture_output=True, text=True).stdout.split()
        self.assertEqual(probe, ["audio"])

    def test_a_failed_stream_is_reported_and_the_rest_continue(self):
        data = json.loads(self.listing.read_text("utf-8"))
        data["items"].insert(0, {"url": "https://example.edu/rec/0", "name": "Broken.mp4", "section": "Unit 4 recordings",
                                 "kind": "recording", "stream_url": str(self.tmp / "missing.m3u8")})
        self.listing.write_text(json.dumps(data), "utf-8")
        fetched = run_json("recordings", "fetch", "--course", self.course, self.listing, self.staged)
        self.assertEqual(fetched["downloaded"], ["Session 5.mp4"])
        self.assertEqual(fetched["failed"], ["Broken.mp4"])


if __name__ == "__main__":
    unittest.main()

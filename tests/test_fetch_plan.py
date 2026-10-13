"""Seam 1 (sync): the Fetch plan the student approves before anything downloads from the course site.

A university plugin (or the generated fallback) hands the Core a listing; `us fetch-plan` turns it into a
checklist the student reads and unticks, then into the approved listing the download and ingest use.
"""
import json
import re
from collections import namedtuple
from pathlib import Path
from unittest import mock

from helpers import CourseTestCase, folders, make_pdf, mock_env, run, run_json, write

Usage = namedtuple("Usage", "total used free")


def listing(*items):
    return {"course_site": "https://example.edu/course/123", "items": list(items)}


RECORDING = {"url": "https://example.edu/v/3", "name": "Session 3", "kind": "recording", "section": "Recordings",
             "seconds": 3600}
SLIDES = {"url": "https://example.edu/f/1", "name": "Unit 2 slides.pdf", "section": "Unit 2", "size": 3_000_000}
EXAM = {"url": "https://example.edu/f/2", "name": "Past exam 2024.pdf", "section": "Past exams", "size": 2_000_000,
        "unit_hint": "general"}
EXERCISES = {"url": "https://example.edu/f/3", "name": "Exercises.pdf", "section": "Units 1-3", "size": 1_000_000}
NOTES = {"url": "https://example.edu/f/4", "name": "notes.docx", "section": "Unit 4"}


def ticked_names(text):
    return [m.group(1) for m in re.finditer(r"^- \[x\] \d+\. .*?  \S+  (.+?)  \(", text, re.M)]


class FetchPlanShow(CourseTestCase):
    def setUp(self):
        super().setUp()
        self.course = self.tmp / "Macro"
        run("setup", self.course, "--name", "Macro", "--language", "en", "--university", "openu")
        self.listing = write(self.tmp / "listing.json",
                             json.dumps(listing(SLIDES, NOTES, RECORDING, EXERCISES, EXAM)))

    def show(self, free=10**12):
        with mock.patch("shutil.disk_usage", return_value=Usage(free * 2, free, free)):
            return run_json("fetch-plan", "show", "--course", self.course, self.listing)

    def test_the_checklist_lists_every_file_biggest_first_all_ticked_with_estimates_marked(self):
        plan = self.show()
        text = Path(plan["checklist"]).read_text("utf-8")
        self.assertEqual(ticked_names(text),
                         ["Session 3", "Unit 2 slides.pdf", "Past exam 2024.pdf", "Exercises.pdf", "notes.docx"])
        lines = [line for line in text.splitlines() if line.startswith("- [")]
        self.assertIn("~810 MB", lines[0])  # one hour at the documented 1.8 Mbit/s, estimated
        self.assertIn(".mp4", lines[0])
        self.assertIn("(Recordings)", lines[0])
        self.assertNotIn("~", "".join(lines[1:]))
        self.assertIn("size unknown", lines[-1])
        self.assertIn("plus 1 file of unknown size", text)
        self.assertTrue(Path(plan["checklist"]).resolve().is_relative_to((self.course / ".unistudent").resolve()))

    def test_totals_per_extension_free_space_and_a_rough_time(self):
        plan = self.show()
        self.assertEqual(plan["totals"][".pdf"]["bytes"], 6_000_000)
        self.assertEqual(plan["totals"][".pdf"]["files"], 3)
        self.assertEqual(plan["totals"][".mp4"]["bytes"], 810_000_000)
        self.assertTrue(plan["totals"][".mp4"]["estimated"])
        self.assertEqual(plan["totals"][".docx"]["unknown_size"], 1)
        self.assertEqual(plan["total_bytes"], 816_000_000)
        self.assertEqual(plan["unknown_size"], 1)
        self.assertEqual(plan["free_bytes"], 10**12)
        self.assertTrue(plan["fits"])
        self.assertTrue(plan["rough"])
        self.assertGreater(plan["hours"], 0)
        self.assertIn("rough", plan["summary"])

    def test_a_recording_titled_with_a_dotted_date_still_counts_as_mp4(self):
        dated = dict(RECORDING, url="https://example.edu/v/5", name="Session 5 - 12.10.2025")
        write(self.listing, json.dumps(listing(dated)))
        plan = self.show()
        self.assertEqual(list(plan["totals"]), [".mp4"])
        self.assertIn(".mp4", Path(plan["checklist"]).read_text("utf-8"))

    def test_a_plan_bigger_than_the_free_space_does_not_fit(self):
        plan = self.show(free=500_000_000)
        self.assertFalse(plan["fits"])
        self.assertIn("does not fit", plan["summary"])

    def test_files_whose_section_names_no_single_unit_are_named_for_the_unit_question(self):
        plan = self.show()
        self.assertEqual([i["name"] for i in plan["needs_unit"]], ["Exercises.pdf"])
        self.assertEqual(plan["needs_unit"][0]["number"], 4)

    def test_an_unticked_line_stays_unticked_and_leaves_the_totals(self):
        path = self.show()["checklist"]
        text = Path(path).read_text("utf-8")
        write(path, text.replace("- [x] 1.", "- [ ] 1."))
        plan = self.show()
        text = Path(path).read_text("utf-8")
        self.assertIn("- [ ] 1.", text)
        self.assertNotIn(".mp4", plan["totals"])
        self.assertEqual(plan["total_bytes"], 6_000_000)

    def test_a_new_listing_starts_a_new_plan_with_everything_ticked(self):
        path = self.show()["checklist"]
        write(path, Path(path).read_text("utf-8").replace("- [x]", "- [ ]"))
        write(self.listing, json.dumps(listing(SLIDES, EXAM)))
        text = Path(self.show()["checklist"]).read_text("utf-8")
        self.assertEqual(ticked_names(text), ["Unit 2 slides.pdf", "Past exam 2024.pdf"])


class FetchPlanApply(CourseTestCase):
    def setUp(self):
        super().setUp()
        self.course = self.tmp / "Macro"
        run("setup", self.course, "--name", "Macro", "--language", "en", "--university", "openu")
        self.staged = self.tmp / "staged"

    def plan(self, *items):
        path = write(self.tmp / "listing.json", json.dumps(listing(*items)))
        return path, run_json("fetch-plan", "show", "--course", self.course, path)["checklist"]

    def test_unticked_files_are_left_out_and_unit_answers_become_hints(self):
        summary = {"url": "https://example.edu/f/5", "name": "Summary.pdf", "section": "Extras", "size": 500_000}
        path, checklist = self.plan(SLIDES, NOTES, EXERCISES, summary)
        # 1 slides, 2 exercises, 3 summary, 4 notes (unknown size, last)
        write(checklist, Path(checklist).read_text("utf-8").replace("- [x] 4.", "- [ ] 4."))
        result = run_json("fetch-plan", "apply", "--course", self.course, path, "--unit", "2=unknown", "3=3")
        approved = json.loads(Path(result["listing"]).read_text("utf-8"))
        by_name = {i["name"]: i for i in approved["items"]}
        self.assertEqual(sorted(by_name), ["Exercises.pdf", "Summary.pdf", "Unit 2 slides.pdf"])
        self.assertNotIn("unit_hint", by_name["Exercises.pdf"])
        self.assertEqual(by_name["Summary.pdf"]["unit_hint"], 3)

        for name in ("Unit 2 slides.pdf", "Exercises.pdf", "Summary.pdf"):
            make_pdf(self.staged / name, [name])
            by_name[name]["file"] = name
        write(result["listing"], json.dumps(approved))
        ingested = run_json("ingest", "--course", self.course, result["listing"], self.staged)
        self.assertEqual(ingested["unsorted"], ["official/Unsorted/Exercises.pdf"])
        self.assertIn("official/Unit 3/Summary.pdf", ingested["new"])
        self.assertTrue((folders(self.course).wiki / "sources" / "unsorted" / "Exercises.md").is_file())

    def test_ticked_recordings_are_approved_for_transcription_once_downloaded(self):
        run("context", "--course", self.course, "--recording-level", "3")
        other = dict(RECORDING, url="https://example.edu/v/4", name="Session 4")
        path, checklist = self.plan(RECORDING, other)
        write(checklist, Path(checklist).read_text("utf-8").replace("- [x] 2.", "- [ ] 2."))
        result = run_json("fetch-plan", "apply", "--course", self.course, path)
        approved = json.loads(Path(result["listing"]).read_text("utf-8"))
        self.assertEqual([i["name"] for i in approved["items"]], ["Session 3"])
        approved["items"][0].update(file="Session 3.mp4", name="Session 3.mp4")  # what `recordings fetch` does
        write(result["listing"], json.dumps(approved))
        write(self.staged / "Session 3.mp4", b"\x00" * 4096)
        ingested = run_json("ingest", "--course", self.course, result["listing"], self.staged)
        rec = ingested["new"][0]
        with mock_env(UNISTUDENT_STT_BACKEND="fake"):
            run_json("recordings", "transcribe", "--course", self.course, rec)

    def test_recordings_are_not_approved_when_the_student_chose_no_transcripts(self):
        run("context", "--course", self.course, "--recording-level", "1")
        path, _ = self.plan(RECORDING)
        result = run_json("fetch-plan", "apply", "--course", self.course, path)
        approved = json.loads(Path(result["listing"]).read_text("utf-8"))
        self.assertNotIn("transcribe", approved["items"][0])

    def test_apply_needs_a_shown_plan(self):
        path = write(self.tmp / "listing.json", json.dumps(listing(SLIDES)))
        code, out = run("fetch-plan", "apply", "--course", self.course, path)
        self.assertEqual(code, 1)
        self.assertIn("fetch-plan show", out)


class FetchPlanStatus(CourseTestCase):
    """Fixture state: both documents in, both recordings downloaded, one of them transcribed."""

    def setUp(self):
        super().setUp()
        self.course = self.tmp / "Macro"
        run("setup", self.course, "--name", "Macro", "--language", "en", "--university", "openu")
        run("context", "--course", self.course, "--recording-level", "3")
        other = dict(RECORDING, url="https://example.edu/v/4", name="Session 4")
        path = write(self.tmp / "listing.json", json.dumps(listing(SLIDES, EXAM, RECORDING, other)))
        run_json("fetch-plan", "show", "--course", self.course, path)
        approved_path = run_json("fetch-plan", "apply", "--course", self.course, path)["listing"]
        approved = json.loads(Path(approved_path).read_text("utf-8"))
        staged = self.tmp / "staged"
        for item in approved["items"]:
            name = item["name"] + (".mp4" if item.get("kind") == "recording" else "")
            item.update(file=name, name=name)
            if name.endswith(".pdf"):
                make_pdf(staged / name, [name])
            else:
                write(staged / name, b"\x00" * 4096)
        write(approved_path, json.dumps(approved))
        new = run_json("ingest", "--course", self.course, approved_path, staged)["new"]
        self._stt = mock_env(UNISTUDENT_STT_BACKEND="fake")
        self._stt.__enter__()
        run_json("recordings", "transcribe", "--course", self.course, next(r for r in new if "Session 3" in r))

    def tearDown(self):
        self._stt.__exit__(None, None, None)
        super().tearDown()

    def test_counts_and_the_progress_box(self):
        status = run_json("fetch-plan", "status", "--course", self.course)
        self.assertEqual((status["documents"]["done"], status["documents"]["total"]), (2, 2))
        self.assertEqual(status["recordings"], {"downloaded": 2, "transcribed": 1, "summarised": 0, "total": 2})
        box = status["box"]
        self.assertTrue(box.isascii())
        self.assertIn("KEEP THE COMPUTER ON, PLUGGED IN AND AWAKE", box)
        self.assertIn("KEEP THIS APP AND CHROME OPEN", box)
        self.assertIn("2 of 2", box)
        self.assertTrue(box.startswith("+") and box.rstrip().endswith("+"))
        self.assertEqual(len({len(line) for line in box.splitlines()}), 1)  # a closed box

    def test_the_time_left_is_rough_until_the_machine_is_benchmarked(self):
        self.assertIn("rough", run_json("fetch-plan", "status", "--course", self.course)["box"].lower())
        write(self.home / "benchmark.json", json.dumps({"backend": "fake", "realtime_factor": 0.25}))
        status = run_json("fetch-plan", "status", "--course", self.course)
        self.assertNotIn("rough", status["box"].lower())
        self.assertEqual(status["hours"], 0.25)  # one hour of recording left at 0.25

    def test_nothing_to_download_is_a_status_too(self):
        course = self.tmp / "Other"
        run("setup", course, "--name", "Other", "--language", "en", "--university", "none")
        status = run_json("fetch-plan", "status", "--course", course)
        self.assertIsNone(status["box"])
        self.assertEqual(status["documents"], {"done": 0, "total": 0})
        self.assertEqual(status["recordings"]["total"], 0)
        self.assertIn("Nothing to download", status["summary"])


class StatusTimeLeft(CourseTestCase):
    """Recordings whose length the site did not show: measured once downloaded, a rough guess before."""

    def setUp(self):
        super().setUp()
        self.course = self.tmp / "Macro"
        run("setup", self.course, "--name", "Macro", "--language", "en", "--university", "openu")
        run("context", "--course", self.course, "--recording-level", "3")
        write(self.home / "benchmark.json", json.dumps({"backend": "fake", "realtime_factor": 0.25}))
        untimed = {k: v for k, v in RECORDING.items() if k != "seconds"}
        path = write(self.tmp / "listing.json", json.dumps(listing(untimed)))
        run_json("fetch-plan", "show", "--course", self.course, path)
        self.approved = run_json("fetch-plan", "apply", "--course", self.course, path)["listing"]

    def test_a_recording_of_unknown_length_makes_the_time_rough_not_zero(self):
        box = run_json("fetch-plan", "status", "--course", self.course)["box"]
        self.assertIn("ROUGH", box)
        self.assertNotIn("1 MINUTES", box)
        self.assertIn("1 RECORDING OF UNKNOWN LENGTH", box)  # named, not counted as zero minutes

    def test_a_downloaded_recording_counts_its_real_length_measured_once(self):
        data = json.loads(Path(self.approved).read_text("utf-8"))
        data["items"][0].update(file="Session 3.mp4", name="Session 3.mp4")
        write(self.approved, json.dumps(data))
        write(self.tmp / "staged" / "Session 3.mp4", b"\x00" * 4096)
        run_json("ingest", "--course", self.course, self.approved, self.tmp / "staged")
        with mock.patch("unistudent.recordings.duration", return_value=3600.0) as probe:
            status = run_json("fetch-plan", "status", "--course", self.course)
            run_json("fetch-plan", "status", "--course", self.course)
        self.assertEqual(status["hours"], 0.25)  # one hour of audio at 0.25
        self.assertFalse(status["rough"])
        self.assertEqual(probe.call_count, 1)  # cached, not probed on every status


class StatusWithoutASite(CourseTestCase):
    """A course fed from the student's own folder has no Fetch plan; the run still shows the same box."""

    def test_own_folder_files_are_counted_and_approved_recordings_wait_for_their_transcript(self):
        own = self.tmp / "own"
        write(own / "Unit 1" / "slides.txt", "GDP is output.")
        write(own / "Lesson 1.mp4", b"\x00" * 4096)
        course = self.tmp / "Linear algebra"
        run("setup", course, "--name", "Linear algebra", "--language", "en", "--university", "none",
            "--import", own, "--tier", "official")
        recording = run_json("recordings", "list", "--course", course)["recordings"][0]["path"]
        run_json("recordings", "approve", "--course", course, recording)
        status = run_json("fetch-plan", "status", "--course", course)
        self.assertEqual((status["documents"]["done"], status["documents"]["total"]), (1, 1))
        self.assertEqual(status["recordings"], {"downloaded": 1, "transcribed": 0, "summarised": 0, "total": 1})
        self.assertIn("KEEP THE COMPUTER ON, PLUGGED IN AND AWAKE", status["box"])
        self.assertIn("1 of 1 downloaded", status["box"])
        self.assertNotIn("CHROME", status["box"])  # no course site: nothing runs in the browser

    def test_a_recording_transcribed_without_a_tick_never_overflows_the_bar(self):
        write(self.tmp / "own" / "Lesson 1.mp4", b"\x00" * 4096)
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--language", "en", "--university", "none",
            "--import", self.tmp / "own", "--tier", "official")
        recording = run_json("recordings", "list", "--course", course)["recordings"][0]["path"]
        run_json("recordings", "approve", "--course", course, recording)
        with mock_env(UNISTUDENT_STT_BACKEND="fake"):
            run_json("recordings", "transcribe", "--course", course, recording)  # no longer waiting: not "wanted"
        box = run_json("fetch-plan", "status", "--course", course)["box"]
        self.assertIn("Recordings  [" + "#" * 20 + "]  1 of 1", box)  # full, and no wider than the other bar


class ImportDryRun(CourseTestCase):
    def test_dry_run_counts_and_sizes_without_copying(self):
        own = self.tmp / "own"
        write(own / "Unit 1" / "a.pdf", b"x" * 100)
        write(own / "b.docx", b"x" * 250)
        course = self.tmp / "Macro"
        run("setup", course, "--name", "Macro", "--language", "en")
        result = run_json("import", "--course", course, own, "--dry-run")
        self.assertEqual((result["files"], result["bytes"]), (2, 350))
        self.assertIn("2 files", result["summary"])
        self.assertEqual(run_json("manifest", "--course", course)["files"], {})
        self.assertEqual([p for p in folders(course).material.rglob("*") if p.is_file()], [])


if __name__ == "__main__":
    import unittest
    unittest.main()

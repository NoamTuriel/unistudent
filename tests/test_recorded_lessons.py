"""Ticket 22: whole-class lessons live in Recorded lessons, outside every unit; the recordings roadmap is slim."""
import unittest

from helpers import CourseTestCase, folders, mock_env, run, run_json, write

LESSON = "official/Unsorted/lesson 9.mp4"


class RecordedLessons(CourseTestCase):
    def setUp(self):
        super().setUp()
        self.course = self.tmp / "Macro"
        own = self.tmp / "own"
        write(own / "Unit 4" / "question 1.mp4", b"\x00" * 64)
        write(own / "lesson 9.mp4", b"\x00" * 64)
        run_json("setup", self.course, "--name", "Macro", "--language", "en", "--import", own, "--tier", "official")
        self.f = folders(self.course)
        self.lesson = self.f.wiki / "recordings" / "lesson 9"
        self.question = self.f.wiki / "recordings" / "question 1"
        with mock_env(UNISTUDENT_STT_BACKEND="fake"):
            for rel in (LESSON, "official/Unit 4/question 1.mp4"):
                run_json("recordings", "approve", "--course", self.course, rel)
                run_json("recordings", "transcribe", "--course", self.course, rel)
        write(self.lesson / "toc.md", "Sources: [transcript](transcript.md)\n\n| Time | Until | Type | What happens | Topic |\n|---|---|---|---|---|\n"
                                      "| [00:00:00](transcript.md#000000) | 00:01:41 | explanation | Intro | Unit 7 |\n\n"
                                      "## Solved in this recording\n\n- question 3 (00:40:00)\n")
        write(self.lesson / "summary.md", "Lesson 9: a lesson about units 7-9.\n\nSources: [transcript](transcript.md)\n\n"
                                          "## Announcements\n\nHomework due Sunday.\n\n## Summary\n\nLong paragraph.\n")
        write(self.question / "summary.md", "Solution of question 1, unit 4.\n\nSources: [transcript](transcript.md)\n")

    def test_a_lesson_goes_to_recorded_lessons_and_is_no_longer_unsorted(self):
        self.assertIn(LESSON, run_json("unsorted", "--course", self.course)["files"])
        run_json("assign", LESSON, "lessons", "--course", self.course)
        self.assertTrue((self.f.material / "official" / "Recorded lessons" / "lesson 9.mp4").is_file())
        self.assertEqual(run_json("unsorted", "--course", self.course)["files"], [])

    def test_a_lesson_roadmap_sits_in_recorded_lessons_and_the_unit_keeps_only_its_solutions(self):
        run_json("assign", LESSON, "lessons", "--course", self.course)
        run_json("wiki", "build", "--course", self.course)
        self.assertEqual(sorted(p.name for p in self.f.study.iterdir()), ["Recorded lessons", "Unit 4"])
        lessons = (self.f.study / "Recorded lessons" / "Recordings roadmap.md").read_text("utf-8")
        unit4 = (self.f.study / "Unit 4" / "Recordings roadmap.md").read_text("utf-8")
        self.assertIn("Lesson 9", lessons)
        self.assertNotIn("Lesson 9", unit4)
        self.assertIn("question 1", unit4)

    def test_the_roadmap_is_slim_and_keeps_the_announcements(self):
        run_json("assign", LESSON, "lessons", "--course", self.course)
        run_json("wiki", "build", "--course", self.course)
        text = (self.f.study / "Recorded lessons" / "Recordings roadmap.md").read_text("utf-8")
        self.assertIn("Homework due Sunday.", text)
        self.assertIn("00:00:00", text)
        self.assertEqual(text.count("Lesson 9: a lesson about units 7-9."), 1)
        for gone in ("Sources:", "Solved in this recording", "Long paragraph."):
            self.assertNotIn(gone, text)
        self.assertEqual(text.count("[recording]("), 1)
        self.assertNotIn("Type", text)
        self.assertNotIn("explanation", text)
        self.assertIn("Intro", text)

    def test_a_lesson_with_no_roadmap_entry_is_reported_until_the_wiki_build_writes_it(self):
        run_json("assign", LESSON, "lessons", "--course", self.course)
        lesson = "official/Recorded lessons/lesson 9.mp4"
        self.assertEqual(run_json("study", "changes", "--course", self.course, "--unit", "8")["lessons_without_roadmap"], [lesson])
        run_json("wiki", "build", "--course", self.course)
        self.assertEqual(run_json("study", "changes", "--course", self.course, "--unit", "8")["lessons_without_roadmap"], [])

    def test_only_a_recording_can_be_assigned_to_recorded_lessons(self):
        write(self.course / "1-inbox" / "notes.txt", "notes")
        run_json("add", "--course", self.course)
        code, out = run("assign", "added/Unsorted/notes.txt", "lessons", "--course", self.course)
        self.assertEqual(code, 1)
        self.assertIn("recording", out)

    def test_the_wiki_check_wants_a_summary_to_open_with_its_one_line_description(self):
        self.assertEqual(self.wiki_problems(), [])
        write(self.lesson / "summary.md", "Sources: [transcript](transcript.md)\n\n## Announcements\n\nNone.\n")
        self.assertEqual(self.wiki_problems(), ["no-description"])
        write(self.lesson / "summary.md", "## Summary\n\nText.\n\nSources: [transcript](transcript.md)\n")
        self.assertEqual(self.wiki_problems(), ["no-description"])

    def test_a_new_table_of_contents_marks_its_unit_page_stale_once(self):  # ticket 31
        run_json("assign", LESSON, "lessons", "--course", self.course)
        write(self.lesson / "summary.md", "Lesson 9: a lesson about units 3-4.\n\nSources: [transcript](transcript.md)\n")
        self.assertEqual(run_json("wiki", "build", "--course", self.course)["units_touched"], ["unit-04"])
        self.assertEqual(run_json("wiki", "build", "--course", self.course)["units_touched"], [])
        write(self.question / "toc.md", "Sources: [transcript](transcript.md)\n\n| Time | Until | Type | What happens | Topic |\n"
                                        "|---|---|---|---|---|\n| [00:00:00](transcript.md#000000) | 00:05:00 | solution | Q1 | Unit 4 |\n")
        self.assertEqual(run_json("wiki", "build", "--course", self.course)["units_touched"], ["unit-04"])

    def wiki_problems(self):
        run_json("wiki", "build", "--course", self.course)
        return [p["kind"] for p in run_json("wiki", "check", "--course", self.course)["problems"]]


if __name__ == "__main__":
    unittest.main()

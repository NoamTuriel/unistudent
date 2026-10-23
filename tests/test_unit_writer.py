"""Seam 2 (Wiki build): what the Wiki hands a unit writer, and when it hands it a unit."""
import json
import unittest

from helpers import CourseTestCase, folders, mock_env, run_json, write

LESSON = "official/Recorded lessons/lesson 9.mp4"
TOC = ("Sources: [transcript](transcript.md)\n\n| Time | Until | Type | What happens | Topic |\n|---|---|---|---|---|\n"
       "| [00:00:00](transcript.md#000000) | 00:01:41 | explanation | Intro | Demand |\n\n"
       "## Solved in this recording\n\n- question 3 (00:40:00)\n")


class UnitWriter(CourseTestCase):
    def setUp(self):
        super().setUp()
        self.course = self.tmp / "Micro"
        own = self.tmp / "own"
        write(own / "Unit 3" / "demand.txt", "Demand curves slope down. Long enough to be a page of text.")
        write(own / "Unit 4" / "supply.txt", "Supply curves slope up. Long enough to be a page of text.")
        write(own / "lesson 9.mp4", b"\x00" * 64)
        run_json("setup", self.course, "--name", "Micro", "--language", "en", "--import", own, "--tier", "official")
        run_json("assign", "official/Unsorted/lesson 9.mp4", "lessons", "--course", self.course)
        self.f = folders(self.course)
        self.lesson = self.f.wiki / "recordings" / "lesson 9"
        with mock_env(UNISTUDENT_STT_BACKEND="fake"):
            run_json("recordings", "approve", "--course", self.course, LESSON)
            run_json("recordings", "transcribe", "--course", self.course, LESSON)
        write(self.lesson / "toc.md", TOC)
        self.summary("units 3-4")
        run_json("wiki", "build", "--course", self.course)

    def summary(self, units):
        write(self.lesson / "recording-summary.md", f"Lesson 9: a lesson about {units}.\n\n"
                                                    "Sources: [transcript](transcript.md)\n\n## Summary\n\nDemand.\n")

    def context(self, unit):
        return run_json("unit", "context", unit, "--course", self.course)["summary"]

    def test_unit_context_hands_the_writer_its_whole_starting_set(self):
        unit4 = self.f.wiki / "units" / "unit-04.md"
        write(unit4, unit4.read_text("utf-8") + "\n## Approved methods\n\n- Supply shift. Sources: [s](../sources/unit-04/supply.md)\n"
                     "\n## Notation\n\n- S: supply. Sources: [s](../sources/unit-04/supply.md)\n"
                     "\n## Assumptions\n\n- Ceteris paribus. Sources: [s](../sources/unit-04/supply.md)\n")
        write(self.f.wiki / "glossary.md", "# Glossary\n\n### Demand (D)\nHow much buyers want. Sources: [d](sources/unit-03/demand.md)\n\n"
                                           "### Supply (S)\nHow much sellers offer. Sources: [s](sources/unit-04/supply.md)\n")
        write(self.f.wiki / "question-bank.md", "# Question bank\n\n### Shift demand  #unit-03/shifts\n- Where: [d](sources/unit-03/demand.md)\n\n"
                                                "### Shift supply  #unit-04/shifts\n- Where: [s](sources/unit-04/supply.md)\n")
        write(self.course / ".unistudent" / "before-test" / "index.json", json.dumps([
            {"exam": "Exam 2024a", "q": 2, "unit": 3, "topic": "demand", "skill": "draw a shift", "points": 10},
            {"exam": "Exam 2024a", "q": 5, "unit": 4, "topic": "supply", "skill": "compute", "points": 15}]))
        text = self.context("3")
        self.assertNotIn("Demand curves slope down", text)  # the source pages are listed, not copied
        for present in ("../sources/unit-03/demand.md", "Grounding rule",  # the unit page, the course rules
                        "### Demand (D)", "### Shift demand", "Exam 2024a", "draw a shift",
                        "Intro | Demand", "Lesson 9: a lesson about units 3-4.",
                        "Supply shift", "S: supply"):  # unit 4's methods and notation
            self.assertIn(present, text)
        for absent in ("### Supply (S)", "### Shift supply", "compute", "Ceteris paribus"):  # another unit's rows, assumptions
            self.assertNotIn(absent, text)

    def touched(self):
        return run_json("wiki", "build", "--course", self.course)["units_touched"]

    def test_a_unit_is_touched_when_the_lessons_covering_it_change(self):
        self.assertEqual(self.touched(), [])
        self.summary("unit 3")  # the lesson no longer covers unit 4: its writer must take that lesson out
        self.assertEqual(self.touched(), ["unit-04"])
        self.summary("units 3 and 7")  # unit 7 has no files: the lesson gives it a page, and its writer the unit
        self.assertEqual(self.touched(), ["unit-07"])
        self.summary("units 3 and 7, with corrections")  # the same lessons: nothing to hand on
        self.assertEqual(self.touched(), [])

    def test_study_changes_sees_covering_lessons_and_the_units_questions(self):
        changes = lambda: run_json("study", "changes", "--unit", "3", "--course", self.course)
        run_json("study", "mark-built", "--unit", "3", "--course", self.course)
        self.assertEqual(changes()["changed"], [])
        self.summary("units 3-4, corrected from the board")
        write(self.lesson / "toc.md", TOC.replace("Intro", "Opening"))
        write(self.f.wiki / "question-bank.md", "# Question bank\n\n### Shift demand  #unit-03/shifts\n- Where: [d](sources/unit-03/demand.md)\n")
        self.assertEqual(changes()["changed"], ["recordings/lesson 9/recording-summary.md", "recordings/lesson 9/toc.md"])
        self.assertEqual(changes()["new"], ["question-bank.md"])
        run_json("study", "mark-built", "--unit", "3", "--course", self.course)
        write(self.f.wiki / "question-bank.md", "# Question bank\n\n### Shift demand  #unit-03/shifts\n- Where: [d](sources/unit-03/demand.md)\n\n"
                                                "### Shift supply  #unit-04/shifts\n- Where: [s](sources/unit-04/supply.md)\n")
        self.assertEqual(changes()["changed"], [])  # another unit's question
        packs = self.course / ".unistudent" / "studypacks.json"
        data = json.loads(packs.read_text("utf-8"))
        sources = data["unit-03"]["sources"]
        for key in [k for k in sources if k.startswith("recordings/")]:
            del sources[key]
        sources["recordings/lesson 9/summary.md"] = "processed"  # how a pack built by an older version recorded it
        write(packs, json.dumps(data))
        self.assertEqual([changes()[k] for k in ("new", "changed", "removed")], [[], [], []])


if __name__ == "__main__":
    unittest.main()

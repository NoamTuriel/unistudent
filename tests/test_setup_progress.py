"""Setup progress + resume (ticket 03): stop after any stage, resume at the next one, answers intact."""
import unittest

from helpers import CourseTestCase, run_json


class SetupProgress(CourseTestCase):
    def test_a_fresh_course_has_no_progress(self):
        status = run_json("setup-progress", "status", "--course-name", "Macro")
        self.assertIsNone(status["stage"])
        self.assertEqual(status["next_stage"], "university")

    def test_each_stage_resumes_at_the_next_one_with_answers_intact(self):
        stages_and_answers = [
            ("university", {"university": "Bar-Ilan"}),
            ("course", {"course_name": "Macro"}),
            ("path", {"path": "/tmp/Macro"}),
            ("format", {"format": "obsidian"}),
            ("fetch", {"origin_mode": "own-folder"}),
            ("sort", {}),
            ("recordings", {"recording_level": "1"}),
            ("analyze", {}),
        ]
        for stage, answers in stages_and_answers:
            args = ["setup-progress", "advance", "--course-name", "Macro", "--stage", stage]
            for k, v in answers.items():
                args += ["--answer", f"{k}={v}"]
            run_json(*args)
            status = run_json("setup-progress", "status", "--course-name", "Macro")
            self.assertEqual(status["stage"], stage)
            for k, v in answers.items():
                self.assertEqual(status["answers"][k], v)
        # Prior stages' answers all still there after the last one.
        final = run_json("setup-progress", "status", "--course-name", "Macro")
        self.assertEqual(final["answers"]["university"], "Bar-Ilan")
        self.assertEqual(final["answers"]["path"], "/tmp/Macro")
        self.assertEqual(final["next_stage"], "capabilities")

    def test_finishing_the_last_stage_clears_progress(self):
        run_json("setup-progress", "advance", "--course-name", "Macro", "--stage", "university")
        result = run_json("setup-progress", "advance", "--course-name", "Macro", "--stage", "capabilities")
        self.assertIn("complete", result["summary"])
        status = run_json("setup-progress", "status", "--course-name", "Macro")
        self.assertIsNone(status["stage"])

    def test_list_surfaces_every_incomplete_setup(self):
        run_json("setup-progress", "advance", "--course-name", "Macro", "--stage", "path")
        run_json("setup-progress", "advance", "--course-name", "Stats", "--stage", "university")
        names = {e["course_name"] for e in run_json("setup-progress", "list")["in_progress"]}
        self.assertEqual(names, {"Macro", "Stats"})

    def test_clear_removes_progress(self):
        run_json("setup-progress", "advance", "--course-name", "Macro", "--stage", "university")
        run_json("setup-progress", "clear", "--course-name", "Macro")
        status = run_json("setup-progress", "status", "--course-name", "Macro")
        self.assertIsNone(status["stage"])


if __name__ == "__main__":
    unittest.main()

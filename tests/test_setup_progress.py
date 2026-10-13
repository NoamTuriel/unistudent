"""Setup progress + resume (ticket 03): stop after any stage, resume at the next one, answers intact."""
import json
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
            ("material", {"origin_mode": "own-folder"}),
            ("recordings", {"recording_level": "1"}),
            ("installs", {}),
            ("plan", {}),
            ("run", {}),
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

    def test_the_stages_follow_the_question_block_then_the_plan_then_the_run(self):
        order = [run_json("setup-progress", "status", "--course-name", "Macro")["next_stage"]]
        while order[-1] != "capabilities" and len(order) < 20:  # the last stage clears progress, so stop before it
            run_json("setup-progress", "advance", "--course-name", "Macro", "--stage", order[-1])
            order.append(run_json("setup-progress", "status", "--course-name", "Macro")["next_stage"])
        self.assertEqual(order, ["university", "course", "language", "path", "format", "material", "recordings",
                                 "installs", "plan", "run", "capabilities"])

    def test_a_setup_started_on_an_older_version_resumes_at_the_matching_new_stage(self):
        # Stages recorded by older versions: what was done then -> what comes next now.
        for old, resume in [("fetch", "recordings"), ("sort", "recordings"), ("analyze", "capabilities"),
                            ("fetch-and-organize", "installs")]:
            progress = self.home / "setup-progress" / "Macro.json"
            progress.parent.mkdir(parents=True, exist_ok=True)
            progress.write_text(json.dumps({"stage": old, "answers": {"university": "openu"}}), "utf-8")
            status = run_json("setup-progress", "status", "--course-name", "Macro")
            self.assertEqual(status["next_stage"], resume, old)
            self.assertEqual(status["answers"]["university"], "openu")

    def test_an_older_setup_names_the_answers_step_7_still_needs(self):
        progress = self.home / "setup-progress" / "Macro.json"
        progress.parent.mkdir(parents=True, exist_ok=True)
        for old, missing in [("fetch-and-organize", ["source", "transcribe", "frame_analysis", "keep_video"]),
                             ("fetch", ["source"]), ("analyze", [])]:  # analyze: step 7 is long done
            progress.write_text(json.dumps({"stage": old, "answers": {"university": "openu"}}), "utf-8")
            self.assertEqual(run_json("setup-progress", "status", "--course-name", "Macro")["missing_answers"],
                             missing, old)
        run_json("setup-progress", "advance", "--course-name", "Macro", "--stage", "recordings",
                 "--answer", "source=own", "transcribe=no", "frame_analysis=no", "keep_video=no")
        self.assertEqual(run_json("setup-progress", "status", "--course-name", "Macro")["missing_answers"], [])

    def test_an_old_stage_name_is_still_accepted_and_recorded_as_the_new_one(self):
        run_json("setup-progress", "advance", "--course-name", "Macro", "--stage", "analyze")
        status = run_json("setup-progress", "status", "--course-name", "Macro")
        self.assertEqual((status["stage"], status["next_stage"]), ("run", "capabilities"))

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

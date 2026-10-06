"""Setup flow: the course-setup commands in the skill's order on a fixture course, plus static checks on SKILL.md.

Deterministic only. What the AI says and asks is not testable here (see evals/); this keeps the
commands the skill tells it to run real, and the stage bookkeeping complete.
"""
import argparse
import json
import re
import unittest
from pathlib import Path

from helpers import CourseTestCase, folders, run, run_json, write
from unistudent import cli

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "plugins" / "unistudent" / "scripts" / "unistudent" / "skills"
SETUP = CORE / "course-setup" / "SKILL.md"
ALL_SKILLS = sorted(ROOT.glob("plugins/*/skills/*/SKILL.md")) + sorted(CORE.glob("*/SKILL.md"))
STAGES = ["university", "course", "language", "path", "format", "fetch", "sort", "recordings", "analyze", "capabilities"]


def subparsers(parser):
    return next((a.choices for a in parser._actions if isinstance(a, argparse._SubParsersAction)), None)


def us_invocations(text):
    """Yield (command words, options) for each `us ...` inline code span that names a real-looking command."""
    for span in re.findall(r"`us ([a-z][^`]*)`", text):
        words = []
        for tok in span.split():
            if not re.fullmatch(r"[a-z][a-z-]*", tok):
                break
            words.append(tok)
        yield words, re.findall(r"(?<![\w-])--[a-z][a-z-]*", span)


class SetupFlow(CourseTestCase):
    def test_the_setup_commands_run_in_order_on_a_fixture_course(self):
        folder = self.tmp / "Macro"
        own = self.tmp / "mine"
        write(own / "Unit 1 - intro" / "slides.txt", "GDP is output.")
        write(own / "past exam.txt", "Question 1")
        name = ["--course-name", "Macro"]
        self.assertEqual(run_json("setup-progress", "status", *name)["next_stage"], "university")
        run_json("university", "save", "--university", "Test U", "--url", "https://example.invalid", "--organizing", "by unit")
        self.assertTrue(run_json("university", "status", "--university", "Test U")["generated"])
        run_json("setup-progress", "advance", *name, "--stage", "university", "--answer", "university=Test U")
        self.assertEqual(run_json("plugins", "recommend", "--university", "Test U")["plugins"], [])
        run_json("setup-progress", "advance", *name, "--stage", "course")
        run_json("setup-progress", "advance", *name, "--stage", "language", "--answer", "language=en")
        run_json("setup-progress", "advance", *name, "--stage", "path", "--answer", f"path={folder}")
        run_json("setup-progress", "advance", *name, "--stage", "format", "--answer", "format=markdown")
        run_json("setup", folder, "--name", "Macro", "--format", "markdown", "--language", "en",
                 "--import", own, "--tier", "official")
        course = ["--course", folder]
        for f in run_json("unsorted", *course).get("files", []):
            run_json("assign", f["path"] if isinstance(f, dict) else f, "general", *course)
        self.assertIn("backend_installed", run_json("recordings", "estimate", *course))
        run_json("context", "--recording-level", "1", "--exam-date", "2030-01-01", *course)
        for stage in ("fetch", "sort", "recordings"):
            run_json("setup-progress", "advance", *name, "--stage", stage)
        run_json("setup-progress", "advance", *name, "--stage", "analyze")
        self.assertEqual(run_json("setup-progress", "status", *name)["next_stage"], "capabilities")
        self.assertIn("complete", run_json("setup-progress", "advance", *name, "--stage", "capabilities")["summary"])
        self.assertIsNone(run_json("setup-progress", "status", *name)["stage"])
        self.assertTrue(folders(folder).inbox.is_dir())
        self.assertTrue((folder / "README.md").is_file())
        self.assertEqual(run("wiki", "check", *course)[0], 0)

    def test_a_leftover_course_skill_setting_is_accepted_and_ignored(self):
        folder = self.tmp / "Course"
        run_json("setup", folder, "--name", "Course", "--language", "en")
        settings = folder / ".unistudent" / "settings.json"
        settings.write_text(json.dumps({**json.loads(settings.read_text("utf-8")), "course_skill": "old"}), "utf-8")
        run_json("setup", folder, "--name", "Course", "--language", "en")
        self.assertNotIn("course_skill", settings.read_text("utf-8"))
        self.assertNotIn("course_skill", run_json("course-context", "--course", folder)["summary"])

    def test_a_self_learner_answers_none_and_gets_a_course_with_no_exam_section(self):
        folder = self.tmp / "Linear algebra"
        own = self.tmp / "mine"
        write(own / "Unit 1 - vectors" / "notes.txt", "A vector has a length.")
        status = run_json("university", "status", "--university", "none")
        self.assertFalse(status["generated"])
        self.assertIn("nothing to interview", status["summary"])
        self.assertEqual(run("university", "save", "--university", "none", "--url", "x", "--organizing", "y")[0], 1)
        self.assertFalse((self.home / "generated").exists())
        self.assertEqual(run_json("plugins", "recommend", "--university", "none")["plugins"], [])
        run_json("setup", folder, "--name", "Linear algebra", "--language", "en", "--university", "none",
                 "--import", own, "--tier", "added")
        self.assertEqual(json.loads((folder / ".unistudent" / "settings.json").read_text("utf-8"))["university"], "none")
        course = ["--course", folder]
        context = run_json("course-context", *course)["summary"]
        self.assertNotIn("## Exam", context)
        run_json("wiki", "build", *course)
        write(folders(folder).wiki / "course.md", "# The course\n\n## Exam format\n\nnot in the course material yet\n")
        run("wiki", "check", *course)
        self.assertNotIn("## Exam", run_json("course-context", *course)["summary"])
        # The exam section comes back as soon as the course page has exam information.
        write(folders(folder).wiki / "course.md", "# The course\n\n## Exam format\n\nThree hours, closed book. "
                                                  "Sources: [exam info](sources/general/exam.md)\n")
        run("wiki", "check", *course)
        self.assertIn("## Exam", run_json("course-context", *course)["summary"])


class SetupSkillStatic(unittest.TestCase):
    text = SETUP.read_text("utf-8")

    def test_every_stage_is_named_and_has_its_progress_call(self):
        self.assertIn("us setup-progress advance", self.text)
        for stage in STAGES:
            self.assertIn(f"`{stage}`", self.text, stage)
        # The stages the skill records itself (the last clears progress, recorded in step 0's list).
        for stage in ("path", "format"):
            self.assertRegex(self.text, rf"--stage {stage}\b")

    def test_every_numbered_step_has_a_done_when(self):
        steps = re.split(r"(?m)^## ", self.text)[1:]
        self.assertGreaterEqual(len(steps), 7)
        for step in steps:
            if step.startswith("0."):  # bookkeeping, not a student-facing step
                continue
            self.assertIn("Done when", step, step.splitlines()[0])

    def test_step_1_names_the_none_answer_and_what_it_skips(self):
        step1 = self.text.split("## 1. University")[1].split("## 2.")[0]
        self.assertIn("university=none", step1)
        self.assertRegex(step1, r"(?i)learning on my own")
        self.assertRegex(step1, r"(?i)skip the plugin recommendation and the interview")
        step5 = self.text.split("## 5.")[1].split("## 6.")[0]
        self.assertIn("No university (`none`", step5)
        self.assertIn("\"nothing yet\" only", step5)

    def test_stage_names_in_the_skill_exist_in_the_cli(self):
        for stage in set(re.findall(r"--stage ([a-z-]+)", self.text)):
            self.assertIn(stage, STAGES)

    def test_every_us_command_and_option_in_every_skill_exists(self):
        parser = cli.build_parser()
        checked = 0
        for skill in ALL_SKILLS:
            for words, options in us_invocations(skill.read_text("utf-8")):
                if not words or words[0] in ("command", "doc"):  # conventions block placeholders
                    continue
                node, label = parser, f"{skill.parent.name}: us {' '.join(words)}"
                for word in words:
                    subs = subparsers(node)
                    if subs is None:  # remaining words are a positional choice value: the command must accept it
                        choices = {c for a in node._actions for c in (a.choices or [])}
                        self.assertIn(word, choices, label)
                        continue
                    self.assertIn(word, subs, label)
                    node = subs[word]
                known = {o for a in node._actions for o in a.option_strings}
                for option in options:
                    self.assertIn(option, known, f"{label} {option}")
                checked += 1
        self.assertGreater(checked, 20)


if __name__ == "__main__":
    unittest.main()

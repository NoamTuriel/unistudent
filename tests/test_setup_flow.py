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
STAGES = ["university", "course", "language", "path", "format", "material", "recordings", "installs", "plan", "run",
          "capabilities"]
ASK = re.compile(r"(?i)\bask|interview|\bconfirm")


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
        # Block 1: questions only; the answers wait in the progress file until the course folder exists.
        run_json("university", "save", "--university", "Test U", "--url", "https://example.invalid", "--organizing", "by unit")
        self.assertTrue(run_json("university", "status", "--university", "Test U")["generated"])
        run_json("setup-progress", "advance", *name, "--stage", "university", "--answer", "university=Test U")
        self.assertEqual(run_json("plugins", "recommend", "--university", "Test U")["plugins"], [])
        run_json("setup-progress", "advance", *name, "--stage", "course")
        run_json("setup-progress", "advance", *name, "--stage", "language", "--answer", "language=en")
        run_json("setup-progress", "advance", *name, "--stage", "path", "--answer", f"path={folder}")
        run_json("setup-progress", "advance", *name, "--stage", "format", "--answer", "format=markdown")
        run_json("setup-progress", "advance", *name, "--stage", "material", "--answer", "source=own",
                 "--answer", f"own_folder={own}", "--answer", "tier=official", "--answer", "exam_date=2030-01-01")
        run_json("setup-progress", "advance", *name, "--stage", "recordings", "--answer", "transcribe=yes",
                 "--answer", "frame_analysis=no", "--answer", "keep_video=no", "--answer", "installs=yes")
        # End of block 1: the course folder, the answers that need it, the one-line copy summary.
        run_json("setup", folder, "--name", "Macro", "--format", "markdown", "--language", "en")
        course = ["--course", folder]
        run_json("context", "--recording-level", "3", "--frame-analysis", "0", "--keep-video", "0",
                 "--exam-date", "2030-01-01", *course)
        self.assertIn("2 files", run_json("import", "--dry-run", own, "--tier", "official", *course)["summary"])
        run_json("setup-progress", "advance", *name, "--stage", "installs")
        # Block 2: the copy, then the box the student sees before leaving.
        run_json("import", own, "--tier", "official", *course)
        self.assertIn("2 of 2 downloaded", run_json("fetch-plan", "status", *course)["box"])
        run_json("setup-progress", "advance", *name, "--stage", "plan")
        # The run, then coming back.
        self.assertIn("backend_installed", run_json("recordings", "estimate", *course))
        run_json("wiki", "build", *course)
        run_json("setup-progress", "advance", *name, "--stage", "run")
        self.assertIn("summary", run_json("wiki", "coverage", *course))
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
        write(folders(folder).wiki / "course.md", "# The course\n\n## Exam format\n\nעדיין לא בחומר הקורס\n")
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
        material = self.text.split("## 5.")[1].split("## 6.")[0]
        self.assertIn("No university (`none`", material)
        self.assertIn("\"nothing yet\" only", material)

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


def step(text, number):
    return next(part for part in text.split("\n## ") if part.startswith(f"{number}."))


class WalkAwaySetup(unittest.TestCase):
    """Ticket 37 (ADR 0013): every question first, one restart at most, a Fetch plan, then a run that never asks."""
    text = SETUP.read_text("utf-8")

    def test_the_overview_promises_ten_minutes_and_lists_the_numbered_steps(self):
        overview = self.text.split("## 0.")[0]
        self.assertIn("about 10 minutes of questions, then you can leave for a few hours", overview)
        numbered = [n for n in re.findall(r"(?m)^## (\d+)\.", self.text) if n != "0"]
        line = next(line for line in overview.splitlines() if "**The steps" in line)
        self.assertIn(f"**The steps ({len(numbered)}):**", line)
        self.assertEqual(re.findall(r"(?<![\d-])(\d+)\. ", line), numbered)

    def test_block_1_asks_in_the_spec_order_then_creates_the_folder(self):
        block = self.text[self.text.index("## 1."):self.text.index("## 8.")]
        marks = ["Ask which university", "Ask which course", "Ask which language", "Ask where to keep",
                 "ask which app", "Ask where the material comes from", "official or added",
                 "anything else the course gave", "ask for the exam date", "Question 1 of 3", "Question 2 of 3",
                 "Question 3 of 3", "consent", "`us setup \"", "`us import --dry-run"]
        at = [block.index(m) for m in marks]
        self.assertEqual(at, sorted(at))

    def test_the_three_recording_questions_are_separate_and_each_says_its_cost_and_recommended(self):
        questions = re.split(r"\*\*Question \d of 3", step(self.text, 6))[1:]
        self.assertEqual(len(questions), 3)
        for question in questions:
            for words in ("per hour of recording", "Recommended", "Ask"):
                self.assertIn(words, question)
        self.assertIn("Claude usage", questions[1])
        self.assertIn("pause", questions[1])

    def test_one_restart_at_most_after_the_questions(self):
        self.assertEqual(self.text.count("close and reopen"), 1)
        seven = step(self.text, 7)
        self.assertIn("close and reopen", seven)
        for words in ("University plugin", "video-analysis tool", "Recommended tools", "Harness table"):
            self.assertIn(words, seven)
        one = step(self.text, 1)
        self.assertIn("recorded, not installed yet", one)
        self.assertLess(one.index("--stage university"), one.index("us plugins recommend"))

    def test_block_2_has_the_fetch_plan_the_unit_question_and_the_box_as_the_command_prints_it(self):
        eight = step(self.text, 8)
        for words in ("inside setup", "download all", "skip all recordings", "edit the list", "explicit OK",
                      "I don't know", "us fetch-plan status", "exactly as it comes"):
            self.assertIn(words, eight)
        self.assertLess(eight.index("us fetch-plan status"), eight.index("--stage plan"))
        self.assertNotIn("plugged in", self.text.lower())  # the box's words live in the command only

    def test_every_question_comes_before_the_plan_stage_and_none_in_the_run(self):
        run_step = step(self.text, 9)
        self.assertIsNone(ASK.search(run_step))
        self.assertIsNone(ASK.search(self.text[self.text.index("--stage plan"):self.text.index("## 9.")]))
        self.assertIn("one question", step(self.text, 10))

    def test_the_run_goes_in_the_spec_order_retries_once_and_resumes(self):
        nine = step(self.text, 9)
        order = ["install_run", "course-wiki", "us recordings transcribe", "recording-summarizer",
                 "us recordings audio-only", "Recorded lessons", "us wiki check"]
        at = [nine.index(m) for m in order]
        self.assertEqual(at, sorted(at))
        for words in ("once more", "report", "run setup again", "us fetch-plan status", "in parallel", "--stage run"):
            self.assertIn(words, nine)

    def test_coming_back_reports_and_then_shows_how_to_use_it(self):
        ten = step(self.text, 10)
        for words in ("failed", "what to do", "I don't know", "us wiki coverage", "gaps"):
            self.assertIn(words, ten)
        self.assertIn("--stage capabilities", step(self.text, 11))

    def test_course_recordings_still_works_for_recordings_added_later(self):
        text = (CORE / "course-recordings" / "SKILL.md").read_text("utf-8")
        self.assertIn("added later", text)
        self.assertLess(text.index("recording-summarizer"), text.index("us recordings audio-only"))

    def test_adr_0013_and_the_readme_say_it(self):
        adr = next((ROOT / "docs" / "adr").glob("0013-*.md")).read_text("utf-8")
        self.assertTrue(adr.startswith(
            "# Setup asks everything first, approves downloads with a Fetch plan, then runs unattended"))
        readme = (ROOT / "README.md").read_text("utf-8")
        for words in ("about 10 minutes of questions", "Fetch plan", "plugged in", "course-add"):
            self.assertIn(words, readme)


if __name__ == "__main__":
    unittest.main()

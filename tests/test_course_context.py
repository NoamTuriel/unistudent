"""Course context (ticket 14): the AI picks the course up by opening the folder, or by one tool call in Desktop."""
import json
import os
import unittest
from contextlib import contextmanager

from helpers import CourseTestCase, run, run_json, write


@contextmanager
def cwd(path):
    old = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


class CourseContext(CourseTestCase):
    def make(self, name):
        folder = self.tmp / name
        run_json("setup", folder, "--name", name, "--language", "en")
        return folder

    def test_from_inside_the_course_it_returns_the_course_rules(self):
        course = self.make("Macro")
        with cwd(course):
            result = run_json("course-context")
        self.assertEqual(result["course"], "Macro")
        self.assertIn("Grounding labels", result["context"])

    def test_from_a_folder_below_the_course_it_still_finds_the_course(self):
        course = self.make("Macro")
        (course / "inbox").mkdir(exist_ok=True)
        with cwd(course / "inbox"):
            self.assertEqual(run_json("course-context")["course"], "Macro")

    def test_outside_any_course_it_uses_the_active_course(self):
        self.make("Macro")
        with cwd(self.tmp):
            self.assertEqual(run_json("course-context")["course"], "Macro")

    def test_with_several_courses_and_none_active_it_lists_them_and_asks(self):
        self.make("Macro")
        self.make("Micro")
        registry = self.home / "registry.json"
        data = json.loads(registry.read_text("utf-8"))
        data["active"] = None
        registry.write_text(json.dumps(data), "utf-8")
        with cwd(self.tmp):
            result = run_json("course-context")
        self.assertIsNone(result["course"])
        self.assertEqual(sorted(c["name"] for c in result["courses"]), ["Macro", "Micro"])
        self.assertIn("ask", result["summary"].lower())

    def test_an_explicit_course_wins(self):
        macro = self.make("Macro")
        self.make("Micro")
        with cwd(self.tmp):
            self.assertEqual(run_json("course-context", "--course", macro)["course"], "Macro")

    def test_with_no_course_at_all_it_says_to_set_one_up(self):
        with cwd(self.tmp):
            code, _ = run("course-context", "--json")
        self.assertEqual(code, 1)

    def test_setup_writes_a_gemini_pointer_and_keeps_the_students_own_file(self):
        course = self.make("Macro")
        self.assertIn("@.unistudent/context.md", (course / "GEMINI.md").read_text("utf-8"))
        other = self.tmp / "Mine"
        write(other / "GEMINI.md", "# Mine\n")
        run_json("setup", other, "--name", "Mine")
        run_json("setup", other, "--name", "Mine")
        text = (other / "GEMINI.md").read_text("utf-8")
        self.assertTrue(text.startswith("# Mine"))
        self.assertEqual(text.count("@.unistudent/context.md"), 1)


if __name__ == "__main__":
    unittest.main()

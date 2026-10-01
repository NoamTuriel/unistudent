"""Graphs in study packs: `us graph` draws a Graph spec to a PNG, and `us check --labels` guards the caption."""
import importlib.util
import json
import unittest

from helpers import CourseTestCase, mock_env, run, run_json, write

HAS_MATPLOTLIB = importlib.util.find_spec("matplotlib") is not None

SKETCH = {"x": "כמות כסף M", "y": "ריבית i",
          "curves": [{"name": "Ms", "vertical": 5},
                     {"name": "Md", "sketch": [[1, 8], [4, 5], [9, 2]]},
                     {"name": "Md'", "sketch": [[2, 9], [5, 6.5], [9.5, 3.5]], "shift_of": "Md"}],
          "points": [{"label": "E1", "at": ["Ms", "Md"]}, {"label": "E2", "at": ["Ms", "Md'"]}]}
FORMULA = {"x": "x", "y": "y",
           "curves": [{"name": "f", "formula": "x^2/10 + sqrt(x)"}, {"name": "g", "points": [[0, 1], [10, 9]]}],
           "points": [{"label": "A", "at": ["f", "g"]}]}


class GraphCommand(CourseTestCase):
    def spec(self, data, name="curve"):
        return write(self.tmp / "vault" / "Unit 1" / "graphs" / f"{name}.json", json.dumps(data, ensure_ascii=False))

    def test_a_spec_is_drawn_next_to_itself_and_not_redrawn_until_it_changes(self):
        if not HAS_MATPLOTLIB:
            self.skipTest("matplotlib not installed")
        spec = self.spec(SKETCH)
        first = run_json("graph", spec)
        png = spec.with_suffix(".png")
        self.assertTrue(first["drawn"])
        self.assertTrue(png.read_bytes().startswith(b"\x89PNG"))

        before = png.read_bytes()
        self.assertFalse(run_json("graph", spec)["drawn"])
        self.assertEqual(png.read_bytes(), before)

        changed = dict(SKETCH, x="Money M")
        spec.write_text(json.dumps(changed), "utf-8")
        self.assertTrue(run_json("graph", spec)["drawn"])
        self.assertNotEqual(png.read_bytes(), before)

    def test_formula_and_sketch_graphs_both_draw(self):
        if not HAS_MATPLOTLIB:
            self.skipTest("matplotlib not installed")
        for name, data in (("sketch", SKETCH), ("formula", FORMULA)):
            spec = self.spec(data, name)
            code, out = run("graph", spec)
            self.assertEqual(code, 0, out)
            self.assertTrue(spec.with_suffix(".png").exists())

    def test_a_formula_outside_the_allowed_list_is_refused_plainly(self):
        bad = {"x": "x", "y": "y", "curves": [{"name": "f", "formula": "__import__(x)"}]}
        code, out = run("graph", self.spec(bad))
        self.assertEqual(code, 1)
        self.assertIn("isn't allowed", out)
        code, out = run("graph", self.spec({"x": "x", "y": "y", "curves": [{"name": "f", "formula": "tan(x)"}]}))
        self.assertIn("'tan'", out)

    def test_plain_messages_for_a_broken_spec(self):
        shift = {"x": "x", "y": "y", "curves": [{"name": "A", "points": [[0, 0], [1, 1]], "shift_of": "B"}]}
        code, out = run("graph", self.spec(shift, "shift"))
        self.assertEqual(code, 1)
        self.assertIn('"B"', out)
        parallel = {"x": "x", "y": "y", "curves": [{"name": "A", "horizontal": 1}, {"name": "B", "horizontal": 2}],
                    "points": [{"label": "E", "at": ["A", "B"]}]}
        code, out = run("graph", self.spec(parallel, "parallel"))
        self.assertIn("do not cross", out)

    def test_without_matplotlib_nothing_is_drawn_and_the_message_says_how_to_add_it(self):
        spec = self.spec(SKETCH)
        with mock_env(UNISTUDENT_NO_MATPLOTLIB="1"):
            code, out = run("graph", spec)
        self.assertEqual(code, 1)
        self.assertIn("pip install", out)
        self.assertFalse(spec.with_suffix(".png").exists())


PAGE = """## Money market

✅ The money market clears where supply meets demand. Sources: [slides p.1](../../.unistudent/wiki/index.md)

![Md shifts right, the interest rate falls](graphs/money.png)
{caption}
"""


class GraphCaptions(CourseTestCase):
    def setUp(self):
        super().setUp()
        self.course = self.tmp / "Macro"
        run("setup", self.course, "--name", "Macro", "--language", "en")
        write(self.course / ".unistudent" / "wiki" / "index.md", "# Wiki\n")
        self.folder = self.course / "3-Macro-study-from-here" / "Unit 1"
        write(self.folder / "graphs" / "money.png", b"\x89PNG")

    def kinds(self, caption):
        page = write(self.folder / "page.md", PAGE.format(caption=caption))
        return sorted(p["kind"] for p in run_json("check", "--course", self.course, page, "--labels")["problems"])

    def test_a_graph_with_a_labelled_caption_passes(self):
        self.assertEqual(self.kinds("✅ Fig 3 [slides](../../.unistudent/wiki/index.md)"), [])
        self.assertEqual(self.kinds("✅ Money market graph from the slides. [slides p.1](../../.unistudent/wiki/index.md)"), [])
        self.assertEqual(self.kinds("💡 An illustration of the money market. [slides p.1](../../.unistudent/wiki/index.md)"), [])

    def test_a_graph_needs_a_caption_with_a_label_that_is_not_outside_the_course(self):
        self.assertEqual(self.kinds(""), ["graph-no-caption"])
        self.assertEqual(self.kinds("⚠️ A graph made up from outside the course material."), ["graph-label"])
        self.assertEqual(self.kinds("A graph of the money market with no label at all."), ["graph-no-caption", "unlabeled"])
        self.assertEqual(self.kinds("✅ A caption with no source link at all here."), ["no-citation", "no-citation"])

    def test_a_missing_image_file_is_reported(self):
        (self.folder / "graphs" / "money.png").unlink()
        self.assertEqual(self.kinds("✅ Money market graph. [slides p.1](../../.unistudent/wiki/index.md)"), ["missing-image"])


if __name__ == "__main__":
    unittest.main()

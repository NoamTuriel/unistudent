"""Picture kinds (ticket 23): `us draw <kind> <spec>` dispatches to one small drawer per kind, installing its package on demand."""
import json
import os
import shutil
import types
import unittest
from unittest import mock

from helpers import CourseTestCase, mock_env, run, run_json, write
from unistudent import draw


def fake_kind(package, calls):
    """A drawer that 'draws' by writing a PNG next to the spec; `package` is the library it needs."""
    def run_kind(spec_path, force=False):
        calls.append(spec_path)
        png = spec_path.with_suffix(".png")
        png.write_bytes(b"png")
        return {"png": str(png), "drawn": True}
    return {"package": package, "label": "the fake tool", "run": run_kind}


class DrawCommand(CourseTestCase):
    def setUp(self):
        super().setUp()
        self.spec = write(self.tmp / "pic.json", json.dumps({"any": "thing"}))
        self.calls = []

    def kinds(self, **kinds):
        return mock.patch.dict(draw.KINDS, kinds, clear=True)

    def test_a_kind_whose_package_is_present_is_drawn_next_to_its_spec(self):
        with self.kinds(fake=fake_kind("json", self.calls)):  # json is always importable
            result = run_json("draw", "fake", self.spec)
        self.assertEqual(self.calls, [self.spec])
        self.assertTrue(self.spec.with_suffix(".png").exists())
        self.assertTrue(result["drawn"])

    def test_an_unknown_kind_lists_the_kinds_that_exist(self):
        with self.kinds(fake=fake_kind("json", self.calls)):
            code, out = run("draw", "circuit", self.spec)
        self.assertEqual(code, 1)
        self.assertIn("fake", out)

    def test_a_missing_package_is_fetched_with_uv_and_the_result_comes_back(self):
        png = self.spec.with_suffix(".png")
        done = types.SimpleNamespace(returncode=0, stdout=json.dumps({"png": str(png), "drawn": True}), stderr="")
        with self.kinds(fake=fake_kind("unistudent_no_such_package", self.calls)), \
                mock.patch("unistudent.draw.shutil.which", return_value="/bin/uv"), \
                mock.patch("unistudent.draw.subprocess.run", return_value=done) as sub:
            result = run_json("draw", "fake", self.spec)
        argv = sub.call_args[0][0]
        self.assertEqual(argv[:2], ["/bin/uv", "run"])
        self.assertEqual(argv[argv.index("--with") + 1], "unistudent_no_such_package")
        self.assertEqual(self.calls, [])  # drawn in the uv process, not here
        self.assertTrue(result["drawn"])
        self.assertIn("one-time", result["summary"])

    def test_a_failed_download_says_so_plainly_and_draws_nothing(self):
        failed = types.SimpleNamespace(returncode=1, stdout="", stderr="no network")
        with self.kinds(fake=fake_kind("unistudent_no_such_package", self.calls)), \
                mock.patch("unistudent.draw.shutil.which", return_value="/bin/uv"), \
                mock.patch("unistudent.draw.subprocess.run", return_value=failed):
            code, out = run("draw", "fake", self.spec)
        self.assertEqual(code, 1)
        self.assertIn("describe", out)  # the words fallback for the study pack
        self.assertIn("try the fake tool again", out)
        self.assertFalse(self.spec.with_suffix(".png").exists())

    def test_without_uv_or_with_installing_off_nothing_is_fetched(self):
        with self.kinds(fake=fake_kind("unistudent_no_such_package", self.calls)), \
                mock.patch("unistudent.draw.subprocess.run") as sub, mock_env(UNISTUDENT_NO_INSTALL="1"):
            code, out = run("draw", "fake", self.spec)
        self.assertEqual(code, 1)
        sub.assert_not_called()
        self.assertIn("describe", out)

    def test_graph_is_still_a_command_and_goes_through_the_same_dispatcher(self):
        with mock.patch("unistudent.draw.draw", return_value={"png": "x.png", "drawn": True}) as dispatch:
            run("graph", self.spec)
        dispatch.assert_called_once()
        self.assertEqual(dispatch.call_args[0][0], "graph")


class Draws(CourseTestCase):
    def test_every_kind_is_listed_with_what_it_draws_and_needs_no_course(self):
        result = run_json("draws")
        self.assertIn("X-Y graphs", result["supports"])  # the kinds
        self.assertIn("Mermaid flowcharts", result["supports"])  # drawn with no tool at all
        self.assertIn("The plugin can draw", result["summary"])

    def test_a_new_kind_shows_up_without_touching_the_command(self):
        with mock.patch.dict(draw.KINDS, {"fake": fake_kind("json", [])}):
            draw.KINDS["fake"]["draws"] = "fake pictures"
            self.assertIn("fake pictures", run_json("draws")["supports"])


@unittest.skipUnless(os.environ.get("UNISTUDENT_SMOKE") and shutil.which("uv"), "set UNISTUDENT_SMOKE=1 to download for real")
class RealDownload(CourseTestCase):
    def test_the_graph_tool_is_fetched_by_uv_and_draws_a_png(self):
        spec = write(self.tmp / "g.json", json.dumps({"x": "x", "y": "y", "curves": [{"name": "f", "points": [[0, 0], [1, 1]]}]}))
        result = draw._fetch_and_draw("graph", draw.KINDS["graph"], spec, False)
        self.assertTrue(result["drawn"])
        self.assertTrue(spec.with_suffix(".png").stat().st_size > 0)


if __name__ == "__main__":
    unittest.main()

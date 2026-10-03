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
        self.assertIn("pip install unistudent_no_such_package", out)
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


@unittest.skipUnless(os.environ.get("UNISTUDENT_SMOKE") and shutil.which("uv"), "set UNISTUDENT_SMOKE=1 to download for real")
class RealDownload(CourseTestCase):
    def test_the_graph_tool_is_fetched_by_uv_and_draws_a_png(self):
        spec = write(self.tmp / "g.json", json.dumps({"x": "x", "y": "y", "curves": [{"name": "f", "points": [[0, 0], [1, 1]]}]}))
        result = draw._fetch_and_draw("graph", draw.KINDS["graph"], spec, False)
        self.assertTrue(result["drawn"])
        self.assertTrue(spec.with_suffix(".png").stat().st_size > 0)


def offerable(**extra):
    kind = {"package": "json", "label": "the circuit tool", "draws": "circuit diagrams", "offer": True,
            "fields": ["electrical", "engineering"], "evidence": ["resistor", "circuit"],
            "run": lambda spec, force=False: {}}
    kind.update(extra)
    return kind


class ToolOffer(CourseTestCase):
    def setUp(self):
        super().setUp()
        self.course = self.tmp / "Circuits"
        run("setup", self.course, "--name", "Circuits", "--language", "en")

    def wiki(self, text):
        write(self.course / ".unistudent" / "wiki" / "units" / "u1.md", text)

    def offer(self, **kinds):
        with mock.patch.dict(draw.KINDS, kinds):
            return run_json("tools", "offer", "--course", self.course, "--field", "engineering")

    def test_what_the_course_shows_decides_the_offer_and_graph_is_never_offered(self):
        self.wiki("Kirchhoff on a resistor circuit.")
        result = self.offer(circuit=offerable())
        self.assertEqual([t["name"] for t in result["tools"]], ["circuit"])
        self.assertIn("circuit diagrams", result["summary"])

    def test_the_field_is_the_fallback_when_the_wiki_says_nothing(self):
        result = self.offer(circuit=offerable())
        self.assertEqual([t["name"] for t in result["tools"]], ["circuit"])

    def test_a_tool_the_course_never_shows_is_not_offered_when_the_wiki_is_rich(self):
        self.wiki("Only sets and groups. " * 50)
        self.assertEqual(self.offer(circuit=offerable(fields=[]))["tools"], [])

    def test_at_most_three_tools_are_offered(self):
        self.wiki("resistor")
        many = {f"k{i}": offerable() for i in range(5)}
        self.assertEqual(len(self.offer(**many)["tools"]), 3)

    def test_an_answer_is_remembered_and_not_asked_again_and_a_skip_can_be_undone(self):
        self.wiki("resistor")
        with mock.patch.dict(draw.KINDS, {"circuit": offerable()}):
            run_json("tools", "skip", "circuit", "--course", self.course)
            self.assertEqual(run_json("tools", "offer", "--course", self.course)["tools"], [])
            context = (self.course / ".unistudent" / "context.md").read_text("utf-8")
            self.assertIn("circuit: skipped", context)
            with mock.patch("unistudent.draw.subprocess.run",
                            return_value=types.SimpleNamespace(returncode=0, stdout="", stderr="")), \
                    mock.patch("unistudent.draw.shutil.which", return_value="/bin/uv"):
                run_json("tools", "accept", "circuit", "--course", self.course)
            context = (self.course / ".unistudent" / "context.md").read_text("utf-8")
        self.assertIn("circuit: accepted", context)
        self.assertNotIn("circuit: skipped", context)

    def test_accepting_fetches_the_package_and_a_failed_fetch_is_said_plainly(self):
        failed = types.SimpleNamespace(returncode=1, stdout="", stderr="offline")
        with mock.patch.dict(draw.KINDS, {"circuit": offerable(package="unistudent_no_such_package")}), \
                mock.patch("unistudent.draw.shutil.which", return_value="/bin/uv"), \
                mock.patch("unistudent.draw.subprocess.run", return_value=failed):
            result = run_json("tools", "accept", "circuit", "--course", self.course)
        self.assertIn("couldn't", result["summary"])
        self.assertEqual(result["failed"], ["circuit"])

    def test_the_supports_line_lists_what_this_course_can_draw(self):
        with mock.patch.dict(draw.KINDS, {"circuit": offerable()}):
            run_json("tools", "skip", "circuit", "--course", self.course)
            self.assertNotIn("circuit diagrams", run_json("tools", "status", "--course", self.course)["supports"])
            with mock.patch("unistudent.draw.subprocess.run",
                            return_value=types.SimpleNamespace(returncode=0, stdout="", stderr="")):
                run_json("tools", "accept", "circuit", "--course", self.course)
            supports = run_json("tools", "status", "--course", self.course)["supports"]
        self.assertIn("X-Y graphs", supports)
        self.assertIn("circuit diagrams", supports)


if __name__ == "__main__":
    unittest.main()

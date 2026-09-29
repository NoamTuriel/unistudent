"""Shared test helpers: run the CLI the way a skill does, and build fixture folders."""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "plugins" / "unistudent" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from unistudent import cli  # noqa: E402


def run(*argv):
    """Run the CLI in-process. Returns (exit_code, stdout)."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = cli.main([str(a) for a in argv])
    return code, out.getvalue()


def run_json(*argv):
    code, out = run(*argv, "--json")
    assert code == 0, out
    return json.loads(out)


def write(path, content=b"x"):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        content = content.encode("utf-8")
    path.write_bytes(content)
    return path


class CourseTestCase(unittest.TestCase):
    """Gives every test an isolated home (Registry, general preferences) and a scratch dir."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.home = self.tmp / "home"
        self._env = mock_env(UNISTUDENT_HOME=str(self.home))
        self._env.__enter__()

    def tearDown(self):
        self._env.__exit__(None, None, None)
        self._tmp.cleanup()


@contextlib.contextmanager
def mock_env(**values):
    old = {k: os.environ.get(k) for k in values}
    os.environ.update({k: v for k, v in values.items() if v is not None})
    for k, v in values.items():
        if v is None:
            os.environ.pop(k, None)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

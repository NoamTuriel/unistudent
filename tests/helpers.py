"""Shared test helpers: run the CLI the way a skill does, and build fixture folders."""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "plugins" / "unistudent" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from unistudent import cli  # noqa: E402


def can_read_pdfs():
    """Whether convert.py has a PDF text tool to work with (pdftotext or pypdf, both optional)."""
    return shutil.which("pdftotext") is not None or importlib.util.find_spec("pypdf") is not None


def file_is_released(path):
    """Whether `path` is closed by whoever still had it open (a detached process writing its own log).

    On Windows an open-for-write handle blocks a rename; POSIX has no such lock, so this is
    always true there. Used to wait out a background process before touching its temp dir.
    """
    try:
        path.replace(path)
        return True
    except PermissionError:
        return False


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


def folders(course):
    """The visible folders and the Wiki of a set-up course folder, as the setup stored them (any language)."""
    course = Path(course)
    names = json.loads((course / ".unistudent" / "settings.json").read_text("utf-8"))["folders"]
    return types.SimpleNamespace(inbox=course / names["inbox"], material=course / names["material"],
                                 study=course / names["study"], wiki=course / ".unistudent" / "wiki")


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


def make_pdf(path, pages):
    """Write a minimal valid PDF with one line of ASCII text per page (no dependencies)."""
    objects = []

    def obj(body):
        objects.append(body)
        return len(objects)

    font = obj(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    kids = []
    pages_id = len(objects) + 1 + 2 * len(pages)  # reserved below
    for text in pages:
        stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode("latin-1")
        content = obj(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        kids.append(obj(b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 612 792] "
                        b"/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>"
                        % (pages_id, font, content)))
    assert obj(b"<< /Type /Pages /Kids [%s] /Count %d >>"
               % (b" ".join(b"%d 0 R" % k for k in kids), len(kids))) == pages_id
    catalog = obj(b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id)
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objects) + 1, catalog, xref)
    return write(path, bytes(out))

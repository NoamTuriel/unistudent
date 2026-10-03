"""Picture kinds (ADR 0010): one small drawer per kind, its library fetched on first use.

`draw(kind, spec)` runs the kind's drawer. When the kind's package is not importable here, the same command runs
again in `uv run --with <package>`, which downloads and caches it: no restart, no config edit, the same on every OS.
Standard library only; the libraries live inside the drawers.
"""
import importlib.util
import json
import os
import shutil
import subprocess
from pathlib import Path

from .common import UserError

SCRIPTS = Path(__file__).resolve().parents[1]  # the folder that holds the `unistudent` package
INNER = "UNISTUDENT_DRAW_INNER"  # set in the uv process so it draws instead of fetching again
RERUN = "import sys; sys.path.insert(0, sys.argv[1]); from unistudent import cli; sys.exit(cli.main(sys.argv[2:]))"


def _graph(spec_path, force=False):
    from . import graph
    return graph.draw(spec_path, force=force)


# kind -> the library it needs (a pip name), a plain label for the student, and the drawer: run(spec_path, force).
# Add a kind by adding a line here and a drawer module; `us draw` and the MCP tool need no other change.
# Every kind fetches its own library the first time a picture needs it, so no kind is ever asked about.
# Add one when a real course shows that picture, not before: an untried drawer is a promise nobody has seen kept.
# `draws` is the plain phrase the student reads; `module` is the import name when it differs from the pip name.
KINDS = {
    "graph": {"package": "matplotlib", "label": "the graph tool", "draws": "X-Y graphs", "run": _graph},
}
ALWAYS = ["Mermaid flowcharts"]  # drawn without any tool
TIMEOUT = 300  # seconds for a one-time download


def _available(kind):
    if kind["package"] == "matplotlib" and os.environ.get("UNISTUDENT_NO_MATPLOTLIB"):
        return False  # lets tests (and students) force the "not installed" path
    modules = [kind["module"]] if "module" in kind else kind["package"].split()
    return all(importlib.util.find_spec(m) is not None for m in modules)


def _with(kind):
    return [a for package in kind["package"].split() for a in ("--with", package)]


def _words_fallback(kind):
    return (f"Link the slide page and describe the picture in one line. Ask me to try {kind['label']} again "
            f"when you're online.")


def _fetch_and_draw(name, kind, spec_path, force):
    """Draw in a uv process that has the package. Returns the drawer's result, or raises a plain UserError."""
    uv = shutil.which("uv")
    if not uv or os.environ.get("UNISTUDENT_NO_INSTALL") or os.environ.get(INNER):
        raise UserError(f"I can't draw this: {kind['label']} ({kind['package']}) isn't installed here and can't be "
                        f"fetched automatically. {_words_fallback(kind)}")
    argv = [uv, "run", "--no-project", *_with(kind), "python", "-c", RERUN, str(SCRIPTS),
            "draw", name, str(spec_path), "--json"] + (["--force"] if force else [])
    env = {k: v for k, v in os.environ.items() if k != "UNISTUDENT_NO_MATPLOTLIB"}
    try:
        done = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace",
                              env={**env, INNER: "1"}, timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        raise UserError(f"Getting {kind['label']} took too long. {_words_fallback(kind)}")
    try:
        result = json.loads(done.stdout)
    except ValueError:
        result = {}
    if done.returncode != 0 or "error" in result:
        reason = result.get("error") or (done.stderr or "").strip().splitlines()[-1:] or ["the download failed"]
        raise UserError(f"I couldn't get {kind['label']} ({reason if isinstance(reason, str) else reason[0]}). "
                        f"{_words_fallback(kind)}")
    result["summary"] = f"Fetched {kind['label']} (one-time download). " + result.get("summary", "")
    return result


def draw(name, spec_path, force=False):
    """Draw the spec with the named kind. Returns {png, drawn}, plus a summary when a tool was fetched."""
    if name not in KINDS:
        raise UserError(f'There is no picture kind "{name}". Kinds: {", ".join(sorted(KINDS))}.')
    kind, spec_path = KINDS[name], Path(spec_path)
    if _available(kind):
        return kind["run"](spec_path, force=force)
    return _fetch_and_draw(name, kind, spec_path, force)


def supports():
    """Every picture the plugin can draw: one phrase per kind, plus what needs no tool at all."""
    return [k["draws"] for k in KINDS.values()] + ALWAYS

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
import sys
from pathlib import Path

from .common import UserError

SCRIPTS = Path(__file__).resolve().parents[1]  # the folder that holds the `unistudent` package
INNER = "UNISTUDENT_DRAW_INNER"  # set in the uv process so it draws instead of fetching again
RERUN = "import sys; sys.path.insert(0, sys.argv[1]); from unistudent import cli; sys.exit(cli.main(sys.argv[2:]))"


def _graph(spec_path, force=False):
    from . import graph
    return graph.draw(spec_path, force=force)


def _pictures(name, spec_path, force):
    from . import pictures
    return getattr(pictures, name)(spec_path, force=force)


# kind -> the library it needs (a pip name), a plain label for the student, and the drawer: run(spec_path, force).
# Add a kind by adding a line here and a drawer module; `us draw` and the MCP tool need no other change.
# `offer` kinds are asked about before the first Study pack (`us tools offer`); the others install themselves silently.
# `draws` is the plain phrase the student reads; `evidence` are words in the Wiki that show the course uses the kind,
# `fields` are the fallback when the Wiki says little. `module` is the import name when it differs from the pip name.
KINDS = {
    "graph": {"package": "matplotlib", "label": "the graph tool", "draws": "X-Y graphs", "offer": False, "run": _graph},
    "circuit": {"package": "schemdraw matplotlib", "module": "schemdraw", "label": "the circuit tool",
                "draws": "circuit diagrams", "offer": True, "fields": ["electrical", "electronic", "engineering", "physics"],
                "evidence": ["resistor", "circuit", "capacitor", "kirchhoff"], "run": lambda s, force=False: _pictures("circuit", s, force)},
    "molecule": {"package": "rdkit", "label": "the molecule tool", "draws": "molecule structures and reaction schemes",
                 "offer": True, "fields": ["chemistry", "biochemistry"], "evidence": ["molecule", "reaction", "benzene", "functional group"],
                 "run": lambda s, force=False: _pictures("molecule", s, force)},
    "tree": {"package": "biopython matplotlib", "module": "Bio", "label": "the family-tree tool", "draws": "phylogenetic trees",
             "offer": True, "fields": ["biology", "evolution"], "evidence": ["phylogen", "cladogram", "evolutionary tree"],
             "run": lambda s, force=False: _pictures("tree", s, force)},
}
ALWAYS = ["Mermaid flowcharts"]  # drawn without any tool
THIN_WIKI = 500  # characters: below this the Wiki says too little to judge, so the field decides
MAX_OFFER = 3
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


# --- the offer: which tools fit this course, and what the student answered ---

def _wiki_text(wiki):
    return " ".join(p.read_text("utf-8", errors="replace") for p in sorted(Path(wiki).rglob("*.md"))).casefold()


def offer(wiki, field, answers):
    """Up to three tools worth offering: what the Wiki shows first, the field only when the Wiki says little."""
    text, field = _wiki_text(wiki), (field or "").casefold()
    thin, found = len(text) < THIN_WIKI, []
    for name, kind in KINDS.items():
        if not kind.get("offer") or name in answers:
            continue
        shown = sum(text.count(w.casefold()) for w in kind.get("evidence", []))
        if shown or (thin and any(f in field for f in kind.get("fields", []) if field)):
            found.append((shown, name))
    return [name for _, name in sorted(found, key=lambda f: -f[0])[:MAX_OFFER]]


def accept(name):
    """Fetch the kind's package now (so the first picture is instant). Returns None, or a plain reason it failed."""
    kind = KINDS[name]
    if _available(kind):
        return None
    uv = shutil.which("uv")
    if not uv or os.environ.get("UNISTUDENT_NO_INSTALL"):
        return f"uv isn't available here. {_words_fallback(kind)}"
    done = subprocess.run([uv, "run", "--no-project", *_with(kind), "python", "-c",
                           f"import {kind.get('module', kind['package'].split()[0])}"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=TIMEOUT)
    return None if done.returncode == 0 else f"the download failed ({(done.stderr or '').strip()[-120:] or 'no detail'})"


def supports(answers):
    """Everything this course can draw now: the baseline, the kinds that install themselves, and accepted tools."""
    drawn = [k["draws"] for n, k in KINDS.items() if not k.get("offer") or answers.get(n, {}).get("state") == "accepted"]
    return drawn + ALWAYS

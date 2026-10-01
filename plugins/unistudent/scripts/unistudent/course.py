"""Course folder, Settings, Manifest and Registry (see CONTEXT.md)."""
import json
import os
import re
from pathlib import Path

STATE_DIR = ".unistudent"

# Folder names are always English; unit titles inside pages follow the course language.
LABELS = {
    "he": {"unit": "יחידה {n}", "general": "כללי", "unsorted": "לא ממוין"},
    "en": {"unit": "Unit {n}", "general": "General", "unsorted": "Unsorted"},
}

DEFAULT_SETTINGS = {
    "course_name": "",
    "language": "he",
    "format": "obsidian",          # obsidian | markdown
    "course_skill": None,          # e.g. "macro"; None → generic rules
    "university": None,            # e.g. "openu"; None → core only
    "recording_level": None,       # None (not asked yet) | 0 skip | 1 download only | 3 transcript + summary
    "frame_analysis": None,        # None (not asked yet) | True | False: per-segment vision calls (opt-in, costly)
    "recordings_dir": None,        # local non-synced folder when the course folder syncs
    "exam_date": None,
    "unit_answers": {},            # raw path → unit number or "general"
}


def safe_name(name: str) -> str:
    """A file or folder name that is valid on every OS."""
    return re.sub(r'[\\/:*?"<>|#^\[\]]', "-", str(name)).strip() or "file"


def parse_unit(value):
    """A unit as stored: an int, "general" (whole course), or None (unsorted)."""
    if value is None or value == "unsorted":
        return None
    if str(value).strip().lower() in ("general", "0"):
        return "general"
    try:
        number = int(str(value).strip())
    except ValueError:
        raise ValueError(f"A unit is a number, 'general' or 'unsorted', not {value!r}.")
    if number < 0:
        raise ValueError(f"A unit number can't be negative: {value!r}.")
    return number


def unit_dir(unit) -> str:
    """Internal folder name for a unit (Wiki pages, state)."""
    unit = parse_unit(unit)
    if unit is None:
        return "unsorted"
    if unit == "general":
        return "general"
    return f"unit-{unit:02d}"


def home() -> Path:
    return Path(os.environ.get("UNISTUDENT_HOME") or Path.home() / ".unistudent")


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text("utf-8"))
    except FileNotFoundError:
        return default


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), "utf-8")
    os.replace(tmp, path)  # atomic, so an interrupted run never leaves half a file


class Course:
    def __init__(self, root):
        self.root = Path(root).resolve()

    # --- locations -------------------------------------------------------
    @property
    def state(self):
        return self.root / STATE_DIR

    @property
    def raw(self):
        return self.root / "raw"

    @property
    def wiki(self):
        return self.root / "wiki"

    @property
    def materials(self):
        return self.root / "materials"

    @property
    def study(self):
        return self.root / "study"

    @property
    def inbox(self):
        return self.root / "inbox"

    @property
    def preferences_file(self):
        return self.root / "course-preferences.md"

    def exists(self):
        return (self.state / "settings.json").exists()

    # --- settings & manifest ----------------------------------------------
    def settings(self):
        data = dict(DEFAULT_SETTINGS)
        data.update(_read_json(self.state / "settings.json", {}))
        return data

    def save_settings(self, data):
        _write_json(self.state / "settings.json", data)

    def update_settings(self, **changes):
        data = self.settings()
        data.update({k: v for k, v in changes.items() if v is not None})
        self.save_settings(data)
        return data

    def manifest(self):
        return _read_json(self.state / "manifest.json", {"files": {}})

    def save_manifest(self, data):
        _write_json(self.state / "manifest.json", data)

    def read_state(self, name, default):
        return _read_json(self.state / name, default)

    def write_state(self, name, data):
        _write_json(self.state / name, data)

    def label(self, key, **kw):
        lang = self.settings().get("language", "he")
        return LABELS.get(lang, LABELS["en"])[key].format(**kw)

    def unit_folder(self, unit):
        """Folder name for a unit in materials/ and study/: English on every course."""
        unit = parse_unit(unit)
        if unit is None:
            return LABELS["en"]["unsorted"]
        if unit == "general":
            return LABELS["en"]["general"]
        return LABELS["en"]["unit"].format(n=unit)

    def unit_label(self, unit):
        """A unit's title in the course language, for page content."""
        unit = parse_unit(unit)
        if unit is None:
            return self.label("unsorted")
        if unit == "general":
            return self.label("general")
        return self.label("unit", n=unit)


def find_course(start=None, use_registry=True):
    """The course folder containing `start` (default: cwd), else the active course in the Registry."""
    here = Path(start or os.getcwd()).resolve()
    for folder in [here, *here.parents]:
        if (folder / STATE_DIR / "settings.json").exists():
            return Course(folder)
    if not use_registry:
        return None
    active = Registry().active()
    if active:
        return Course(active)
    return None


class Registry:
    """Per-student list of course folders, next to the general preferences."""

    def __init__(self):
        self.path = home() / "registry.json"

    def _data(self):
        return _read_json(self.path, {"courses": [], "active": None})

    def courses(self):
        data = self._data()
        for entry in data["courses"]:
            entry["active"] = entry["path"] == data.get("active")
            entry["exists"] = Path(entry["path"], STATE_DIR, "settings.json").exists()
        return data["courses"]

    def active(self):
        return self._data().get("active")

    def add(self, course: Course, name: str):
        data = self._data()
        path = str(course.root)
        data["courses"] = [c for c in data["courses"] if c["path"] != path]
        data["courses"].append({"name": name, "path": path})
        data["active"] = path
        _write_json(self.path, data)

    def switch(self, name_or_path: str):
        data = self._data()
        for entry in data["courses"]:
            if name_or_path in (entry["name"], entry["path"]):
                data["active"] = entry["path"]
                _write_json(self.path, data)
                return entry
        return None


def general_preferences_file() -> Path:
    return home() / "general-preferences.md"


def _slug(text: str) -> str:
    """A lookup key that survives spelling/case/spacing drift between sessions ("Bar-Ilan" == "bar ilan")."""
    return re.sub(r"[^a-z0-9]+", "-", str(text).strip().casefold()).strip("-") or "unknown"


# The university-to-plugin and subject-to-plugin mapping, in one place (ticket 12). A university plugin is matched
# by its own test on the normalized name ("Open University UK" must not match the Israeli one); a subject plugin on a keyword inside the field or course name. One entry per plugin.
PLUGIN_RECOMMENDATIONS = [
    {"name": "openu", "kind": "university",
     "gives": "downloads new material from your Open University of Israel course site",
     "match": lambda uni: (uni == "oui" or "פתוחה" in uni or "openu" in uni.replace("openuniversity", "")
                           or ("openuniversity" in uni and ("israel" in uni or "ישראל" in uni)))},
    {"name": "economics", "kind": "subject",
     "gives": "study-pack rules for economics courses, plus a skill for intro macroeconomics",
     "keywords": {"economics", "economy", "כלכלה", "כלכלי"}},
]


def _plain(text: str) -> str:
    """Lowercase, keeping only letters and digits in any script (Hebrew included), so spelling drift still matches."""
    return "".join(c for c in str(text or "").casefold() if c.isalnum())


def recommend_plugins(university: str = "", field: str = "", course_name: str = "") -> list:
    """The plugins that fit this university and course, university plugins first. Never installs anything."""
    uni, subjects = _plain(university), [_plain(field), _plain(course_name)]  # matched apart: a keyword can't span the join
    return [p for p in PLUGIN_RECOMMENDATIONS
            if (p["kind"] == "university" and p["match"](uni))
            or (p["kind"] == "subject" and any(_plain(k) in t for k in p["keywords"] for t in subjects))]


def generated_university_file(university: str) -> Path:
    """A once-interviewed, cached fallback for a university with no installed plugin (ADR 0005)."""
    return home() / "generated" / _slug(university) / "site.md"


def generated_course_skill_file(field: str, course_name: str) -> Path:
    """A once-interviewed, cached study-pack fallback for a course with no installed course skill (ADR 0005)."""
    return home() / "generated" / _slug(field) / (_slug(course_name) + ".md")


def write_generated_reference(path: Path, heading: str, sections: list) -> None:
    """One interview-generate-persist mechanism, shared by the university and course/subject fallbacks (ADR 0005).

    `sections` is [(title, words)]; `words` is joined with spaces, matching how the CLI collects free text.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    body = (f"# {heading}\n\n"
            "Written once from the student's own description, not independently verified — "
            "a starting point, not gospel.\n\n")
    for title, words in sections:
        body += f"## {title}\n\n{' '.join(words)}\n\n"
    path.write_text(body, "utf-8")


def list_generated() -> list:
    """Every generated fallback on disk (university and course/subject), with a one-line preview."""
    folder = home() / "generated"
    out = []
    for path in sorted(folder.rglob("*.md")) if folder.is_dir() else []:
        lines = [l.strip() for l in path.read_text("utf-8").splitlines() if l.strip()]
        out.append({"path": str(path), "kind": "university" if path.name == "site.md" else "course",
                    "preview": lines[0].lstrip("# ") if lines else ""})
    return out


SETUP_STAGES = ["university", "course", "path", "format", "fetch-and-organize", "analyze", "capabilities"]


def _setup_progress_dir() -> Path:
    return home() / "setup-progress"


def setup_progress_file(course_name: str) -> Path:
    return _setup_progress_dir() / (safe_name(course_name) + ".json")


def read_setup_progress(course_name: str) -> dict:
    return _read_json(setup_progress_file(course_name), {"stage": None, "answers": {}})


def write_setup_progress(course_name: str, stage: str, answers: dict) -> dict:
    if stage not in SETUP_STAGES:
        raise ValueError(f"Unknown setup stage {stage!r}; must be one of {', '.join(SETUP_STAGES)}.")
    data = read_setup_progress(course_name)
    data["answers"].update(answers)
    data["stage"] = stage
    _write_json(setup_progress_file(course_name), data)
    return data


def clear_setup_progress(course_name: str):
    setup_progress_file(course_name).unlink(missing_ok=True)


def list_setup_progress() -> list:
    """Every course with setup started but not finished (finishing clears its file)."""
    folder = _setup_progress_dir()
    if not folder.is_dir():
        return []
    out = []
    for path in sorted(folder.glob("*.json")):
        data = _read_json(path, {"stage": None, "answers": {}})
        out.append({"course_name": data["answers"].get("course_name", path.stem),
                    "stage": data["stage"], "answers": data["answers"]})
    return out


def next_setup_stage(stage):
    if stage is None:
        return SETUP_STAGES[0]
    i = SETUP_STAGES.index(stage)
    return SETUP_STAGES[i + 1] if i + 1 < len(SETUP_STAGES) else None

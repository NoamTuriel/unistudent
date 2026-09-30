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
    "origin_mode": "own-folder",   # where material comes from: site | own-folder | both
    "recording_level": None,       # None (not asked yet) | 0 skip | 1 download only | 3 transcript + summary
    "recordings_dir": None,        # local non-synced folder when the course folder syncs
    "lecturer": None,
    "recording_segments": [],      # unit spans inside recordings: {"unit": 4, "from": "<rec> 00:00:00", "to": "<rec> 01:39:00"}
    "exam_date": None,
    "sort_patterns": [],
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

"""Course folder, Settings, Manifest and Registry (see CONTEXT.md)."""
import json
import os
import re
from pathlib import Path

STATE_DIR = ".unistudent"

LAYOUT = 2

# The visible folder names and the labels inside them, one table per language (ADR 0007). A new language is one
# more entry; a language with no entry falls back to English. The Hidden folder keeps English names.
LABELS = {
    "he": {"inbox": "1-קבצים-חדשים", "material": "2-חומרי-הקורס", "study": "3-{course}-ללמוד-מכאן",
           "official": "חומר-רשמי-של-הקורס", "added": "חומר-לא-רשמי", "unit": "יחידה {n}",
           "general": "חומר-כללי-לכל-היחידות", "unsorted": "עוד-לא-שויך-ליחידה", "roadmap": "מפת הקלטות",
           "lessons": "הקלטות מפגשים", "before_test": "לקראת מבחן", "question_pages": "עמודי שאלות"},
    "en": {"inbox": "1-inbox", "material": "2-course-material", "study": "3-{course}-study-from-here",
           "official": "official", "added": "added", "unit": "Unit {n}", "general": "General", "unsorted": "Unsorted",
           "roadmap": "Recordings roadmap", "lessons": "Recorded lessons",
           "before_test": "Before the test", "question_pages": "Question pages"},
}
# Hebrew names used before 0.5.0: still recognized (and renamed by `ensure_layout`) in folders made with them.
OLD_LABELS = [{"official": "רשמי", "added": "נוסף", "unit": "יחידה {n}", "general": "כללי", "unsorted": "לא ממוין"}]

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
    "layout": 1,                   # 2 once the course folder has the three visible folders (LAYOUT)
    "folders": {},                 # the visible folder names chosen at setup: inbox, material, study
}


def safe_name(name: str) -> str:
    """A file or folder name that is valid on every OS."""
    return re.sub(r'[\\/:*?"<>|#^\[\]]', "-", str(name)).strip() or "file"


def parse_unit(value):
    """A unit as stored: an int, "general" (whole course), "lessons" (Recorded lessons: recordings of whole class
    sessions, outside every unit), or None (unsorted)."""
    if value is None or value == "unsorted":
        return None
    if str(value).strip().lower() in ("general", "0"):
        return "general"
    if str(value).strip().lower() == "lessons":
        return "lessons"
    try:
        number = int(str(value).strip())
    except ValueError:
        raise ValueError(f"A unit is a number, 'general', 'lessons' or 'unsorted', not {value!r}.")
    if number < 0:
        raise ValueError(f"A unit number can't be negative: {value!r}.")
    return number


def parse_tier_folder(name):
    """"official" or "added" when `name` is a trust-level folder in any language, else None."""
    return next((t for table in (*LABELS.values(), *OLD_LABELS) for t in ("official", "added") if name == table[t]), None)


def parse_unit_folder(name):
    """(True, unit) when `name` is a unit folder in any language: a number, "general", "lessons" or None (unsorted)."""
    for table in (*LABELS.values(), *OLD_LABELS):
        if name == table["general"]:
            return True, "general"
        if name == table.get("lessons"):  # the pre-0.5.0 names had no lessons folder
            return True, "lessons"
        if name == table["unsorted"]:
            return True, None
        head, tail = table["unit"].split("{n}")
        match = re.fullmatch(re.escape(head) + r"(\d+)" + re.escape(tail), name)
        if match:
            return True, int(match.group(1))
    return False, None


def unit_dir(unit) -> str:
    """Internal folder name for a unit (Wiki pages, state)."""
    unit = parse_unit(unit)
    if unit is None:
        return "unsorted"
    if unit in ("general", "lessons"):
        return unit
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
    def wiki(self):
        return self.state / "wiki"

    def folder_names(self, language=None, course_name=None):
        """The three visible folder names: the stored ones, or those the labels table gives."""
        settings = self.settings()
        table = LABELS.get(language or settings["language"], LABELS["en"])
        name = safe_name(course_name or settings["course_name"] or self.root.name)
        computed = {k: table[k].format(course=name) for k in ("inbox", "material", "study")}
        return computed if language else {**computed, **settings.get("folders", {})}

    def _folder(self, key):
        return self.root / self.folder_names()[key]

    @property
    def material(self):
        return self._folder("material")

    @property
    def study(self):
        return self._folder("study")

    @property
    def inbox(self):
        return self._folder("inbox")

    def ensure_layout(self):
        """Create the Inbox and the Material folder in the settings' language (the Study vault only appears at the first
        Study pack, ADR 0008), renaming existing ones (and the trust-level and unit folders inside them) when it changed. Returns True when something was renamed. A rename that can't be done
        stops everything before anything changes: the Settings never say a folder has a name it doesn't have."""
        from .common import UserError
        settings = self.settings()
        wanted = self.folder_names(settings["language"])
        stored = settings.get("folders", {})
        renames = [(stored[k], name) for k, name in wanted.items()
                   if stored.get(k) and stored[k] != name and (self.root / stored[k]).is_dir()]
        for old, new in renames:
            if (self.root / new).exists() and not (self.root / new).samefile(self.root / old):
                raise UserError(f"Can't switch the folder names: \"{new}\" already exists next to \"{old}\". Nothing was "
                                f"changed. Move or rename \"{new}\" aside (or keep your files in \"{old}\") and try again.")
        done = []
        try:
            for old, new in renames:
                (self.root / old).rename(self.root / new)
                done.append((old, new))
        except OSError as error:
            for old, new in reversed(done):
                (self.root / new).rename(self.root / old)
            raise UserError(f"Can't rename the folder \"{old}\" to \"{new}\" ({error}). Nothing was changed. "
                            "Close anything that has it open and try again.")
        settings.update(layout=LAYOUT, folders=wanted)
        self.save_settings(settings)
        for key in ("inbox", "material"):
            (self.root / wanted[key]).mkdir(parents=True, exist_ok=True)
        inner = self._rename_inner(self.material, tiers=True) | (self.study.is_dir() and self._rename_inner(self.study))
        return bool(renames) or inner

    def _rename_inner(self, base, tiers=False):
        """Trust-level and unit folders inside `base` take the course language's names. Returns whether any changed."""
        def rename(folder, name):
            if folder.name == name or (folder.parent / name).exists():
                return folder, False
            return folder.rename(folder.parent / name), True

        changed = False
        for folder in sorted(p for p in base.iterdir() if p.is_dir()):
            tier = parse_tier_folder(folder.name) if tiers else None
            if tiers and not tier:
                continue
            if tier:
                folder, did = rename(folder, self.label(tier))
                changed |= did
                children = sorted(p for p in folder.iterdir() if p.is_dir())
            else:
                children = [folder]
            for child in children:
                known, unit = parse_unit_folder(child.name)
                if known:
                    changed |= rename(child, self.unit_folder(unit))[1]
        return changed

    def pack_folder(self, unit):
        """Where a unit's study pack lives in the Study vault (the vault itself is made by the first Study pack)."""
        return self.study / self.unit_folder(unit)

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
        """Folder name for a unit (in the Material folder and the Study vault), in the course language."""
        unit = parse_unit(unit)
        if unit is None:
            return self.label("unsorted")
        if unit in ("general", "lessons"):
            return self.label(unit)
        return self.label("unit", n=unit)

    def unit_label(self, unit):
        """A unit's title in the course language, for page content."""
        unit = parse_unit(unit)
        if unit is None:
            return self.label("unsorted")
        if unit in ("general", "lessons"):
            return self.label(unit)
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


SETUP_STAGES = ["university", "course", "language", "path", "format", "fetch", "sort", "recordings", "analyze", "capabilities"]
RENAMED_STAGES = {"fetch-and-organize": "recordings"}  # recorded by versions that had one step for fetch, sort and recordings


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
    i = SETUP_STAGES.index(RENAMED_STAGES.get(stage, stage))
    return SETUP_STAGES[i + 1] if i + 1 < len(SETUP_STAGES) else None

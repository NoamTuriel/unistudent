"""Course folder, Settings, Manifest and Registry (see CONTEXT.md)."""
import contextlib
import json
import os
import re
import time
from pathlib import Path

STATE_DIR = ".unistudent"
MANIFEST_LOCK_STALE = 120  # seconds; the lock is held only while the Manifest is read, changed and saved

LAYOUT = 2

# The visible folder names and the labels inside them, one table per language (ADR 0007): the built-in ones. Any other
# language gets its table translated once at setup and kept in the Settings (`labels`, see `Course.labels`); a key it
# lacks falls back to English. The Hidden folder keeps English names.
LABELS = {
    "he": {"inbox": "1-קבצים-חדשים", "material": "2-חומרי-הקורס", "study": "3-{course}-ללמוד-מכאן",
           "official": "חומר-רשמי-של-הקורס", "added": "חומר-לא-רשמי", "unit": "יחידה {n}",
           "general": "חומר-כללי-לכל-היחידות", "unsorted": "עוד-לא-שויך-ליחידה", "roadmap": "מפת הקלטות",
           "lessons": "הקלטות מפגשים", "before_test": "לקראת מבחן", "question_pages": "עמודי שאלות",
           "model_answer": "תשובה לדוגמה", "say_it": "ככה אומרים", "sources": "מקורות", "from": "מתוך"},
    "en": {"inbox": "1-inbox", "material": "2-course-material", "study": "3-{course}-study-from-here",
           "official": "official", "added": "added", "unit": "Unit {n}", "general": "General", "unsorted": "Unsorted",
           "roadmap": "Recordings roadmap", "lessons": "Recorded lessons",
           "before_test": "Before the test", "question_pages": "Question pages",
           "model_answer": "Model answer", "say_it": "Say it", "sources": "Sources", "from": "From"},
}
# Hebrew names used before 0.5.0: still recognized (and renamed by `ensure_layout`) in folders made with them.
OLD_LABELS = [{"official": "רשמי", "added": "נוסף", "unit": "יחידה {n}", "general": "כללי", "unsorted": "לא ממוין"}]

DEFAULT_SETTINGS = {
    "course_name": "",
    "language": "en",            # the course language; `us setup` asks for it, so no course gets it by default
    "format": "obsidian",          # obsidian | markdown
    "university": None,            # e.g. "openu"; None → core only
    "recording_level": None,       # None (not asked yet) | 0 skip | 1 download only | 3 transcript + summary
    "frame_analysis": None,        # None (not asked yet) | True | False: per-segment vision calls (opt-in, costly)
    "keep_video": None,            # None (not asked yet: kept) | True | False: keep only an audio-only copy of each recording
    "recordings_dir": None,        # local non-synced folder when the course folder syncs
    "exam_date": None,
    "layout": 1,                   # 2 once the course folder has the three visible folders (LAYOUT)
    "folders": {},                 # the visible folder names chosen at setup: inbox, material, study
    "labels": {},                  # a language with no built-in LABELS table: its labels, translated once at setup
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


def parse_tier_folder(name, tables):
    """"official" or "added" when `name` is a trust-level folder in any of `tables` (a course's `label_tables()`),
    else None."""
    return next((t for table in tables for t in ("official", "added") if name == table[t]), None)


def parse_unit_folder(name, tables):
    """(True, unit) when `name` is a unit folder in any of `tables` (a course's `label_tables()`): a number,
    "general", "lessons" or None (unsorted)."""
    for table in tables:
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


def _retry(action):
    """Run `action`, retrying for up to 2 s on PermissionError: Windows refuses to replace or open a file while another
    command has it open for a moment, where macOS and Linux never refuse."""
    for _ in range(40):
        try:
            return action()
        except PermissionError:
            time.sleep(0.05)
    return action()


def _read_json(path: Path, default):
    try:
        return json.loads(_retry(lambda: path.read_text("utf-8")))
    except FileNotFoundError:
        return default


def _write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")  # two commands at once never share one
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), "utf-8")
    _retry(lambda: os.replace(tmp, path))  # atomic, so an interrupted run never leaves half a file


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
        table = self.labels()
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

    def ensure_layout(self, old_labels=None):
        """Create the Inbox and the Material folder in the settings' language (the Study vault only appears at the first
        Study pack, ADR 0008), renaming existing ones (and the trust-level and unit folders inside them) when it changed. Returns True when something was renamed. A rename that can't be done
        stops everything before anything changes: the Settings never say a folder has a name it doesn't have. `old_labels`:
        the course's own labels before a language change, so folders named by them are recognized and renamed too."""
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
        tables = (*self.label_tables(), *([{**LABELS["en"], **old_labels}] if old_labels else []))
        inner = self._rename_inner(self.material, tables, tiers=True) | (self.study.is_dir()
                                                                          and self._rename_inner(self.study, tables))
        return bool(renames) or inner

    def _rename_inner(self, base, tables, tiers=False):
        """Trust-level and unit folders inside `base` take the course language's names. Returns whether any changed."""
        def rename(folder, name):
            if folder.name == name or (folder.parent / name).exists():
                return folder, False
            return folder.rename(folder.parent / name), True

        changed = False
        for folder in sorted(p for p in base.iterdir() if p.is_dir()):
            tier = parse_tier_folder(folder.name, tables) if tiers else None
            if tiers and not tier:
                continue
            if tier:
                folder, did = rename(folder, self.label(tier))
                changed |= did
                children = sorted(p for p in folder.iterdir() if p.is_dir())
            else:
                children = [folder]
            for child in children:
                known, unit = parse_unit_folder(child.name, tables)
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
        data.pop("course_skill", None)  # left by versions that had course skills (ADR 0011)
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

    @contextlib.contextmanager
    def edit_manifest(self):
        """Read, change and save the Manifest holding a lock file, so two commands running at once (a recording
        ingested during a document ingest) never lose each other's entries. Saved only when the block ends without an
        error."""
        with self.locked("manifest.lock"):
            manifest = self.manifest()
            yield manifest
            self.save_manifest(manifest)

    @contextlib.contextmanager
    def locked(self, name):
        """Hold the lock file `name` in the Hidden folder for the block. A lock older than MANIFEST_LOCK_STALE was left
        by a run that died, and is taken over."""
        lock = self.state / name
        while True:
            try:
                os.close(os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                break
            except (FileExistsError, PermissionError):  # Windows says PermissionError while a lock is being deleted
                try:
                    if time.time() - lock.stat().st_mtime > MANIFEST_LOCK_STALE:
                        lock.unlink()  # ponytail: two waiters may both take over a stale lock; only after a crash
                except OSError:
                    pass
                time.sleep(0.05)
        try:
            yield
        finally:
            lock.unlink(missing_ok=True)

    def read_state(self, name, default):
        return _read_json(self.state / name, default)

    def write_state(self, name, data):
        _write_json(self.state / name, data)

    def labels(self):
        """This course's label table: the student's own (Settings `labels`, translated at setup for a language with no
        built-in table) over the built-in table of the course language, English for any key missing."""
        settings = self.settings()
        return {**LABELS["en"], **LABELS.get(settings["language"], {}), **settings.get("labels", {})}

    def label_tables(self):
        """Every table a folder name of this course may come from: the built-in ones, the older names, and its own."""
        return (*LABELS.values(), *OLD_LABELS, self.labels())

    def line_words(self, key):
        """The words a "Sources:" or "From:" line (`key`) may open with: the English one always, and the course
        language's."""
        return {LABELS["en"][key], self.label(key)}

    def label(self, key, **kw):
        return self.labels()[key].format(**kw)

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


# The university-to-plugin mapping, in one place (ticket 12). A university plugin is matched by its own test on the
# normalized name ("Open University UK" must not match the Israeli one). One entry per plugin.
PLUGIN_RECOMMENDATIONS = [
    {"name": "openu",
     "gives": "downloads new material from your Open University of Israel course site",
     "match": lambda uni: (uni == "oui" or "פתוחה" in uni or "openu" in uni.replace("openuniversity", "")
                           or ("openuniversity" in uni and ("israel" in uni or "ישראל" in uni)))},
]


# The Tool list (ADR 0012): self-installing kinds and Recommended tools, hardcoded, each proven by one sample call in
# CI (.github/workflows/tool-list.yml). Empty until a real course shows a picture no existing kind draws. Entry shape:
#   {"name": "circuit",                      # what the student says in chat; `us tools add <name>`
#    "label": "circuit drawer",              # the plain name the roadmap sentence uses
#    "draws": "electric circuits",           # what it draws, in words
#    "kinds": ["circuit"],                   # the Presentation kind words it serves
#    "install": {"python": "<package>"} or {"mcp": ["<command>", "<arg>", ...], "node": True},
#    "sample": "<a short text spec the CI job draws once>"}
TOOL_LIST = []

def _plain(text: str) -> str:
    """Lowercase, keeping only letters and digits in any script (Hebrew included), so spelling drift still matches."""
    return "".join(c for c in str(text or "").casefold() if c.isalnum())


def recommend_plugins(university: str) -> list:
    """The plugins that fit this university. Never installs anything."""
    return [p for p in PLUGIN_RECOMMENDATIONS if p["match"](_plain(university))]


def generated_university_file(university: str) -> Path:
    """A once-interviewed, cached fallback for a university with no installed plugin (ADR 0005)."""
    return home() / "generated" / _slug(university) / "site.md"


def list_generated() -> list:
    """Every generated university fallback on disk, with a one-line preview."""
    folder = home() / "generated"
    out = []
    for path in sorted(folder.rglob("site.md")) if folder.is_dir() else []:  # other files are course rules from before ADR 0011
        lines = [l.strip() for l in path.read_text("utf-8").splitlines() if l.strip()]
        out.append({"path": str(path),
                    "preview": lines[0].lstrip("# ") if lines else ""})
    return out


# The question block (language .. installs), the Fetch plan (plan), the unattended run (run), then capabilities.
SETUP_STAGES = ["language", "university", "course", "path", "format", "material", "recordings", "installs", "plan",
                "run", "capabilities"]
# Stages recorded by older versions, read as the new stage they finished: fetch-and-organize was one step for fetch,
# sort and the recordings question; fetch and sort brought the material in; analyze built the Wiki (the run's end).
RENAMED_STAGES = {"fetch-and-organize": "recordings", "fetch": "material", "sort": "material", "analyze": "run"}


# The answers step 7 applies, by the stage that asks them. A setup started on an older version may have passed the
# stage without them: they are asked again before step 7, never guessed.
STAGE_ANSWERS = {"material": ["source"], "recordings": ["transcribe", "frame_analysis", "keep_video"]}


def missing_setup_answers(data) -> list:
    """The answers of stages already done that step 7 (`installs`) still needs; none once it is done."""
    if data["stage"] is None:
        return []
    done = SETUP_STAGES[:SETUP_STAGES.index(RENAMED_STAGES.get(data["stage"], data["stage"])) + 1]
    if "installs" in done:
        return []
    return [k for stage in done for k in STAGE_ANSWERS.get(stage, []) if k not in data["answers"]]


def _setup_progress_dir() -> Path:
    return home() / "setup-progress"


def setup_progress_file(course_name: str) -> Path:
    return _setup_progress_dir() / (safe_name(course_name) + ".json")


def read_setup_progress(course_name: str) -> dict:
    return _read_json(setup_progress_file(course_name), {"stage": None, "answers": {}})


def write_setup_progress(course_name: str, stage: str, answers: dict) -> dict:
    stage = RENAMED_STAGES.get(stage, stage)
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

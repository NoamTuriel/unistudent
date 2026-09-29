"""Bringing files into Raw and keeping the readable by-unit layout (materials/) in step.

Raw holds the only real copy of each file. Files from the student's own folder stay
where they are and Raw links to them; downloaded and inbox files live in Raw itself.
materials/ is rebuilt from the Manifest and is made of links only (ADR 0003).
"""
import hashlib
import os
import shutil
from pathlib import Path

from . import links
from .sorting import detect_unit

SKIP_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
INDEX_NAME = "INDEX.md"


def fingerprint(path: Path) -> str:
    """Cheap, stable identity: size + hash of the first and last MiB (recordings are GBs)."""
    size = path.stat().st_size
    digest = hashlib.sha256(str(size).encode())
    with open(path, "rb") as handle:
        digest.update(handle.read(1 << 20))
        if size > 2 << 20:
            handle.seek(-(1 << 20), os.SEEK_END)
            digest.update(handle.read(1 << 20))
    return digest.hexdigest()[:24]


def iter_files(folder: Path):
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for name in sorted(filenames):
            if name.startswith(".") or name in SKIP_NAMES or name.endswith(".tmp"):
                continue
            yield Path(dirpath) / name


def _entry_unit(course, rel, file_path):
    settings = course.settings()
    answers = settings.get("unit_answers", {})
    if rel in answers:
        return answers[rel], "student answer"
    return detect_unit(rel, file_path, settings.get("sort_patterns", []))


def _free_rel(files, rel, source_path, prefix):
    existing = files.get(rel)
    if existing is None or existing.get("source_path") == str(source_path):
        return rel
    return f"{prefix}/{rel}"


def import_folder(course, folder, tier="added", origin="student-folder"):
    """Register every file of `folder` without copying. Returns the list of new Raw paths."""
    folder = Path(folder).resolve()
    manifest = course.manifest()
    files = manifest["files"]
    added = []
    for path in iter_files(folder):
        rel = _free_rel(files, path.relative_to(folder).as_posix(), path, folder.name)
        fp = fingerprint(path)
        entry = files.get(rel)
        if entry is None:
            added.append(rel)
        elif entry.get("fingerprint") != fp:
            added.append(rel)  # changed on disk: re-registered below
        unit, reason = _entry_unit(course, rel, path)
        files[rel] = {
            "origin": origin,
            "tier": tier,
            "source_path": str(path),
            "size": path.stat().st_size,
            "fingerprint": fp,
            "unit": unit,
            "sort_reason": reason,
        }
        links.make_link(path, course.raw / rel)
    course.save_manifest(manifest)
    rebuild_materials(course)
    return added


def add_file(course, path, tier="added", origin="inbox", rel=None, move=True):
    """Put one file into Raw as a real file (inbox and downloads). Returns its Raw path."""
    path = Path(path)
    manifest = course.manifest()
    files = manifest["files"]
    rel = rel or f"{origin}/{path.name}"
    base, n = rel, 2
    while rel in files and files[rel].get("fingerprint") != fingerprint(path):
        stem, suffix = os.path.splitext(base)
        rel, n = f"{stem} ({n}){suffix}", n + 1
    target = course.raw / rel
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.resolve() != path.resolve():
        if move:
            shutil.move(str(path), str(target))
        else:
            shutil.copy2(path, target)
    unit, reason = _entry_unit(course, rel, target)
    files[rel] = {
        "origin": origin,
        "tier": tier,
        "source_path": str(target),
        "size": target.stat().st_size,
        "fingerprint": fingerprint(target),
        "unit": unit,
        "sort_reason": reason,
    }
    course.save_manifest(manifest)
    return rel


def assign(course, rel, unit):
    """Record the student's answer for one unsorted file (kept across re-imports)."""
    manifest = course.manifest()
    if rel not in manifest["files"]:
        raise KeyError(rel)
    value = "general" if str(unit) in ("general", "0") else int(unit)
    settings = course.settings()
    settings.setdefault("unit_answers", {})[rel] = value
    course.save_settings(settings)
    manifest["files"][rel]["unit"] = value
    manifest["files"][rel]["sort_reason"] = "student answer"
    course.save_manifest(manifest)
    rebuild_materials(course)


def unsorted(course):
    return sorted(rel for rel, e in course.manifest()["files"].items() if e.get("unit") is None)


def raw_path(course, rel):
    """Where the file can be opened: Raw if a link/file exists there, else its original path."""
    raw = course.raw / rel
    if raw.exists():
        return raw
    return Path(course.manifest()["files"][rel]["source_path"])


def rebuild_materials(course):
    """Recreate materials/ from the Manifest. Only removes what it made itself."""
    made = course.read_state("materials.json", [])
    for rel in made:
        path = course.materials / rel
        if path.is_symlink() or path.exists():
            links.remove_link(path)
    for dirpath, dirnames, _ in os.walk(course.materials, topdown=False):
        for d in dirnames:
            try:
                (Path(dirpath) / d).rmdir()
            except OSError:
                pass

    by_folder = {}
    for rel, entry in sorted(course.manifest()["files"].items()):
        by_folder.setdefault(course.unit_label(entry.get("unit")), []).append(rel)

    made = []
    for folder, rels in by_folder.items():
        unlinked = []
        used = set()
        for rel in rels:
            name = Path(rel).name
            stem, suffix = os.path.splitext(name)
            n = 2
            while name in used:
                name, n = f"{stem} ({n}){suffix}", n + 1
            used.add(name)
            link_rel = f"{folder}/{name}"
            if links.make_link(raw_path(course, rel), course.materials / link_rel):
                made.append(link_rel)
            else:
                unlinked.append((name, rel))
        if unlinked:
            index = course.materials / folder / INDEX_NAME
            index.parent.mkdir(parents=True, exist_ok=True)
            lines = [f"# {folder}", ""]
            for name, rel in unlinked:
                lines.append(f"- [{name}]({raw_path(course, rel).as_uri()})")
            index.write_text("\n".join(lines) + "\n", "utf-8")
            made.append(f"{folder}/{INDEX_NAME}")
    course.write_state("materials.json", made)

"""The Material folder: the real files of the course, sorted by trust level and unit (ADR 0007).

Layout: <Material folder>/<official|added>/<unit folder>/<file>. Where a file sits is the truth: `scan` reads the
folder, follows moved or renamed files by fingerprint, drops deleted ones and takes new ones as added. Files from the
site and the Inbox are moved in; a student's own folder is copied once and the originals are left alone.
"""
import hashlib
import os
import platform
import shutil
import unicodedata
from pathlib import Path

from .common import UserError
from .convert import kind
from .course import LAYOUT, parse_tier_folder, parse_unit, parse_unit_folder, safe_name
from .sorting import detect_unit

SKIP_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}
FULL_HASH_LIMIT = 200 << 20


def fingerprint(path: Path) -> str:
    """Content identity. Files up to 200 MB are hashed whole; bigger ones (recordings)
    by size, modification time and their first and last MiB, to stay fast."""
    stat = path.stat()
    digest = hashlib.sha256(str(stat.st_size).encode())
    with open(path, "rb") as handle:
        if stat.st_size <= FULL_HASH_LIMIT:
            for chunk in iter(lambda: handle.read(1 << 20), b""):
                digest.update(chunk)
        else:
            digest.update(str(int(stat.st_mtime)).encode())
            digest.update(handle.read(1 << 20))
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


def _entry(path, origin, tier, unit, reason, **extra):
    return {"origin": origin, "tier": tier, "size": path.stat().st_size, "mtime": path.stat().st_mtime_ns,
            "fingerprint": fingerprint(path),
            "unit": unit, "sort_reason": reason, **extra}


def _key(name):
    return unicodedata.normalize("NFC", name).casefold()


def _free_name(folder: Path, name: str, taken=()):
    stem, suffix = os.path.splitext(name)
    candidate, n = name, 2
    taken = {_key(t) for t in taken}
    while (folder / candidate).exists() or _key(candidate) in taken:
        candidate, n = f"{stem} ({n}){suffix}", n + 1
    return candidate


def wiki_folders(files):
    """{recording rel: its Wiki folder}. A folder, once given, stays in the Manifest entry, so a recording that is
    renamed or moved between trust levels keeps its transcript and summary, and a newcomer of the same name can't take them."""
    used = {e["wiki_folder"] for e in files.values() if e.get("wiki_folder")}
    out = {}
    for rel, entry in sorted(files.items()):
        if kind(rel) != "recording":
            continue
        folder = entry.get("wiki_folder")
        if not folder:
            stem = safe_name(Path(rel).stem)
            folder, n = f"recordings/{stem}", 2
            while folder in used:
                folder, n = f"recordings/{stem} ({n})", n + 1
            used.add(folder)
        out[rel] = folder
    return out


def assign_wiki_folders(files):
    for rel, folder in wiki_folders(files).items():
        files[rel]["wiki_folder"] = folder


def _slot(course, tier, unit):
    return f"{course.label(tier)}/{course.unit_folder(unit)}"


LEGACY = ("This course folder has the old layout (raw, materials, wiki, study), which this version no longer reads. "
          "Install UniStudent 0.4.2 once and run `us migrate --apply` there, then update again.")
WINDOWS_PATH_LIMIT = 240  # Windows stops at 260 characters; keep room for what is added after the name


def require_new_layout(course):
    if course.settings().get("layout") != LAYOUT:
        raise UserError(LEGACY)


def check_path_length(path):
    """On Windows a path over ~260 characters fails half-way; refuse early, with what to do about it."""
    if platform.system() == "Windows" and len(str(path)) > WINDOWS_PATH_LIMIT:
        raise UserError(f"This path is too long for Windows ({len(str(path))} characters): {path}. Shorten the file's "
                        "name, or move the course folder to a shorter place such as C:\\Courses, then try again.")


def _put(course, path, rel, copy):
    """Place `path` at `rel` in the Material folder: a copy (own folder) or a move (Inbox, site). Recordings of a
    course folder that syncs are kept in a local, non-synced folder instead; returns where the file now is.
    The file arrives under a temporary name first, so an update never loses the copy that is already there."""
    recordings_dir = course.settings().get("recordings_dir")
    keep = Path(recordings_dir) / rel if recordings_dir and kind(path) == "recording" else course.material / rel
    check_path_length(course.state / "wiki" / "sources" / "unit-00" / (keep.name + ".md"))
    check_path_length(keep)
    keep.parent.mkdir(parents=True, exist_ok=True)
    if keep.exists() and keep.samefile(path):
        return keep
    part = keep.with_name(keep.name + ".tmp")
    try:
        (shutil.copy2 if copy else shutil.move)(str(path), str(part))
    except BaseException:
        part.unlink(missing_ok=True)
        raise
    os.replace(part, keep)
    return keep


def add_file(course, path, tier="added", origin="inbox", hint=None, replace_rel=None, note=None, copy=False,
             site_unit=None, extra=None, name=None):
    """Put one file into the Material folder, sorted by tier and unit. `hint` is where it sat in its own folder
    (unit evidence). `replace_rel` updates that file in place (a newer version from the site) wherever the student
    has put it. Returns the file's path relative to the Material folder."""
    require_new_layout(course)
    path = Path(path)
    name = name or path.name
    manifest = course.manifest()
    files = manifest["files"]
    stale = None
    if replace_rel in files:
        rel = replace_rel
        old = files.pop(rel)
        tier, unit, reason = old["tier"], old.get("unit"), old.get("sort_reason")
        stale = Path(old.get("stored_at") or course.material / rel)
        if Path(name).suffix.lower() != Path(rel).suffix.lower():  # the new version is another kind of file
            rel = os.path.splitext(rel)[0] + Path(name).suffix
            if (course.material / rel).exists():
                rel = f"{os.path.dirname(rel)}/{_free_name((course.material / rel).parent, Path(rel).name)}"
    else:
        unit, reason = (site_unit, "site listing") if site_unit is not None else detect_unit(hint or name, path)
        slot = _slot(course, tier, unit)
        target = course.material / slot / name
        if target.exists() and fingerprint(target) == fingerprint(path):
            if not copy:
                path.unlink()
            return f"{slot}/{name}"  # the same file again: nothing new to keep
        rel = f"{slot}/{_free_name(target.parent, name)}"
    stored = _put(course, path, rel, copy)
    if stale and stale.exists() and not stale.samefile(stored):  # only now that the new copy is in place
        stale.unlink()
    entry = _entry(stored, origin, tier, unit, reason, **(extra or {}))
    if stored != course.material / rel:
        entry["stored_at"] = str(stored)
    if note:
        entry["origin_note"] = note
    files[rel] = entry
    assign_wiki_folders(files)
    course.save_manifest(manifest)
    return rel


def import_folder(course, folder, tier="added"):
    """Copy every file of the student's own `folder` into the Material folder, once; the originals stay.
    Returns the new or changed files' paths."""
    require_new_layout(course)
    folder = Path(folder).resolve()
    scan(course)  # the student may have moved or renamed what was copied before: know where it is now
    added = []
    for path in iter_files(folder):
        files = course.manifest()["files"]
        origin_path = str(path)
        before = next((r for r, e in files.items() if e.get("imported_from") == origin_path), None)
        if before and files[before].get("fingerprint") == fingerprint(path):
            continue  # copied once already: never again
        rel = add_file(course, path, tier=tier, origin="student-folder", hint=path.relative_to(folder).as_posix(),
                       replace_rel=before, copy=True, extra={"imported_from": origin_path})
        added.append(rel)
    return added


def assign(course, rel, unit):
    """Answer for one unsorted file: move it into its unit's folder. Returns its new path."""
    require_new_layout(course)
    manifest = course.manifest()
    files = manifest["files"]
    if rel not in files:
        raise KeyError(rel)
    entry = files.pop(rel)
    value = parse_unit(unit)
    new_rel = f"{_slot(course, entry['tier'], value)}/{Path(rel).name}"
    if entry.get("stored_at") is None and new_rel != rel:
        target = course.material / new_rel
        new_rel = f"{_slot(course, entry['tier'], value)}/{_free_name(target.parent, target.name)}"
        (course.material / new_rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(course.material / rel), str(course.material / new_rel))
    entry.update(unit=value, sort_reason="student answer")
    files[new_rel] = entry
    course.save_manifest(manifest)
    return new_rel


def unsorted(course):
    return sorted(rel for rel, e in course.manifest()["files"].items() if e.get("unit") is None)


def path_of(course, rel):
    """Where the file can be opened."""
    entry = course.manifest()["files"].get(rel, {})
    return Path(entry.get("stored_at") or course.material / rel)


def _is_sidecar(path: Path) -> bool:
    """A transcript .vtt written next to its recording: ours, not course material."""
    return path.suffix.lower() == ".vtt" and any(
        sibling.stem == path.stem and kind(sibling) == "recording" for sibling in path.parent.iterdir())


def _location(rel):
    """(tier, unit, in_slot, loose): what a file's place in the Material folder says. `in_slot` is False when the file
    isn't under <trust level>/<unit folder>/; `loose` when it sits straight in the Material folder or straight in a
    trust-level folder, which is where UniStudent sorts it into a unit folder (a folder the student made is left alone)."""
    parts = Path(rel).parts
    tier = parse_tier_folder(parts[0]) if len(parts) > 1 else None
    known, unit = parse_unit_folder(parts[1]) if tier and len(parts) > 2 else (False, None)
    return tier, unit, known, len(parts) == 1 or (tier is not None and len(parts) == 2)


def _icloud_placeholders(folder: Path):
    """Files iCloud has moved out of the folder but still lists as `.name.icloud`: present, not deleted."""
    for dirpath, _, filenames in os.walk(folder):
        for name in filenames:
            if name.startswith(".") and name.endswith(".icloud"):
                yield (Path(dirpath) / name[1:-len(".icloud")]).relative_to(folder).as_posix()


def _twin(gone, rel, fp):
    """The deleted Manifest entry a new file most likely is: same content, preferably from the same folder, then
    the same name, so identical copies do not swap their notes."""
    twins = [r for r, e in gone.items() if e.get("fingerprint") == fp]
    parent, name = os.path.dirname(rel), os.path.basename(rel)
    return next((r for r in twins if os.path.dirname(r) == parent), None) or \
        next((r for r in twins if os.path.basename(r) == name), None) or (twins[0] if twins else None)


def scan(course):
    """Make the Manifest match the Material folder (where a file sits is the truth). Follows moves and renames by
    fingerprint, drops deleted files and takes new ones as added, sorting them into a unit when the evidence is clear
    (and into that unit's folder, so the folder tells the truth). Returns {moved, dropped, new}.
    An emptied or missing Material folder is never read as "the student deleted everything": it stops, changing nothing."""
    result = {"moved": [], "dropped": [], "new": []}
    manifest = course.manifest()
    files = manifest["files"]
    if not course.material.is_dir():
        raise UserError(f"The Material folder is missing ({course.material}). Nothing was changed. Put it back "
                        "(or restore it from the Trash) and run this again.")
    found = {p.relative_to(course.material).as_posix(): p for p in iter_files(course.material) if not _is_sidecar(p)}
    away = set(_icloud_placeholders(course.material))
    gone = {rel: e for rel, e in files.items()
            if rel not in found and rel not in away and not (e.get("stored_at") and Path(e["stored_at"]).exists())}
    if files and not found and not away and len(gone) == len(files):
        raise UserError(f"The Material folder ({course.material.name}) looks empty, but UniStudent remembers "
                        f"{len(files)} files in it. Nothing was changed. If a sync or drive is not ready, wait and run this "
                        "again; if you really removed them all, restore them from the Trash first.")
    kept = {rel: e for rel, e in files.items() if rel not in gone}
    misplaced = []
    for rel, path in sorted(found.items()):
        stat = path.stat()
        entry = kept.get(rel)
        fresh = entry is None
        if not fresh and entry.get("mtime") == stat.st_mtime_ns and entry.get("size") == stat.st_size:
            fp = entry["fingerprint"]
        else:
            fp = fingerprint(path)
        if fresh:
            twin = _twin(gone, rel, fp)
            if twin:
                entry = gone.pop(twin)
                result["moved"].append((twin, rel))
            else:
                entry = {"origin": "material-folder"}
                result["new"].append(rel)
        tier, unit, known, loose = _location(rel)
        entry["tier"] = tier or entry.get("tier", "added")
        if known:
            if entry.get("unit") != unit:
                entry.update(unit=unit, sort_reason="folder")
        elif rel in result["new"]:
            entry["unit"], entry["sort_reason"] = detect_unit(rel, path)
            if loose:
                misplaced.append(rel)
        entry.update(fingerprint=fp, size=stat.st_size, mtime=stat.st_mtime_ns)
        kept[rel] = entry
    for rel in misplaced:
        entry = kept.pop(rel)
        slot = _slot(course, entry["tier"], entry["unit"])
        (course.material / slot).mkdir(parents=True, exist_ok=True)
        name = _free_name(course.material / slot, Path(rel).name)
        shutil.move(str(course.material / rel), str(course.material / slot / name))
        kept[f"{slot}/{name}"] = entry
        result["new"] = [f"{slot}/{name}" if r == rel else r for r in result["new"]]
        result["moved"] = [(a, f"{slot}/{name}" if b == rel else b) for a, b in result["moved"]]
    result["dropped"] = sorted(gone)
    manifest["files"] = kept
    assign_wiki_folders(kept)
    course.save_manifest(manifest)
    return result

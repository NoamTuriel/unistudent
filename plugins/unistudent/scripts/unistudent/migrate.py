"""Moving a course folder from the old layout (raw, materials, wiki, study) to the new one (ADR 0007).

`plan` lists every move without touching anything; `apply` does them. Safe to run again: a file already in place with
the same content counts as done, and a different file in the way stops everything before the first move.
"""
import json
import os
import re
import shutil
from pathlib import Path

from . import material
from .common import UserError
from .course import LAYOUT, STATE_DIR

OLD_UNIT_FOLDER = re.compile(r"^Unit (\d+)$")


def _same(a: Path, b: Path) -> bool:
    return b.exists() and material.fingerprint(a) == material.fingerprint(b)


def _free(taken, rel):
    stem, suffix = os.path.splitext(rel)
    candidate, n = rel, 2
    while candidate in taken:
        candidate, n = f"{stem} ({n}){suffix}", n + 1
    taken.add(candidate)
    return candidate


def _vault_name(course, part):
    """The old study folders were English (Unit 4); the vault's follow the course language."""
    match = OLD_UNIT_FOLDER.match(part)
    if match:
        return course.unit_folder(int(match.group(1)))
    return {"General": course.unit_folder("general"), "Unsorted": course.unit_folder(None)}.get(part, part)


def plan(course):
    """{moves: [{kind, how, from, to}], conflicts: [...], missing: [...], names, files: {old rel: new rel}}"""
    settings = course.settings()
    names = course.folder_names(settings["language"])
    root, moves, conflicts, missing, files = course.root, [], [], [], {}
    recordings_dir = settings.get("recordings_dir")

    def add(kind, how, src, dst):
        shown = Path(src).relative_to(root).as_posix() if Path(src).is_relative_to(root) else str(src)
        moves.append({"kind": kind, "how": how, "from": shown, "to": Path(dst).relative_to(root).as_posix()})
        if how in ("move", "copy") and Path(dst).exists() and not _same(Path(src), Path(dst)):
            conflicts.append(moves[-1]["to"])

    taken = set()
    for rel, entry in sorted(course.manifest()["files"].items()):
        src = course.raw / rel
        real = Path(os.path.realpath(src)) if src.is_symlink() else src
        if not real.is_file():
            missing.append(rel)
            continue
        slot = f"{course.label(entry['tier'])}/{course.unit_folder(entry.get('unit'))}"
        new = _free(taken, f"{slot}/{Path(rel).name}")
        files[rel] = new
        stored = recordings_dir and src.is_symlink() and real.is_relative_to(Path(recordings_dir).resolve())
        dst = root / names["material"] / new
        if stored:
            moves.append({"kind": "file", "how": "keep", "from": str(real), "to": f"(stays in {recordings_dir})"})
        else:
            add("file", "copy" if src.is_symlink() else "move", real, dst)
    if (root / "wiki").is_dir():
        target = course.state / "wiki"
        if target.exists() and any(target.iterdir()):
            conflicts.append(f"{STATE_DIR}/wiki")
        moves.append({"kind": "wiki", "how": "move", "from": "wiki", "to": f"{STATE_DIR}/wiki"})
    for old, key in (("study", "study"), ("inbox", "inbox")):
        for path in material.iter_files(root / old) if (root / old).is_dir() else []:
            parts = path.relative_to(root / old).parts
            if old == "study":
                parts = (_vault_name(course, parts[0]), *parts[1:]) if len(parts) > 1 else parts
            add(old, "move", path, root / names[key] / Path(*parts))
    for rel in course.read_state("materials.json", []):
        if (course.root / "materials" / rel).is_symlink() or (course.root / "materials" / rel).exists():
            moves.append({"kind": "links", "how": "remove", "from": f"materials/{rel}", "to": "-"})
    return {"moves": moves, "conflicts": sorted(set(conflicts)), "missing": missing, "names": names, "files": files}


def _prune(folder: Path):
    """Remove `folder` and the empty folders under it, leaving anything that still holds a file."""
    for dirpath, _, _ in os.walk(folder, topdown=False):
        try:
            os.rmdir(dirpath)
        except OSError:
            pass


def apply(course, found):
    """Do the moves of `plan`. Returns what was left behind, if anything."""
    root, names, recordings_dir = course.root, found["names"], course.settings().get("recordings_dir")
    if found["conflicts"]:
        raise UserError("Nothing was moved: these places already hold a different file, so the move would overwrite "
                        "it. Rename or move them aside and run `us migrate` again: " + ", ".join(found["conflicts"]))
    for name in names.values():
        (root / name).mkdir(parents=True, exist_ok=True)
    manifest = course.manifest()
    new_files = {}
    for old, new in found["files"].items():
        entry = manifest["files"][old]
        src = course.raw / old
        link = src.is_symlink()
        real = Path(os.path.realpath(src)) if link else src
        dst = root / names["material"] / new
        stored = recordings_dir and link and real.is_relative_to(Path(recordings_dir).resolve())
        if not stored:
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():  # an earlier, interrupted run got here
                if not link:
                    src.unlink()
            else:
                (shutil.copy2 if link else shutil.move)(str(real), str(dst))
            if link:
                src.unlink()
        final = real if stored else dst
        if not final.exists():
            continue
        entry = {k: v for k, v in entry.items() if k != "source_path"}
        if entry.get("origin") == "student-folder" and link:
            entry["imported_from"] = str(real)
        entry.update(fingerprint=material.fingerprint(final), size=final.stat().st_size)
        if stored:
            entry["stored_at"] = str(final)
        new_files[new] = entry
    manifest["files"] = new_files
    course.save_manifest(manifest)
    state = course.read_state("wiki.json", {})
    by_new = {old: new for old, new in found["files"].items() if new in new_files}
    course.write_state("wiki.json", {by_new[o]: i for o, i in state.items() if o in by_new})

    if (root / "wiki").is_dir():
        target = course.state / "wiki"
        if target.exists():
            target.rmdir()
        shutil.move(str(root / "wiki"), str(target))
        for page in target.rglob("*.md"):
            text = page.read_text("utf-8")
            patched = text
            for old, new in by_new.items():
                patched = patched.replace(f"source: {old}\n", f"source: {new}\n", 1)
            if patched != text:
                page.write_text(patched, "utf-8")
    for old, key in (("study", "study"), ("inbox", "inbox")):
        for path in list(material.iter_files(root / old)) if (root / old).is_dir() else []:
            parts = path.relative_to(root / old).parts
            if old == "study" and len(parts) > 1:
                parts = (_vault_name(course, parts[0]), *parts[1:])
            dst = root / names[key] / Path(*parts)
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists():
                path.unlink()
            else:
                shutil.move(str(path), str(dst))
            if old == "study" and dst.suffix == ".md":  # the Wiki moved into the Hidden folder
                text = dst.read_text("utf-8")
                dst.write_text(text.replace("(../../wiki/", f"(../../{STATE_DIR}/wiki/"), "utf-8")
    for rel in course.read_state("materials.json", []):
        link = root / "materials" / rel
        if link.is_symlink() or link.is_file():
            link.unlink()
    (course.state / "materials.json").unlink(missing_ok=True)
    settings = course.settings()
    settings.update(layout=LAYOUT, folders=names)
    course.save_settings(settings)
    left = []
    for old in ("raw", "materials", "study", "inbox"):
        if (root / old).is_dir():
            _prune(root / old)
            if (root / old).is_dir():
                left.append(old)
    return left

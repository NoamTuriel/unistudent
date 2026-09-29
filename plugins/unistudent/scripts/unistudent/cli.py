"""Command line used by the skills: `python3 <plugin>/scripts/us.py <command> ...`.

Every command prints a short human summary, or JSON with --json.
Commands that act on a course take --course; without it the course is found
from the current folder, then from the Registry's active course.
"""
import argparse
import json
import sys
from pathlib import Path

from . import material
from .course import Course, Registry, find_course, general_preferences_file

TEMPLATES = Path(__file__).resolve().parents[2] / "templates"


class UserError(Exception):
    pass


def render(template_name, **values):
    text = (TEMPLATES / template_name).read_text("utf-8")
    for key, value in values.items():
        text = text.replace("{" + key + "}", str(value))
    return text


def write_context_files(course: Course):
    settings = course.settings()
    exam = []
    if settings.get("exam_date"):
        exam.append(f"- Exam date: {settings['exam_date']}")
    exam.append("- Exam format, formula sheet and lecturer emphasis: see `wiki/course.md` "
                "(filled when the Wiki is built).")
    others = [c for c in Registry().courses() if c["path"] != str(course.root)]
    other_lines = [f"- {c['name']}: `{Path(c['path']) / 'wiki'}`" for c in others] or ["- None."]
    context = render("CLAUDE.md",
                     course_name=settings["course_name"],
                     language=settings.get("language", "he"),
                     general_preferences=general_preferences_file(),
                     other_courses="\n".join(other_lines),
                     exam_section="\n".join(exam))
    (course.root / "CLAUDE.md").write_text(context, "utf-8")
    readme = course.root / "README.md"
    if not readme.exists():
        lang = "he" if settings.get("language") == "he" else "en"
        readme.write_text(render(f"README.{lang}.md", course_name=settings["course_name"]), "utf-8")


def refresh_other_contexts(course: Course):
    """Every course's context file names the student's other courses; keep them in step."""
    for entry in Registry().courses():
        other = Course(entry["path"])
        if other.root != course.root and other.exists():
            write_context_files(other)


SYNCED_MARKERS = ("mobile documents", "icloud", "google drive", "googledrive", "my drive",
                  "dropbox", "onedrive", "box sync")


def is_synced_folder(path: Path) -> bool:
    """iCloud, Google Drive, Dropbox and OneDrive don't carry links reliably and evict big files."""
    return any(marker in part.lower() for part in path.parts for marker in SYNCED_MARKERS)


def recordings_root() -> Path:
    import os
    return Path(os.environ.get("UNISTUDENT_RECORDINGS_ROOT") or Path.home() / "UniStudent recordings")


def safe_name(name: str) -> str:
    import re
    return re.sub(r'[\\/:*?"<>|]', "-", name).strip() or "course"


def resolve_course(args) -> Course:
    course = Course(args.course) if getattr(args, "course", None) else find_course()
    if course is None or not course.exists():
        raise UserError("No course folder found. Run setup first, or pass --course <folder>.")
    return course


# --- commands ---------------------------------------------------------------

def cmd_setup(args):
    course = Course(args.path)
    for folder in (course.raw, course.wiki, course.materials, course.study, course.inbox):
        folder.mkdir(parents=True, exist_ok=True)
    settings = course.settings()
    settings.update({k: v for k, v in {
        "course_name": args.name or settings["course_name"] or course.root.name,
        "language": args.language,
        "format": args.format,
        "course_skill": args.course_skill,
        "university": args.university,
        "source_mode": args.source_mode,
    }.items() if v is not None})
    synced = is_synced_folder(course.root)
    if synced and not settings.get("recordings_dir"):
        settings["recordings_dir"] = str(recordings_root() / safe_name(settings["course_name"]))
    course.save_settings(settings)
    if not course.preferences_file.exists():
        course.preferences_file.write_text("# Course preferences\n\n", "utf-8")
    Registry().add(course, settings["course_name"])
    refresh_other_contexts(course)
    added = []
    if args.import_dir:
        added = material.import_folder(course, args.import_dir, tier=args.tier)
    else:
        material.rebuild_materials(course)
    write_context_files(course)
    return {
        "course": str(course.root),
        "course_name": settings["course_name"],
        "imported": len(added),
        "synced": synced,
        "recordings_dir": settings.get("recordings_dir"),
        "unsorted": material.unsorted(course),
        "summary": f"Course folder ready at {course.root} ({len(added)} new files, "
                   f"{len(material.unsorted(course))} unsorted).",
    }


def cmd_import(args):
    course = resolve_course(args)
    added = material.import_folder(course, args.folder, tier=args.tier)
    return {"imported": added, "unsorted": material.unsorted(course),
            "summary": f"{len(added)} new or changed files; {len(material.unsorted(course))} unsorted."}


def cmd_manifest(args):
    return resolve_course(args).manifest()


def cmd_unsorted(args):
    course = resolve_course(args)
    files = material.unsorted(course)
    return {"files": files, "summary": "\n".join(files) or "Nothing unsorted."}


def cmd_assign(args):
    course = resolve_course(args)
    try:
        material.assign(course, args.path, args.unit)
    except KeyError:
        raise UserError(f"Not in the Manifest: {args.path}")
    return {"summary": f"{args.path} → {course.unit_label(course.manifest()['files'][args.path]['unit'])}"}


def cmd_courses(args):
    registry = Registry()
    if args.action == "switch":
        entry = registry.switch(args.target)
        if not entry:
            raise UserError(f"No course named {args.target}.")
        return {"active": entry, "summary": f"Working on: {entry['name']}"}
    if args.action == "current":
        course = find_course()
        if course is None:
            return {"course": None, "summary": "No course detected."}
        name = course.settings()["course_name"]
        return {"course": str(course.root), "name": name, "summary": f"Working on: {name}"}
    courses = registry.courses()
    lines = [("* " if c["active"] else "  ") + f"{c['name']}  ({c['path']})" for c in courses]
    return {"courses": courses, "summary": "\n".join(lines) or "No courses yet."}


def cmd_context(args):
    course = resolve_course(args)
    if args.exam_date:
        course.update_settings(exam_date=args.exam_date)
    write_context_files(course)
    return {"summary": f"Context file written: {course.root / 'CLAUDE.md'}"}


# --- parser -----------------------------------------------------------------

def build_parser():
    parser = argparse.ArgumentParser(prog="us", description="UniStudent core commands")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name, func, help_text):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("--json", action="store_true", help="print JSON")
        p.set_defaults(func=func)
        return p

    def with_course(p):
        p.add_argument("--course", help="course folder (default: detect)")
        return p

    p = add("setup", cmd_setup, "create or update a course folder")
    p.add_argument("path")
    p.add_argument("--name")
    p.add_argument("--language")
    p.add_argument("--format", choices=["obsidian", "markdown"])
    p.add_argument("--course-skill")
    p.add_argument("--university")
    p.add_argument("--source-mode", choices=["site", "own-folder", "both"])
    p.add_argument("--import", dest="import_dir")
    p.add_argument("--tier", choices=["official", "added"], default="added")

    p = with_course(add("import", cmd_import, "register a folder's files without copying"))
    p.add_argument("folder")
    p.add_argument("--tier", choices=["official", "added"], default="added")

    with_course(add("manifest", cmd_manifest, "print the Manifest"))
    with_course(add("unsorted", cmd_unsorted, "list files with no unit"))

    p = with_course(add("assign", cmd_assign, "assign an unsorted file to a unit or 'general'"))
    p.add_argument("path")
    p.add_argument("unit")

    p = add("courses", cmd_courses, "list, switch or show the current course")
    p.add_argument("action", choices=["list", "switch", "current"], nargs="?", default="list")
    p.add_argument("target", nargs="?")

    p = with_course(add("context", cmd_context, "rewrite the course context file"))
    p.add_argument("--exam-date")

    from . import extra_commands
    extra_commands.register(add, with_course)
    return parser


def main(argv=None):
    parser = build_parser()
    argv = list(sys.argv[1:] if argv is None else argv)
    commands = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction)).choices
    if argv and argv[0] in commands:
        # Intermixed: options and positionals in any order (skills needn't care).
        args = commands[argv[0]].parse_intermixed_args(argv[1:])
    else:
        args = parser.parse_args(argv)
    try:
        result = args.func(args)
    except UserError as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False) if args.json else f"Error: {error}")
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result.get("summary", json.dumps(result, ensure_ascii=False, indent=2))
              if isinstance(result, dict) else result)
    return 0


if __name__ == "__main__":
    sys.exit(main())

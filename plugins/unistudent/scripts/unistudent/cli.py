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
from .common import UserError, resolve_course
from .course import Course, Registry, find_course, general_preferences_file, safe_name
from .links import is_synced_folder, recordings_root

TEMPLATES = Path(__file__).resolve().parent / "templates"
CONTEXT_MARK = "<!-- unistudent:context -->"


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
    context = render("context.md",
                     course_name=settings["course_name"],
                     language=settings.get("language", "he"),
                     general_preferences=general_preferences_file(),
                     other_courses="\n".join(other_lines),
                     exam_section="\n".join(exam))
    # The full context lives in .unistudent/context.md. AGENTS.md (read by Codex, Cursor, Gemini
    # and others) carries it in full; CLAUDE.md imports it. A student's own file is kept and gets
    # one pointer line instead.
    ours = course.state / "context.md"
    ours.parent.mkdir(parents=True, exist_ok=True)
    ours.write_text(context, "utf-8")
    _write_or_point(course.root / "AGENTS.md", context,
                    "Read `.unistudent/context.md` first: it holds this course's rules (UniStudent).")
    _write_or_point(course.root / "CLAUDE.md", "@.unistudent/context.md\n", "@.unistudent/context.md")
    readme = course.root / "README.md"
    if not readme.exists():
        lang = "he" if settings.get("language") == "he" else "en"
        readme.write_text(render(f"README.{lang}.md", course_name=settings["course_name"]), "utf-8")


def _write_or_point(path: Path, content: str, pointer: str):
    if not path.exists() or path.read_text("utf-8").startswith(CONTEXT_MARK):
        path.write_text(f"{CONTEXT_MARK}\n{content}", "utf-8")
        return
    text = path.read_text("utf-8")
    if pointer not in text:
        path.write_text(text.rstrip("\n") + f"\n\n{pointer}\n", "utf-8")


def refresh_other_contexts(course: Course):
    """Every course's context file names the student's other courses; keep them in step."""
    for entry in Registry().courses():
        other = Course(entry["path"])
        if other.root != course.root and other.exists():
            write_context_files(other)


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
        "origin_mode": args.origin_mode,
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
        courses = [{"name": c["name"], "path": c["path"]} for c in registry.courses()]
        inside = find_course(use_registry=False)
        course = inside or find_course()
        if course is None:
            return {"course": None, "found_by": None, "courses": courses,
                    "summary": "No course yet: run /unistudent:course-setup."}
        name = course.settings()["course_name"]
        found_by = "course folder" if inside else "last active"
        summary = f"Working on: {name}"
        if not inside and len(courses) > 1:
            others = ", ".join(c["name"] for c in courses if c["path"] != str(course.root))
            summary += (f" (last active; not inside a course folder). Other courses: {others}. "
                        "If the request is about one of them, use it (--course <path>); if unclear, ask.")
        return {"course": str(course.root), "name": name, "found_by": found_by,
                "courses": courses, "summary": summary}
    courses = registry.courses()
    lines = [("* " if c["active"] else "  ") + f"{c['name']}  ({c['path']})" for c in courses]
    return {"courses": courses, "summary": "\n".join(lines) or "No courses yet."}


def cmd_context(args):
    course = resolve_course(args)
    course.update_settings(exam_date=args.exam_date,
                           recording_level=int(args.recording_level) if args.recording_level is not None else None,
                           frame_analysis=(args.frame_analysis == "1") if args.frame_analysis is not None else None)
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
    p.add_argument("--origin-mode", choices=["site", "own-folder", "both"])
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

    p = with_course(add("context", cmd_context, "update exam date / recording level and rewrite the context file"))
    p.add_argument("--exam-date")
    p.add_argument("--recording-level", choices=["0", "1", "3"],
                   help="0 skip, 1 download only, 3 transcript and summary")
    p.add_argument("--frame-analysis", choices=["0", "1"],
                   help="0 off, 1 on: per-segment vision calls when indexing recordings (separate opt-in, costly)")

    from . import commands
    commands.register(add, with_course)
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
        sys.stdout.reconfigure(encoding="utf-8")  # Windows pipes default to a legacy code page
    except (AttributeError, ValueError):
        pass
    try:
        result = args.func(args)
    except (UserError, RuntimeError, ValueError, KeyError, OSError) as error:
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

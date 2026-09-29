"""Commands added by later tickets (Wiki, inbox, preferences, recordings, checks)."""
from pathlib import Path


def register(add, with_course):
    from . import wiki
    from .cli import resolve_course

    def cmd_wiki(args):
        course = resolve_course(args)
        if args.action == "check":
            return wiki.check(course)
        return wiki.build(course, force=args.force)

    p = with_course(add("wiki", cmd_wiki, "build or check the Wiki"))
    p.add_argument("action", choices=["build", "check"])
    p.add_argument("--force", action="store_true", help="convert every file again")

    def cmd_add(args):
        from . import material
        course = resolve_course(args)
        official = set(args.official or [])
        added = []
        for path in list(material.iter_files(course.inbox)):
            rel_in_inbox = path.relative_to(course.inbox).as_posix()
            tier = "official" if (path.name in official or rel_in_inbox in official) else "added"
            added.append(material.add_file(course, path, tier=tier, origin="inbox",
                                           rel=f"inbox/{rel_in_inbox}"))
        for folder in sorted((p for p in course.inbox.rglob("*") if p.is_dir()), reverse=True):
            try:
                folder.rmdir()
            except OSError:
                pass
        material.rebuild_materials(course)
        built = wiki.build(course) if added else None
        unsorted = [rel for rel in material.unsorted(course) if rel in added]
        return {"added": added, "unsorted": unsorted, "wiki": built,
                "summary": (f"Added {len(added)} files; {len(unsorted)} need a unit."
                            if added else "The inbox is empty.")}

    def cmd_check(args):
        from . import labels
        from .links_check import check_links
        course = resolve_course(args)
        report = {"paragraphs": [], "problems": []}
        for name in args.files:
            page = Path(name).resolve()
            pages = sorted(page.rglob("*.md")) if page.is_dir() else [page]
            for one in pages:
                if args.labels:
                    part = labels.check_page(one, course.root)
                    report["paragraphs"] += part["paragraphs"]
                    report["problems"] += part["problems"]
                else:
                    report["problems"] += check_links(one, course.root)
        report["summary"] = f"{len(report['problems'])} problems." + "".join(
            f"\n- {p['kind']}: {p['page']}:{p.get('line', '')} {p.get('link', p.get('text', ''))[:80]}"
            for p in report["problems"])
        return report

    p = with_course(add("check", cmd_check, "check links (and grounding labels) in pages"))
    p.add_argument("files", nargs="+", help="Markdown files or folders")
    p.add_argument("--labels", action="store_true", help="also require one grounding label per paragraph")

    def cmd_eval_grade(args):
        import json
        from . import labels
        course = resolve_course(args)
        case = json.loads(Path(args.case).read_text("utf-8"))
        result = labels.grade(case, Path(args.answer).resolve(), course.root)
        result["summary"] = ("PASS " if result["passed"] else "FAIL ") + str(result["id"]) + "".join(
            f"\n- {f}" for f in result["failures"])
        return result

    p = with_course(add("eval-grade", cmd_eval_grade, "grade one grounding-eval answer"))
    p.add_argument("case")
    p.add_argument("answer")

    def cmd_prefs(args):
        from datetime import date
        from .course import general_preferences_file
        course = resolve_course(args)
        files = [("general", general_preferences_file()), ("course", course.preferences_file)]
        if args.action == "add":
            if not args.text:
                from .cli import UserError
                raise UserError("Give the preference text.")
            path = dict(files)[args.scope]
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists():
                title = "General preferences" if args.scope == "general" else "Course preferences"
                path.write_text(f"# {title}\n\n", "utf-8")
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(f"- {' '.join(args.text)} ({date.today().isoformat()})\n")
        shown = [{"scope": scope, "path": str(path),
                  "content": path.read_text("utf-8") if path.exists() else ""} for scope, path in files]
        return {"files": shown,
                "summary": "\n\n".join(f"[{s['scope']}] {s['path']}\n{s['content'].strip() or '(empty)'}"
                                       for s in shown) + "\n\nCourse preferences win over general ones."}

    p = with_course(add("prefs", cmd_prefs, "show or add student preferences"))
    p.add_argument("action", choices=["show", "add"])
    p.add_argument("--text", nargs="+")
    p.add_argument("--scope", choices=["course", "general"], default="course")

    def cmd_study(args):
        from datetime import datetime
        course = resolve_course(args)
        folder = wiki.unit_dir(int(args.unit) if str(args.unit).isdigit() else args.unit)
        current = {info["page"]: info.get("fingerprint")
                   for info in course.read_state("wiki.json", {}).values()
                   if info["page"].startswith(f"sources/{folder}/")}
        for rel, info in wiki.recording_pages(course).items():
            if wiki.unit_dir(info["unit"]) == folder and info["processed"]:
                current[info["folder"] + "/summary.md"] = "processed"
        packs = course.read_state("studypacks.json", {})
        if args.action == "mark-built":
            packs[folder] = {"built": datetime.now().isoformat(timespec="seconds"), "sources": current}
            course.write_state("studypacks.json", packs)
            return {"summary": f"Recorded the sources of the {folder} study pack ({len(current)})."}
        base = packs.get(folder)
        if base is None:
            return {"has_study_pack": False, "new": [], "changed": [], "removed": [],
                    "summary": f"No study pack recorded for {folder}."}
        old = base["sources"]
        result = {
            "has_study_pack": True, "built": base["built"],
            "new": sorted(p for p in current if p not in old),
            "changed": sorted(p for p in current if p in old and old[p] != current[p]),
            "removed": sorted(p for p in old if p not in current),
        }
        n = len(result["new"]) + len(result["changed"]) + len(result["removed"])
        result["summary"] = f"{n} changes since the study pack was built ({base['built']})."
        return result

    p = with_course(add("study", cmd_study, "track which sources a study pack was built from"))
    p.add_argument("action", choices=["mark-built", "changes"])
    p.add_argument("--unit", required=True, help="unit number or 'general'")

    def cmd_recordings(args):
        from . import recordings
        course = resolve_course(args)
        if args.action == "list":
            rows = recordings.listing(course, args.unit)
            return {"recordings": rows, "summary": "\n".join(
                f"{'✓' if r['processed'] else ('½' if r['has_transcript'] else '·')} {r['path']}" for r in rows)
                or "No recordings."}
        if args.action == "estimate":
            est = recordings.estimate(course, args.unit)
            timing = (f"about {est['estimated_hours']} h on this machine" if est["estimated_hours"] is not None
                      else "time unknown: run `recordings benchmark` first")
            est["summary"] = (f"{est['recordings']} recordings, {est['hours']} h of audio, {est['gigabytes']} GB; "
                              f"{timing}. Backend: {est['backend']}"
                              + ("" if est["backend_installed"] else " (not installed)") + ".")
            return est
        if not args.paths:
            from .cli import UserError
            raise UserError("Name at least one recording (its path in Raw).")
        if args.action == "benchmark":
            factor = recordings.benchmark(course, args.paths[0])
            return {"realtime_factor": factor,
                    "summary": f"This machine transcribes 1 hour of audio in about {factor:.2f} h."}
        done = [str(recordings.transcribe(course, rel)) for rel in args.paths]
        return {"transcripts": done, "summary": "Transcribed:\n" + "\n".join(done)}

    p = with_course(add("recordings", cmd_recordings, "list, estimate, benchmark or transcribe recordings"))
    p.add_argument("action", choices=["list", "estimate", "benchmark", "transcribe"])
    p.add_argument("paths", nargs="*", help="recording paths in Raw")
    p.add_argument("--unit", help="only this unit's recordings")

    p = with_course(add("add", cmd_add, "move inbox files into Raw, sort them, update the Wiki"))
    p.add_argument("--official", nargs="*", help="inbox file names that are the lecturer's material")

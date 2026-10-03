"""Commands for the Wiki, the inbox, checks, preferences, study packs, recordings and the course site."""
from pathlib import Path

from .common import UserError, problems_summary, resolve_course
from .course import (Course, Registry, find_course, SETUP_STAGES, clear_setup_progress, generated_course_skill_file, generated_university_file,
                     list_generated, list_setup_progress, next_setup_stage, parse_unit, read_setup_progress, recommend_plugins,
                     safe_name, unit_dir,
                     write_generated_reference, write_setup_progress)


def register(add, with_course):
    from . import wiki

    def cmd_wiki(args):
        course = resolve_course(args)
        if args.action == "check":
            return wiki.check(course)
        if args.action == "coverage":
            return wiki.coverage(course)
        from . import material
        material.require_new_layout(course)
        return wiki.build(course, force=args.force)

    p = with_course(add("wiki", cmd_wiki, "build or check the Wiki, or show which files it did and did not read"))
    p.add_argument("action", choices=["build", "check", "coverage"])
    p.add_argument("--force", action="store_true", help="convert every file again")

    def cmd_add(args):
        from . import material
        course = resolve_course(args)
        material.require_new_layout(course)
        official = set(args.official or [])
        notes = dict(pair.split("=", 1) for pair in (args.describe or []) if "=" in pair)
        added = []
        for path in list(material.iter_files(course.inbox)):
            rel_in_inbox = path.relative_to(course.inbox).as_posix()
            tier = "official" if (path.name in official or rel_in_inbox in official) else "added"
            added.append(material.add_file(course, path, tier=tier, origin="inbox", hint=rel_in_inbox,
                                           note=notes.get(path.name) or notes.get(rel_in_inbox)))
        for folder in sorted((p for p in course.inbox.rglob("*") if p.is_dir()), reverse=True):
            try:
                folder.rmdir()
            except OSError:
                pass
        built = wiki.build(course) if added else None
        unsorted = [rel for rel in material.unsorted(course) if rel in added]
        return {"added": added, "unsorted": unsorted, "wiki": built,
                "summary": (f"Added {len(added)} files; {len(unsorted)} need a unit."
                            if added else "The inbox is empty.")}

    def cmd_check(args):
        from . import labels
        from .links_check import check_links, check_pack_page, check_vault_page
        course = resolve_course(args)
        report = {"paragraphs": [], "problems": []}
        for name in args.files:
            page = Path(name).resolve()
            pages = sorted(page.rglob("*.md")) if page.is_dir() else [page]
            for one in pages:
                if one.resolve().is_relative_to(course.study.resolve()):
                    report["problems"] += check_vault_page(one, course.state) + check_pack_page(one)
                if args.labels:
                    part = labels.check_page(one, course.root)
                    report["paragraphs"] += part["paragraphs"]
                    report["problems"] += part["problems"]
                else:
                    report["problems"] += check_links(one, course.root)
        report["summary"] = problems_summary(
            report["problems"],
            lambda p: f"{p['kind']}: {p['page']}:{p.get('line', '')} {p.get('link', p.get('text', ''))[:80]}")
        return report

    p = with_course(add("check", cmd_check, "check links (and the grounding rule) in pages"))
    p.add_argument("files", nargs="+", help="Markdown files or folders")
    p.add_argument("--labels", action="store_true", help="also require every paragraph to cite a source or carry the warning")

    def cmd_draw(args, kind=None):
        from . import draw
        result = draw.draw(kind or args.kind, args.spec, force=args.force)
        result.setdefault("summary", f"Drew {result['png']}" if result["drawn"]
                          else f"{result['png']} is up to date (the spec has not changed).")
        return result

    p = add("draw", cmd_draw, "draw a picture spec (JSON) to a PNG next to it; fetches the drawing tool on first use")
    p.add_argument("kind", help="the picture kind, e.g. graph")
    p.add_argument("spec", help="the spec file; the PNG is saved beside it")
    p.add_argument("--force", action="store_true", help="draw again even if the spec has not changed")

    p = add("graph", lambda args: cmd_draw(args, "graph"), "draw a Graph spec (JSON) to a PNG next to it")
    p.add_argument("spec", help="the Graph spec file; the PNG is saved beside it")
    p.add_argument("--force", action="store_true", help="draw again even if the spec has not changed")

    def cmd_tools(args):
        import datetime
        from . import draw
        from .cli import write_context_files
        course = resolve_course(args)
        answers = dict(course.settings().get("tools") or {})
        if args.action == "status":
            return {"tools": answers, "supports": draw.supports(answers),
                    "summary": "This course can draw: " + ", ".join(draw.supports(answers)) + "."}
        if args.action == "offer":
            names = draw.offer(course.wiki, args.field, answers)
            tools = [{"name": n, "draws": draw.KINDS[n]["draws"], "label": draw.KINDS[n]["label"]} for n in names]
            summary = ("Nothing more to offer for this course." if not tools else
                       "Offer the student, in one message: " + "; ".join(f"{t['label']} ({t['draws']})" for t in tools)
                       + ". Then `us tools accept <name>` or `us tools skip <name>` for each answer.")
            return {"tools": tools, "summary": summary}
        names = args.names or []
        unknown = [n for n in names if n not in draw.KINDS or not draw.KINDS[n].get("offer")]
        if not names or unknown:
            raise UserError(f"Name the tools to {args.action}; the ones that can be offered are: "
                            + ", ".join(sorted(n for n, k in draw.KINDS.items() if k.get("offer")) or ["none yet"]) + ".")
        failed, today = {}, datetime.date.today().isoformat()
        for name in names:
            reason = draw.accept(name) if args.action == "accept" else None
            if reason:
                failed[name] = reason
                continue
            answers[name] = {"state": "accepted" if args.action == "accept" else "skipped", "date": today}
        course.update_settings(tools=answers)
        write_context_files(course)
        summary = (f"Noted: {', '.join(n for n in names if n not in failed) or 'nothing'}."
                   + "".join(f" I couldn't get {n} ({why}); the study pack will describe those pictures in words."
                             for n, why in failed.items()))
        return {"tools": answers, "failed": list(failed), "summary": summary}

    p = with_course(add("tools", cmd_tools, "offer, accept or skip the picture tools that fit this course; show what it can draw"))
    p.add_argument("action", choices=["offer", "accept", "skip", "status"])
    p.add_argument("names", nargs="*", help="accept/skip: the tool names")
    p.add_argument("--field", help="offer: the course's academic field, used when the Wiki says little")

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

    def fallback(args, path, name, noun, need, heading, sections):
        """Shared status/save for a generated fallback (ADR 0005): `noun` names it, `need` the missing-option message."""
        if args.action == "status":
            exists = path.exists()
            return {"generated": exists, "path": str(path),
                    "content": path.read_text("utf-8") if exists else None,
                    "summary": (f"Reusing the generated {noun} for {name} ({path})." if exists
                                else f"No generated {noun} yet for {name}.")}
        if not all(words for _, words in sections):
            raise UserError(need)
        write_generated_reference(path, heading, sections)
        return {"path": str(path), "summary": f"Saved a generated {noun} for {name} at {path}."}

    def cmd_university(args):
        return fallback(args, generated_university_file(args.university), args.university, "fallback",
                        "Give both --url and --organizing.",
                        f"{args.university}: how the student reaches the course site",
                        [("Site", args.url), ("How the student organizes and prioritizes material", args.organizing)])

    p = add("university", cmd_university, "check for or save a generated university fallback (no installed plugin)")
    p.add_argument("action", choices=["status", "save"])
    p.add_argument("--university", required=True)
    p.add_argument("--url", nargs="+")
    p.add_argument("--organizing", nargs="+", help="how the student organizes and prioritizes material")

    def cmd_course_skill(args):
        return fallback(args, generated_course_skill_file(args.field, args.course_name), args.course_name,
                        "study-pack fallback", "Give both --emphasis and --summarize.",
                        f"{args.field} — {args.course_name}: generated study-pack rules",
                        [("What to emphasize", args.emphasis), ("How to summarize", args.summarize)])

    p = add("course-skill", cmd_course_skill,
            "check for or save a generated course/subject study-pack fallback (no installed course skill)")
    p.add_argument("action", choices=["status", "save"])
    p.add_argument("--field", required=True, help="broad academic field, e.g. economics")
    p.add_argument("--course-name", required=True)
    p.add_argument("--emphasis", nargs="+", help="what to emphasize in this course's study packs")
    p.add_argument("--summarize", nargs="+", help="how this course wants material summarized")

    def cmd_plugins(args):
        if not (args.university or args.field or args.course_name):
            raise UserError("Give at least one of --university, --field or --course-name.")
        found = [{"name": p["name"], "kind": p["kind"], "gives": p["gives"],
                  "install": f"/plugin install {p['name']}@unistudent"}
                 for p in recommend_plugins(args.university or "", args.field or "", " ".join(args.course_name or []))]
        other = ("In another app (Cursor, Codex, Gemini CLI...), add the skills with "
                 "`npx skills@latest add NoamTuriel/unistudent`.")
        summary = ("\n".join(f"{p['name']}: {p['gives']}. To add it: {p['install']}" for p in found) if found
                   else "No plugin for this university or course yet: carry on with the generic rules (they work for any "
                        "course). If you are not using Claude, the same skills are available too.") + "\n" + other
        return {"plugins": found, "other_apps": other, "summary": summary}

    p = add("plugins", cmd_plugins, "recommend the plugins to install for a university and course (never installs)")
    p.add_argument("action", choices=["recommend"])
    p.add_argument("--university")
    p.add_argument("--field", help="broad academic field, e.g. economics")
    p.add_argument("--course-name", nargs="+")

    def cmd_course_context(args):
        """The course rules for the AI: from --course, else the folder it runs in, else the active course."""
        course = find_course(args.course)  # --course may be any folder inside the course
        if course is None or not course.exists():
            entries = [{"name": c["name"], "path": c["path"]} for c in Registry().courses() if c["exists"]]
            if not entries:
                raise UserError("No course found. Run /unistudent:course-setup first.")
            if len(entries) == 1:  # one course left (the active entry may be stale): just use it
                course = Course(entries[0]["path"])
        if course is None or not course.exists():
            return {"course": None, "courses": entries,
                    "summary": "Several courses and none is active: ask the student which course they mean, then call "
                               "this again with that course's path. Courses: "
                               + "; ".join(f"{c['name']} ({c['path']})" for c in entries)}
        if not (course.state / "context.md").exists():
            from .cli import write_context_files
            write_context_files(course)  # an older course folder: make the context it never got
        context = (course.state / "context.md").read_text("utf-8")
        return {"course": course.settings()["course_name"], "path": str(course.root), "summary": context}

    p = with_course(add("course-context", cmd_course_context,
                        "the rules and facts for the student's course: call this first in every new chat"))

    def cmd_generated(args):
        entries = list_generated()
        return {"generated": entries,
                "summary": "\n".join(f"{e['preview']} ({e['path']})" for e in entries) or "Nothing generated yet."}

    p = add("generated", cmd_generated, "list the generated university and course fallbacks saved for reuse")
    p.add_argument("action", nargs="?", choices=["list"], default="list")

    def cmd_setup_progress(args):
        if args.action == "list":
            entries = list_setup_progress()
            return {"in_progress": entries,
                    "summary": "\n".join(f"{e['course_name']}: after '{e['stage']}'" for e in entries)
                               or "No setup in progress."}
        if not args.course_name:
            raise UserError("Give --course-name.")
        if args.action == "clear":
            clear_setup_progress(args.course_name)
            return {"summary": f"Cleared setup progress for {args.course_name}."}
        if args.action == "status":
            data = read_setup_progress(args.course_name)
            nxt = next_setup_stage(data["stage"])
            return {"stage": data["stage"], "next_stage": nxt, "answers": data["answers"],
                    "summary": (f"Resuming {args.course_name} after '{data['stage']}': next is '{nxt}'."
                                if data["stage"] else f"No setup in progress for {args.course_name}.")}
        if not args.stage:
            raise UserError("Give --stage.")
        answers = {}
        for kv in args.answer or []:
            if "=" not in kv:
                raise UserError(f"--answer needs key=value, got {kv!r}.")
            k, v = kv.split("=", 1)
            answers[k] = v
        answers.setdefault("course_name", args.course_name)
        data = write_setup_progress(args.course_name, args.stage, answers)
        if next_setup_stage(args.stage) is None:
            clear_setup_progress(args.course_name)
            return {"summary": f"Setup for {args.course_name} complete; progress cleared."}
        return {"stage": data["stage"], "answers": data["answers"],
                "summary": f"Recorded stage '{args.stage}' done for {args.course_name}."}

    p = add("setup-progress", cmd_setup_progress, "track and resume course-setup's stage-by-stage progress")
    p.add_argument("action", choices=["status", "advance", "clear", "list"])
    p.add_argument("--course-name")
    p.add_argument("--stage", choices=SETUP_STAGES)
    p.add_argument("--answer", nargs="+", help="key=value pairs to remember (repeatable)")

    def cmd_study(args):
        from datetime import datetime
        course = resolve_course(args)
        folder = unit_dir(args.unit)
        current = {info["page"]: info.get("fingerprint")
                   for info in course.read_state("wiki.json", {}).values()
                   if info["page"].startswith(f"sources/{folder}/")}
        for rel, info in wiki.recording_pages(course).items():
            if unit_dir(info["unit"]) == folder and info["processed"]:
                current[info["folder"] + "/summary.md"] = "processed"
        packs = course.read_state("studypacks.json", {})
        pack = str(course.pack_folder(args.unit))
        course.study.mkdir(exist_ok=True)  # the first Study pack request makes the Study vault (ADR 0008)
        if args.action == "mark-built":
            packs[folder] = {"built": datetime.now().isoformat(timespec="seconds"), "sources": current}
            course.write_state("studypacks.json", packs)
            return {"pack_folder": pack, "summary": f"Recorded the sources of the {folder} study pack ({len(current)})."}
        base = packs.get(folder)
        if base is None:
            return {"has_study_pack": False, "pack_folder": pack, "new": [], "changed": [], "removed": [],
                    "summary": f"No study pack recorded for {folder}."}
        old = base["sources"]
        result = {
            "has_study_pack": True, "pack_folder": pack, "built": base["built"],
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
                f"{'done' if r['processed'] else ('partial' if r['has_transcript'] else 'none')}  {r['path']}" for r in rows)
                or "No recordings."}
        if args.action == "estimate":
            est = recordings.estimate(course, args.unit)
            timing = (f"about {est['estimated_hours']} h on this machine" if est["estimated_hours"] is not None
                      else "time unknown: run `recordings benchmark` first")
            est["summary"] = (f"{est['recordings']} recordings, {est['hours']} h of audio, {est['gigabytes']} GB; "
                              f"{timing}. Backend: {est['backend']}"
                              + ("" if est["backend_installed"] else " (not installed)") + ". "
                              f"Frame analysis (separate opt-in): {est['frame_analysis_segments']} segments, "
                              "one vision call each.")
            return est
        if args.action == "fetch":
            if len(args.paths) != 2:
                raise UserError("fetch needs the listing JSON and the download folder.")
            result = recordings.fetch_streams(args.paths[0], args.paths[1], audio_only=args.audio_only)
            result["summary"] = (f"Downloaded {len(result['downloaded'])} recordings"
                                 + (f"; failed: {', '.join(result['failed'])}" if result["failed"] else "") + ".")
            return result
        if not args.paths:
            raise UserError("Name at least one recording (its path in the Material folder).")
        if args.action == "benchmark":
            factor = recordings.benchmark(course, args.paths[0])
            return {"realtime_factor": factor,
                    "summary": f"This machine transcribes 1 hour of audio in about {factor:.2f} h."}
        if args.action == "approve":
            chosen = recordings.approve(course, args.paths)
            return {"approved": chosen, "summary": "Approved for transcription:\n" + "\n".join(chosen)}
        recordings.require_approved(course, args.paths)
        if args.background:
            job = recordings.start_background(course, args.paths)
            return {**job, "summary": f"Transcribing {len(args.paths)} recordings in the background. "
                                      f"Progress: {job['log']}. Check with `recordings list`."}
        done = [str(recordings.transcribe(course, rel)) for rel in args.paths]
        return {"transcripts": done, "summary": "Transcribed:\n" + "\n".join(done)}

    p = with_course(add("recordings", cmd_recordings, "list, estimate, benchmark, approve or transcribe recordings (transcribe only runs what the student approved)"))
    p.add_argument("action", choices=["list", "estimate", "benchmark", "approve", "transcribe", "fetch"])
    p.add_argument("paths", nargs="*", help="recording paths in the Material folder (fetch: listing JSON and download folder)")
    p.add_argument("--audio-only", action="store_true", help="fetch: keep only the sound (enough for transcripts)")
    p.add_argument("--background", action="store_true",
                   help="transcribe: run detached and return at once (long jobs outlive tool-call time limits)")
    p.add_argument("--unit", help="only this unit's recordings")

    def cmd_ingest(args):
        """The fetcher interface: a university plugin's listing + downloaded files → the Material folder."""
        import json
        from . import material
        course = resolve_course(args)
        material.require_new_layout(course)
        material.scan(course)  # the student may have moved files since the last sync: find them first
        data = json.loads(Path(args.listing).read_text("utf-8"))
        staged = Path(args.folder)
        by_url = {e.get("site_url"): rel for rel, e in course.manifest()["files"].items() if e.get("site_url")}
        new, changed, missing, recordings = [], [], [], []
        for item in data.get("items", []):
            url = item.get("url")
            source = staged / item["file"] if item.get("file") else None
            if source is None or not source.exists():
                if url in by_url:
                    continue  # downloaded in an earlier sync
                (recordings if item.get("kind") == "recording" else missing).append(url)
                continue
            before = by_url.get(url)
            if before and course.manifest()["files"][before].get("fingerprint") == material.fingerprint(source):
                source.unlink()
                continue
            name = safe_name(item.get("name") or source.name)
            hint = item.get("unit_hint")
            rel = material.add_file(course, source, tier="official", origin="course-site", name=name,
                                    hint=f"{safe_name(item.get('section') or 'General')}/{name}", replace_rel=before,
                                    site_unit=parse_unit(hint) if hint is not None else None,
                                    extra={"site_url": url, "site_modified": item.get("modified")})
            (changed if before else new).append(rel)
        built = wiki.build(course) if (new or changed) else None
        return {"new": new, "changed": changed, "missing": missing, "recordings_available": recordings,
                "unsorted": [r for r in material.unsorted(course) if r in new or r in changed], "wiki": built,
                "summary": f"{len(new)} new, {len(changed)} changed, {len(missing)} missing, "
                           f"{len(recordings)} recordings available on the site."}

    p = with_course(add("ingest", cmd_ingest, "take a university plugin's listing and downloaded files into the Material folder"))
    p.add_argument("listing", help="listing JSON written by the university plugin")
    p.add_argument("folder", help="folder with the downloaded files")

    def cmd_site_status(args):
        course = resolve_course(args)
        entries = [e for e in course.manifest()["files"].values() if e.get("site_url")]
        urls = sorted(e["site_url"] for e in entries)
        modified = {e["site_url"]: e.get("site_modified") for e in entries}
        return {"downloaded": urls, "modified": modified,
                "summary": f"{len(urls)} files already downloaded from the course site."}

    with_course(add("site-status", cmd_site_status, "which course-site files are already in the Material folder"))

    def cmd_doc(args):
        package = Path(__file__).resolve().parent
        docs = {f.stem: f for folder in ("agents", "reference") for f in sorted((package / folder).glob("*.md"))}
        if not args.name:
            return {"docs": sorted(docs), "summary": "Docs: " + ", ".join(sorted(docs))}
        if args.name not in docs:
            raise UserError(f"No doc named {args.name}. Docs: {', '.join(sorted(docs))}")
        text = docs[args.name].read_text("utf-8")
        return {"name": args.name, "text": text, "summary": text}

    p = add("doc", cmd_doc, "read a UniStudent reference: worker instructions or study-pack rules")
    p.add_argument("name", nargs="?", help="e.g. study-pack, verifier, source-reader")

    p = with_course(add("add", cmd_add, "move the inbox files into the Material folder, sort them, update the Wiki"))
    p.add_argument("--official", nargs="*", help="inbox file names that are the lecturer's material")
    p.add_argument("--describe", nargs="*", metavar="NAME=ORIGIN",
                   help="where a file comes from, e.g. \"summary.pdf=friend's summary\"")

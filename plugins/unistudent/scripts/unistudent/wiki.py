"""Building the Wiki from the Material folder (the deterministic part).

The script converts documents, and writes the index and the generated block of each
unit page. Claude writes the rest (glossary, question bank, course page, the
methods/notation/assumptions of each unit) through the wiki skill; those parts are
never touched by a rebuild.
"""
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from . import material
from .common import problems_summary
from .convert import convert, kind
from .course import LABELS, safe_name, unit_dir
from .links_check import MD_LINK, STUB_MARK, check_links, has_sources

GEN_START = "<!-- unistudent:generated:start -->"
GEN_END = "<!-- unistudent:generated:end -->"

STUBS = {
    "glossary.md": """# Glossary

{stub}
<!-- One entry per term, in the course's notation:
### <term> (<symbol if any>)
<one-sentence definition as the course defines it>. Sources: [..](sources/..#page-N)
-->
""",
    "question-bank.md": """# Question bank

{stub}
<!-- One entry per question found in the course material (Q&A files, assignments, past exams):
### <short title>  #unit-NN/<topic-tag>
- Where: [..](sources/..#page-N) · Solved in a recording: [..](recordings/../toc.md#..) or "no"
- Question: <short paraphrase>
-->
""",
    "course.md": """# The course

{stub}
<!-- Filled from exam information files and past exams. Each line cites its source.
## Exam format
## Formula sheet and aids allowed
## What the lecturer stresses
-->
""",
}


def _plan_pages(course):
    """Stable Material folder path → Wiki page mapping (sorted, so collisions resolve the same way every time)."""
    plan, used = {}, set()
    for rel, entry in sorted(course.manifest()["files"].items()):
        if kind(rel) != "document":
            continue
        folder = unit_dir(entry.get("unit"))
        stem = safe_name(Path(rel).stem)
        candidate, n = f"sources/{folder}/{stem}.md", 2
        while candidate in used:
            candidate, n = f"sources/{folder}/{stem} ({n}).md", n + 1
        used.add(candidate)
        plan[rel] = candidate
    return plan


def _source_page(rel, entry, conversion):
    lines = [
        "---",
        f"source: {rel}",
        f"origin: {entry.get('origin')}",
        f"tier: {entry.get('tier')}",
        *([f"origin_note: {entry['origin_note']}"] if entry.get("origin_note") else []),
        f"unit: {entry.get('unit') if entry.get('unit') is not None else 'unsorted'}",
        f"converted_with: {conversion.method}",
        "---",
        "",
        f"# {Path(rel).name}",
        "",
    ]
    if conversion.empty_pages:
        lines += [f"> Pages with no text layer (read them visually): {', '.join(map(str, conversion.empty_pages))}", ""]
    for number, text in enumerate(conversion.pages, 1):
        lines += [f"## Page {number}", "", text.rstrip(), ""]
    return "\n".join(lines).rstrip() + "\n"


def _write_generated(path: Path, block: str):
    """Replace only the generated block; keep everything Claude wrote around it."""
    block = f"{GEN_START}\n{block.rstrip()}\n{GEN_END}"
    if path.exists():
        text = path.read_text("utf-8")
        if GEN_START in text and GEN_END in text:
            head, rest = text.split(GEN_START, 1)
            _, tail = rest.split(GEN_END, 1)
            text = head + block + tail
        else:
            text = block + "\n\n" + text
    else:
        text = block + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, "utf-8")


def _link(label, target):
    return f"[{label}](<{target}>)" if " " in target else f"[{label}]({target})"


def recording_pages(course):
    """Recordings and their Wiki folders (filled by the recordings pipeline). The folder is kept in the Manifest entry."""
    files = course.manifest()["files"]
    return {rel: {"folder": folder, "unit": files[rel].get("unit"),
                  "processed": (course.wiki / folder / "summary.md").exists()}
            for rel, folder in material.wiki_folders(files).items()}


def _video_path(course, rel, from_dir):
    video = material.path_of(course, rel)
    try:
        return Path(os.path.relpath(video, from_dir)).as_posix()
    except ValueError:  # another drive (Windows): link it by address
        return video.as_uri()


def _target(path):
    return f"<{path}>" if " " in path else path


def video_link(course, rel, from_dir):
    """A link to the recording's file, computed now (not remembered), so it follows moves of the file or the folder."""
    return _link("recording", _video_path(course, rel, from_dir))


def _relink_pages(wiki, moved):
    """Links in Wiki pages (written by Claude between builds) to a source page that moved follow it to its new place."""
    for page in wiki.rglob("*.md"):
        text = page.read_text("utf-8")

        def fix(match):
            raw = match.group(2)
            target = raw.strip("<>")
            path, hash_, anchor = target.partition("#")
            if not path or "://" in path:
                return match.group(0)
            here = os.path.normpath(os.path.join(page.parent.relative_to(wiki).as_posix(), unquote(path))).replace(os.sep, "/")
            if here not in moved:
                return match.group(0)
            new = Path(os.path.relpath(wiki / moved[here], page.parent)).as_posix() + hash_ + anchor
            return match.group(0).replace(raw, f"<{new}>" if " " in new or raw.startswith("<") else new, 1)

        patched = MD_LINK.sub(fix, text)
        if patched != text:
            page.write_text(patched, "utf-8")


def build(course, force=False):
    wiki = course.wiki
    wiki.mkdir(parents=True, exist_ok=True)
    found = material.scan(course)  # the folder is the truth: follow moves, drop deletions, take new files as added
    manifest = course.manifest()["files"]
    state = course.read_state("wiki.json", {})
    plan = _plan_pages(course)

    # Pages whose file was deleted, moved or renamed (the scan above already followed it in the Manifest).
    moved_pages = {}
    for rel, info in list(state.items()):
        if plan.get(rel) != info.get("page"):
            successor = plan.get(rel) or next(  # the same content, now at another path: its page moved
                (page for new, page in sorted(plan.items(), key=lambda i: Path(i[0]).name != Path(rel).name)
                 if new not in state and manifest[new].get("fingerprint") == info.get("fingerprint")), None)
            if successor and successor != info["page"]:
                moved_pages[info["page"]] = successor
            old = wiki / info["page"]
            if old.exists():
                old.unlink()
            del state[rel]

    converted, warnings_out, needs_visual, touched = 0, [], [], set()
    for rel, page in plan.items():
        entry = manifest[rel]
        target = wiki / page
        info = state.get(rel)
        if not force and info and info.get("fingerprint") == entry.get("fingerprint") and target.exists():
            needs_visual += [{"source": rel, "pages": info.get("empty_pages", [])}] if info.get("empty_pages") else []
            continue
        conversion = convert(material.path_of(course, rel))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_source_page(rel, entry, conversion), "utf-8")
        state[rel] = {"page": page, "fingerprint": entry.get("fingerprint"),
                      "method": conversion.method, "empty_pages": conversion.empty_pages,
                      "warnings": list(conversion.warnings)}
        converted += 1
        touched.add(unit_dir(entry.get("unit")))
        warnings_out += [f"{rel}: {w}" for w in conversion.warnings]
        if conversion.empty_pages:
            needs_visual.append({"source": rel, "pages": conversion.empty_pages})
    course.write_state("wiki.json", state)
    _relink_pages(wiki, {old: new for old, new in moved_pages.items() if (wiki / new).exists()})

    images = [rel for rel in manifest if kind(rel) == "image"]
    recordings = recording_pages(course)
    for name, template in STUBS.items():
        if not (wiki / name).exists():
            (wiki / name).write_text(template.replace("{stub}", STUB_MARK), "utf-8")

    # Unit pages: generated block only.
    by_unit = {}
    for rel, page in plan.items():
        by_unit.setdefault(unit_dir(manifest[rel].get("unit")), []).append((rel, page))
    for rel, info in recordings.items():
        by_unit.setdefault(unit_dir(info["unit"]), [])
    unit_pages = []
    for folder in sorted(by_unit):
        unit = {"unsorted": None, "general": "general"}.get(folder, folder[len("unit-"):])
        lines = [f"# {course.unit_label(unit)}", "", "Sources:", ""]
        for rel, page in sorted(by_unit[folder], key=lambda item: item[1]):
            lines.append(f"- {_link(Path(page).stem, '../' + page)} ({manifest[rel].get('tier')}, {manifest[rel].get('origin')})")
        recs = [(r, i) for r, i in recordings.items() if unit_dir(i["unit"]) == folder]
        if recs:
            lines += ["", "Recordings:", ""]
            for r, i in recs:
                status = _link("summary", f"../{i['folder']}/summary.md") if i["processed"] else "not processed yet"
                lines.append(f"- {Path(r).name}: {status}")
            for title, heading in (("Announcements", "Announcements"), ("This will be on the exam", "This will be on the exam")):
                found_in = [(r, i, _section((wiki / i["folder"] / "summary.md").read_text("utf-8"), heading))
                            for r, i in recs if i["processed"]]
                if any(items for _, _, items in found_in):
                    lines += ["", f"{title} (the lecturer said, in a recording):", ""]
                    for r, i, items in found_in:
                        lines += [f"- {Path(r).name} ({_link('summary', '../' + i['folder'] + '/summary.md')}): {item}"
                                  for item in items]
        lines += ["", f"Questions: {_link('question bank', '../question-bank.md')} (tag #{folder})"]
        path = wiki / "units" / f"{folder}.md"
        _write_generated(path, "\n".join(lines))
        unit_pages.append(f"units/{folder}.md")

    index = [f"# {course.settings()['course_name']}: Wiki", "",
             "Start here. Every page cites its sources; source pages hold the full text of each file.", "",
             "## Course", "", f"- {_link('The course: exam format, aids, emphasis', 'course.md')}",
             f"- {_link('Glossary', 'glossary.md')}", f"- {_link('Question bank', 'question-bank.md')}", "",
             "## Units", ""]
    index += [f"- {_link(Path(p).stem, p)}" for p in unit_pages]
    if recordings:
        index += ["", "## Recordings", ""]
        for rel, info in recordings.items():
            status = _link("summary", info["folder"] + "/summary.md") if info["processed"] else "not processed"
            index.append(f"- {Path(rel).name} ({course.unit_label(info['unit'])}): {status}")
    index += ["", "## What was and wasn't analyzed", "", f"- {_link('Coverage of every file', 'coverage.md')}"]
    (wiki / "index.md").write_text("\n".join(index) + "\n", "utf-8")
    for rel, info in recordings.items():
        transcript = wiki / info["folder"] / "transcript.md"
        if transcript.exists():
            text = transcript.read_text("utf-8")
            patched = re.sub(r"(?m)^Sources: \[recording\]\(.*\)$",
                             lambda _: "Sources: " + video_link(course, rel, transcript.parent), text, count=1)
            if patched != text:
                transcript.write_text(patched, "utf-8")
    covered = coverage(course, write=True)
    roadmaps = write_roadmaps(course, recordings)
    relink_vault(course)

    return {
        "converted": converted,
        "folder": {k: len(v) for k, v in found.items()},
        "roadmaps": roadmaps,
        "units_touched": sorted(touched),
        "pages": len(plan),
        "recordings": list(recordings),
        "images": images,
        "needs_visual": needs_visual,
        "warnings": warnings_out,
        "coverage": covered["counts"],
        "summary": f"Wiki: {converted} converted, {len(plan)} source pages, {len(recordings)} recordings, "
                   f"{len(images)} images and {len(needs_visual)} files needing visual reading. {covered['summary']}",
    }


def _section(text, title):
    """The lines under the `## ` heading that contains `title`, up to the next `## ` heading."""
    match = re.search(rf'(?ms)^## [^\n]*{re.escape(title)}[^\n]*\n(.*?)(?=^## |\Z)', text)
    return [re.sub(r"^\s*[-*]\s+", "", l).strip() for l in match.group(1).splitlines() if l.strip()] if match else []


def _for_the_vault(path: Path, video=None) -> str:
    """A Wiki page as the student reads it in the Study vault: no frontmatter, no links into the hidden Wiki,
    headings two levels down."""
    text = re.sub(r"\A---\n.*?\n---\n", "", path.read_text("utf-8"), flags=re.S)

    def keep(match):  # a time in the transcript becomes a time in the video; other links into the hidden Wiki go
        stamp = re.fullmatch(r"(?:.*transcript\.md)?#(\d\d)(\d\d)(\d\d)", match.group(2).strip("<>"))
        if not (video and stamp):
            return match.group(1)
        seconds = int(stamp[1]) * 3600 + int(stamp[2]) * 60 + int(stamp[3])
        return _link(match.group(1), f"{video}#t={seconds}")

    return re.sub(r"(?m)^(#{1,4}) ", r"\1## ", MD_LINK.sub(keep, text)).strip()


def write_roadmaps(course, recordings):
    """One recordings roadmap per unit in the Study vault, from the hidden Wiki's recording pages: what each processed
    recording covers, with the announcements and exam hints the lecturer made, and a link to the video."""
    if course.legacy:
        return []
    by_unit = {}
    for rel, info in recordings.items():
        if info["processed"]:
            by_unit.setdefault(unit_dir(info["unit"]), []).append((rel, info))
    written = []
    for folder, recs in sorted(by_unit.items()):
        unit = recs[0][1]["unit"]
        page = course.pack_folder(unit) / f"{course.label('roadmap')}.md"
        lines = [f"# {course.label('roadmap')}: {course.unit_label(unit)}", ""]
        for rel, info in recs:
            video = material.path_of(course, rel).as_uri()
            lines += [f"## {Path(rel).name}", "", f"[recording]({video})", ""]
            for name in ("toc.md", "summary.md"):
                if (course.wiki / info["folder"] / name).exists():
                    lines += [_for_the_vault(course.wiki / info["folder"] / name, video), ""]
        lines[2:2] = ["✅ Made from the transcripts and summaries of these recordings; the times open the video. "
                      + "Sources: " + ", ".join(_link(Path(r).name, material.path_of(course, r).as_uri()) for r, _ in recs), ""]
        _write_generated(page, "\n".join(lines))
        written.append(page.relative_to(course.root).as_posix())
    _remove_stale_roadmaps(course, written)
    return written


def relink_vault(course):
    """Keep the citations in the Study vault pointing at the student's own files: a link that went stale because the
    course folder or the file moved is found again in the Material folder, and an old link into the hidden Wiki
    becomes a link to the file the Wiki page was made from (the page or time stays in the visible text)."""
    if course.legacy or not course.study.is_dir():
        return
    state = course.read_state("wiki.json", {})
    page_source = {info["page"]: rel for rel, info in state.items() if info.get("page")}
    recording_source = {folder: rel for rel, folder in material.wiki_folders(course.manifest()["files"]).items()}
    on_disk = {}
    for found in course.material.rglob("*") if course.material.is_dir() else []:
        on_disk.setdefault(found.name, []).append(found)

    def resolve(page, path):
        return (page.parent / unquote(path)).resolve()

    for page in sorted(course.study.rglob("*.md")):
        text = page.read_text("utf-8")

        def fix(match):
            label, raw = match.group(1), match.group(2).strip("<>")
            parsed = urlparse(raw)
            if parsed.scheme not in ("", "file"):
                return match.group(0)
            local = Path(url2pathname(parsed.path)) if parsed.scheme else resolve(page, raw.partition("#")[0])
            anchor = raw.partition("#")[2]
            if local.is_relative_to(course.wiki):  # an old link into the Wiki
                inner = local.relative_to(course.wiki).as_posix()
                rel = page_source.get(inner)
                where = re.fullmatch(r"page-(\d+)", anchor)
                if rel:
                    return f"[{label}{', page ' + where[1] if where else ''}]({material.path_of(course, rel).as_uri()})"
                folder = inner.rsplit("/", 1)[0]
                if folder in recording_source:
                    stamp = re.fullmatch(r"(\d\d)(\d\d)(\d\d)", anchor)
                    secs = int(stamp[1]) * 3600 + int(stamp[2]) * 60 + int(stamp[3]) if stamp else None
                    video = material.path_of(course, recording_source[folder]).as_uri()
                    return f"[{label}]({video}{'#t=' + str(secs) if secs is not None else ''})"
                return label  # nothing of the student's to point at
            if parsed.scheme != "file" or local.exists():
                return match.group(0)
            parts = local.parts  # a moved course folder: the same place under the Material folder now
            names = {course.material.name, *(t["material"] for t in LABELS.values())}
            for i, part in enumerate(parts):
                if part in names and (course.material / Path(*parts[i + 1:])).exists():
                    return _link(label, (course.material / Path(*parts[i + 1:])).as_uri() + (("#" + anchor) if anchor else ""))
            same = on_disk.get(local.name, [])  # a moved file: the one file of that name
            if len(same) == 1:
                return _link(label, same[0].as_uri() + (("#" + anchor) if anchor else ""))
            return match.group(0)

        fixed = MD_LINK.sub(fix, text)
        if fixed != text:
            page.write_text(fixed, "utf-8")


def _remove_stale_roadmaps(course, written):
    """A roadmap whose recordings are gone, or lost their summaries, is removed (what the student added around the
    generated block stays)."""
    names = {table["roadmap"] + ".md" for table in LABELS.values()}
    keep = {course.root / w for w in written}
    for page in sorted(course.study.rglob("*.md")) if course.study.is_dir() else []:
        if page.name not in names or page in keep:
            continue
        text = page.read_text("utf-8")
        if GEN_START not in text or GEN_END not in text:
            continue
        head, rest = text.split(GEN_START, 1)
        outside = (head + rest.split(GEN_END, 1)[1]).strip()
        if outside:
            page.write_text(outside + "\n", "utf-8")
        else:
            page.unlink()
            try:
                page.parent.rmdir()
            except OSError:
                pass


def coverage(course, write=False):
    """What the Wiki did and did not read, per file: analyzed, failed (with the reason), skipped (with who
    chose it) or pending. With write=True (the build) also saved as coverage.md in the Wiki, so a later session knows
    what is NOT in the Wiki. Showing it changes nothing on disk."""
    state = course.read_state("wiki.json", {})
    level = course.settings().get("recording_level")
    recordings = recording_pages(course)
    files, rows = course.manifest()["files"], []
    for rel in sorted(files):
        what = kind(rel)
        info = state.get(rel)
        if what == "document":
            if info is None or info.get("fingerprint") != files[rel].get("fingerprint"):
                status, why = "pending", "new or changed since the last build: run the Wiki build"
            elif info.get("method") == "none":
                status, why = "failed", " ".join(info.get("warnings") or ["could not be read"])
            elif info.get("empty_pages"):
                status = "analyzed"
                why = f"pages with no text layer need visual reading: {', '.join(map(str, info['empty_pages']))}"
            else:
                status, why = "analyzed", ""
        elif what == "recording":
            if recordings[rel]["processed"]:
                status, why = "analyzed", ""
            elif level in (0, 1):
                status, why = "skipped", "you chose " + ("not to process recordings" if level == 0 else "download only, no transcript")
            elif level is None:
                status, why = "pending", "you haven't chosen yet whether to transcribe recordings"
            else:
                status, why = "pending", "waiting for transcription (/unistudent:course-recordings)"
        elif what == "image":
            status, why = "skipped", "images are listed but not read"
        else:
            status, why = "skipped", "not a file type the Wiki reads"
        rows.append({"path": rel, "status": status, "why": why, "page": info["page"] if info and what == "document" else None})
    counts = {name: sum(1 for r in rows if r["status"] == name) for name in ("analyzed", "failed", "skipped", "pending")}
    lines = ["# Coverage: what the Wiki has and hasn't read", "",
             "Anything not marked analyzed is NOT in the Wiki: never present it as ✅ from the material.", ""]
    for name, title in (("failed", "Failed"), ("pending", "Not analyzed yet"), ("skipped", "Skipped"), ("analyzed", "Analyzed")):
        group = [r for r in rows if r["status"] == name]
        if group:
            lines += [f"## {title} ({len(group)})", ""]
            for r in group:
                label = _link(r["path"], r["page"]) if r["page"] else r["path"]
                lines.append(f"- {label}" + (f": {r['why']}" if r["why"] else ""))
            lines.append("")
    if write:
        course.wiki.mkdir(parents=True, exist_ok=True)
        (course.wiki / "coverage.md").write_text("\n".join(lines).rstrip() + "\n", "utf-8")
    summary = ", ".join(f"{n} {name}" for name, n in counts.items() if n) or "no files yet"
    return {"files": rows, "counts": counts, "summary": f"Coverage: {summary}."}


def check(course):
    problems = []
    for page in sorted(course.wiki.rglob("*.md")):
        problems += check_links(page, course.wiki)
        if page.name not in ("index.md", "coverage.md") and not has_sources(page):
            problems.append({"kind": "no-sources", "page": str(page)})
    return {"problems": problems,
            "summary": problems_summary(problems, lambda p: f"{p['kind']}: {p['page']} {p.get('link', '')}")}

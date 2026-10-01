"""Building the Wiki from the Material folder (the deterministic part).

The script converts documents, and writes the index and the generated block of each
unit page. Claude writes the rest (glossary, question bank, course page, the
methods/notation/assumptions of each unit) through the wiki skill; those parts are
never touched by a rebuild.
"""
import os
import re
from pathlib import Path

from . import material
from .common import problems_summary
from .convert import convert, kind
from .course import safe_name, unit_dir
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
    """Recordings and their Wiki folders (filled by the recordings pipeline).
    Folder names are unique and stable: sorted, with a suffix on name clashes."""
    out, used = {}, set()
    for rel, entry in sorted(course.manifest()["files"].items()):
        if kind(rel) == "recording":
            stem = safe_name(Path(rel).stem)
            folder, n = f"recordings/{stem}", 2
            while folder in used:
                folder, n = f"recordings/{stem} ({n})", n + 1
            used.add(folder)
            out[rel] = {"folder": folder, "unit": entry.get("unit"),
                        "processed": (course.wiki / folder / "summary.md").exists()}
    return out


def build(course, force=False):
    wiki = course.wiki
    wiki.mkdir(parents=True, exist_ok=True)
    found = material.scan(course)  # the folder is the truth: follow moves, drop deletions, take new files as added
    manifest = course.manifest()["files"]
    state = course.read_state("wiki.json", {})
    plan = _plan_pages(course)

    # Pages whose file was deleted, moved or renamed (the scan above already followed it in the Manifest).
    for rel, info in list(state.items()):
        if plan.get(rel) != info.get("page"):
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
    covered = coverage(course, write=True)
    roadmaps = write_roadmaps(course, recordings)

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


def _for_the_vault(path: Path) -> str:
    """A Wiki page as the student reads it in the Study vault: no frontmatter, no links into the hidden Wiki,
    headings two levels down."""
    text = re.sub(r"\A---\n.*?\n---\n", "", path.read_text("utf-8"), flags=re.S)
    return re.sub(r"(?m)^(#{1,4}) ", r"\1## ", MD_LINK.sub(lambda m: m.group(1), text)).strip()


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
            try:
                video = Path(os.path.relpath(material.path_of(course, rel), page.parent)).as_posix()
            except ValueError:  # a recording on another drive (Windows): link it by address
                video = material.path_of(course, rel).as_uri()
            lines += [f"## {Path(rel).name}", "", _link("recording", video), ""]
            for name in ("toc.md", "summary.md"):
                if (course.wiki / info["folder"] / name).exists():
                    lines += [_for_the_vault(course.wiki / info["folder"] / name), ""]
        _write_generated(page, "\n".join(lines))
        written.append(page.relative_to(course.root).as_posix())
    return written


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

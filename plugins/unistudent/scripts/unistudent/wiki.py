"""Building the Wiki from Raw (the deterministic part).

The script converts documents, and writes the index and the generated block of each
unit page. Claude writes the rest (glossary, question bank, course page, the
methods/notation/assumptions of each unit) through the wiki skill; those parts are
never touched by a rebuild.
"""
import re
from pathlib import Path

from . import material
from .common import problems_summary
from .convert import convert, kind
from .course import safe_name, unit_dir
from .links_check import STUB_MARK, check_links, has_sources

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
    """Stable Raw path → Wiki page mapping (sorted, so collisions resolve the same way every time)."""
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
    manifest = course.manifest()["files"]
    state = course.read_state("wiki.json", {})
    plan = _plan_pages(course)

    # Pages whose Raw file disappeared or moved to another unit.
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
        conversion = convert(material.raw_path(course, rel))
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_source_page(rel, entry, conversion), "utf-8")
        state[rel] = {"page": page, "fingerprint": entry.get("fingerprint"),
                      "method": conversion.method, "empty_pages": conversion.empty_pages}
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
    (wiki / "index.md").write_text("\n".join(index) + "\n", "utf-8")

    return {
        "converted": converted,
        "units_touched": sorted(touched),
        "pages": len(plan),
        "recordings": list(recordings),
        "images": images,
        "needs_visual": needs_visual,
        "warnings": warnings_out,
        "summary": f"Wiki: {converted} converted, {len(plan)} source pages, {len(recordings)} recordings, "
                   f"{len(images)} images and {len(needs_visual)} files needing visual reading.",
    }


def check(course):
    problems = []
    for page in sorted(course.wiki.rglob("*.md")):
        problems += check_links(page, course.wiki)
        if page.name != "index.md" and not has_sources(page):
            problems.append({"kind": "no-sources", "page": str(page)})
    return {"problems": problems,
            "summary": problems_summary(problems, lambda p: f"{p['kind']}: {p['page']} {p.get('link', '')}")}

"""Grounding rule (ADR 0009): an unmarked paragraph is from the course Wiki and must cite.

A paragraph is a block of text between blank lines. Headings, tables, code, comments,
frontmatter and navigation-only blocks (links and icons, no prose) are not checked.
A paragraph that starts with the warning ⚠️ is not from the Wiki and needs no source;
every other paragraph must cite at least one source link, and every link must resolve.
"""
import re
from pathlib import Path
from urllib.parse import unquote

from .course import Course
from .links_check import MD_LINK, WIKILINK, check_links

_WARNING_RE = re.compile("⚠️?")
_LEGACY_RE = re.compile("[\u2705\U0001F4A1\u274C]")  # old labels in existing pages read as plain text
_MARKER = re.compile(r"^\s*(?:>\s*)*(?:\[![^\]]*\][+-]?\s*)?(?:[-*+]\s+|\d+[.)]\s+)?(?:\*\*|__)?\s*")
_MIN_PROSE_LETTERS = 15
IMAGE_LINE = re.compile(r'^\s*!\[[^\]]*\]\((<[^>]+>|[^)\s]+)(?:\s+"[^"]*")?\)\s*$')


def _blank_comments(text):
    return re.sub(r"<!--.*?-->", lambda m: "\n" * m.group().count("\n"), text, flags=re.S)


def _blocks(text):
    text = _blank_comments(text)
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == "---"), None)
        if end is not None:
            lines = [""] * (end + 1) + lines[end + 1:]
    blocks, current, start, in_code = [], [], 0, False
    for number, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        stripped = line.strip()
        skip = (not stripped or stripped.startswith("#") or stripped.startswith("|")
                or re.fullmatch(r"[-*_]{3,}", stripped))
        if skip:
            if current:
                blocks.append((start, current))
                current = []
            continue
        if IMAGE_LINE.match(line):  # a graph's picture carries no claim; its caption line below does
            if current:
                blocks.append((start, current))
                current = []
            continue
        if not current:
            start = number
        current.append(line)
    if current:
        blocks.append((start, current))
    return blocks


def _prose_letters(text):
    text = MD_LINK.sub("", text)
    text = WIKILINK.sub("", text)
    return len(re.findall(r"[^\W\d_]", text))


_CLOSING_LINE = re.compile(r"(?i)^\W*(?:from|sources|מתוך|מקורות)\W*:")
_SOURCES_START = re.compile(r"(?i)^\s*(?:[-*>]\s*)?(?:\*\*)?(sources|מקורות)(?:\*\*)?\s*:")
_LIST_LINE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")


def _merge_continuations(blocks):
    """A trailing "Sources:" block, or a list right after a paragraph, belongs to that paragraph."""
    merged = []
    for start, lines in blocks:
        if merged:
            prev = merged[-1][1]
            is_sources = bool(_SOURCES_START.match(lines[0]))
            is_intro_list = not _LIST_LINE.match(prev[0]) and not _WARNING_RE.match(
                _MARKER.sub("", lines[0], count=1)) and all(
                _LIST_LINE.match(l) or l.startswith((" ", "\t")) for l in lines)
            if is_sources or is_intro_list:
                prev.extend(lines)
                continue
        merged.append((start, list(lines)))
    return merged


def paragraphs(text):
    """[{line, warning, links, text}] for every paragraph that makes a claim."""
    out = []
    for start, lines in _merge_continuations(_blocks(text)):
        body = "\n".join(lines)
        if _prose_letters(_WARNING_RE.sub("", _LEGACY_RE.sub("", body))) < _MIN_PROSE_LETTERS:
            continue
        head = _MARKER.sub("", lines[0], count=1)
        links = [t for _, t in MD_LINK.findall(body)] + [n for n, _, _ in WIKILINK.findall(body)]
        out.append({"line": start, "warning": bool(_WARNING_RE.match(_LEGACY_RE.sub("", head).lstrip())),
                    "body": body, "links": links, "text": body.strip()[:120]})
    return out


def graph_problems(page: Path, text: str):
    """Graphs (images in a graphs/ folder) need an existing file and a caption on the next line that cites or carries the warning."""
    problems, in_code = [], False
    lines = _blank_comments(text).split("\n")
    for number, line in enumerate(lines, 1):
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        match = None if in_code else IMAGE_LINE.match(line)
        if not match or "graphs/" not in match.group(1):
            continue
        target = match.group(1).strip("<>")
        where = {"page": str(page), "line": number, "text": target}
        if not (Path(page).parent / unquote(target)).is_file():
            problems.append({"kind": "missing-image", **where})
        caption = lines[number] if number < len(lines) else ""
        head = _LEGACY_RE.sub("", _MARKER.sub("", caption, count=1)).lstrip()
        if not caption.strip():
            problems.append({"kind": "graph-no-caption", **where})
        elif not _WARNING_RE.match(head) and not MD_LINK.search(caption) and not WIKILINK.search(caption):
            problems.append({"kind": "no-citation", **where})
    return problems


def check_page(page: Path, root: Path):
    """Warning and citation problems in one answer or study-pack page."""
    from .wiki import GEN_END, GEN_START
    page = Path(page)
    text = page.read_text("utf-8")
    if GEN_START in text and GEN_END in text:  # the block UniStudent generates (the recordings roadmap) is checked for
        start = text.index(GEN_START)         # links only; everything around it for the rule (line numbers stay)
        end = text.index(GEN_END, start) + len(GEN_END)
        text = text[:start] + re.sub(r"[^\n]", "", text[start:end]) + text[end:]
    found = paragraphs(text)
    pack = re.match(r"\d+\.\d", page.name)  # a Study pack page carries its own sources block (only chat answers do)
    problems = [p for p in graph_problems(page, text) if not pack or p["kind"] == "missing-image"]
    for p in found:
        where = {"page": str(page), "line": p["line"], "text": p["text"]}
        if pack or p["warning"] or p["links"]:
            continue
        if _CLOSING_LINE.match(p["text"]):
            continue
        if any(f"{name}/" in p["body"] for name in ("inbox", Course(root).inbox.name)) and len(p["body"]) < 300:
            continue  # the closing "add material to inbox/" suggestion is not a claim
        problems.append({"kind": "no-citation", **where})
    problems += check_links(page, root)
    return {"paragraphs": found, "problems": problems}


def grade(case: dict, answer: Path, root: Path):
    """Score one eval answer against its case."""
    report = check_page(answer, root)
    warned = any(p["warning"] for p in report["paragraphs"])
    links = " ".join(link for p in report["paragraphs"] for link in p["links"])
    text = Path(answer).read_text("utf-8")
    failures = []
    if case.get("must_warn") and not warned:
        failures.append("missing warning")
    if case.get("must_not_warn") and warned:
        failures.append("forbidden warning")
    failures += [f"missing citation {c}" for c in case.get("must_cite", []) if c not in links]
    failures += [f"missing mention {m}" for m in case.get("must_mention", [])
                 if not any(alt.strip().lower() in text.lower() for alt in m.split("|"))]
    failures += [f"{p['kind']} at line {p.get('line', '?')}" for p in report["problems"]]
    return {"id": case.get("id"), "passed": not failures, "failures": sorted(failures)}

"""Grounding labels: one per paragraph (spec, "Grounding rule").

A paragraph is a block of text between blank lines. Headings, tables, code, comments,
frontmatter and navigation-only blocks (links and icons, no prose) carry no label.
✅ (from course material) and 💡 (my explanation of course material) paragraphs must cite
at least one source link, and every link must resolve.
"""
import re
from pathlib import Path
from urllib.parse import unquote

from .course import Course
from .links_check import MD_LINK, WIKILINK, check_links

CITED = ("✅", "💡")  # these must link the course material they rest on
_LABEL_RE = re.compile("✅|💡|⚠️?|❌")
_MARKER = re.compile(r"^\s*(?:>\s*)*(?:\[![^\]]*\][+-]?\s*)?(?:[-*+]\s+|\d+[.)]\s+)?(?:\*\*|__)?\s*")
_MIN_PROSE_LETTERS = 15
IMAGE_LINE = re.compile(r'^\s*!\[[^\]]*\]\((<[^>]+>|[^)\s]+)(?:\s+"[^"]*")?\)\s*$')


def _normalise(label):
    return "⚠️" if label.startswith("⚠") else label


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


_SOURCES_START = re.compile(r"(?i)^\s*(?:[-*>]\s*)?(?:\*\*)?(sources|מקורות)(?:\*\*)?\s*:")
_LIST_LINE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+")


def _merge_continuations(blocks):
    """A trailing "Sources:" block, or an unlabelled list right after a paragraph, belongs to that paragraph."""
    merged = []
    for start, lines in blocks:
        if merged:
            prev = merged[-1][1]
            is_sources = bool(_SOURCES_START.match(lines[0]))
            is_intro_list = not _LIST_LINE.match(prev[0]) and not _LABEL_RE.match(
                _MARKER.sub("", lines[0], count=1)) and all(
                _LIST_LINE.match(l) or l.startswith((" ", "\t")) for l in lines)
            if is_sources or is_intro_list:
                prev.extend(lines)
                continue
        merged.append((start, list(lines)))
    return merged


def paragraphs(text):
    """[{line, label, labels_at_start, links, text}] for every paragraph that needs a label."""
    out = []
    for start, lines in _merge_continuations(_blocks(text)):
        body = "\n".join(lines)
        if _prose_letters(_LABEL_RE.sub("", body)) < _MIN_PROSE_LETTERS:
            continue
        head = _MARKER.sub("", lines[0], count=1)
        labels = []
        while True:
            match = _LABEL_RE.match(head)
            if not match:
                break
            labels.append(_normalise(match.group(0)))
            head = head[match.end():].lstrip()
        links = [t for _, t in MD_LINK.findall(body)] + [n for n, _, _ in WIKILINK.findall(body)]
        out.append({"line": start, "label": labels[0] if len(labels) == 1 else None, "body": body,
                    "labels_at_start": labels, "links": links, "text": body.strip()[:120]})
    return out


def graph_problems(page: Path, text: str):
    """Graphs (images in a graphs/ folder) need an existing file and a ✅ or 💡 caption on the next line."""
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
        label = _LABEL_RE.match(_MARKER.sub("", caption, count=1))
        if not label:
            problems.append({"kind": "graph-no-caption", **where})
        elif _normalise(label.group(0)) not in CITED:
            problems.append({"kind": "graph-label", **where})
        elif not MD_LINK.search(caption) and not WIKILINK.search(caption):
            problems.append({"kind": "no-citation", **where})
    return problems


def check_page(page: Path, root: Path):
    """Label and citation problems in one answer or study-pack page."""
    from .wiki import GEN_START
    page = Path(page)
    text = page.read_text("utf-8")
    if GEN_START in text:  # a page UniStudent generates (the recordings roadmap): the checks that apply are links
        return {"paragraphs": [], "problems": check_links(page, root)}
    found = paragraphs(text)
    problems = graph_problems(page, text)
    for p in found:
        where = {"page": str(page), "line": p["line"], "text": p["text"]}
        if not p["labels_at_start"]:
            if any(f"{name}/" in p["body"] for name in ("inbox", Course(root).inbox.name)) and len(p["body"]) < 300:
                continue  # the closing "add material to inbox/" suggestion is not a claim
            problems.append({"kind": "unlabeled", **where})
        elif len(p["labels_at_start"]) > 1:
            problems.append({"kind": "several-labels", **where})
        elif p["label"] in CITED and not p["links"]:
            problems.append({"kind": "no-citation", **where})
    problems += check_links(page, root)
    return {"paragraphs": found, "problems": problems}


def grade(case: dict, answer: Path, root: Path):
    """Score one eval answer against its case."""
    report = check_page(answer, root)
    labels = {p["label"] for p in report["paragraphs"] if p["label"]}
    links = " ".join(link for p in report["paragraphs"] for link in p["links"])
    text = Path(answer).read_text("utf-8")
    failures = [f"missing label {l}" for l in case.get("must_include_labels", []) if l not in labels]
    failures += [f"forbidden label {l}" for l in case.get("must_not_include_labels", []) if l in labels]
    failures += [f"missing citation {c}" for c in case.get("must_cite", []) if c not in links]
    failures += [f"missing mention {m}" for m in case.get("must_mention", [])
                 if not any(alt.strip().lower() in text.lower() for alt in m.split("|"))]
    failures += [f"{p['kind']} at line {p.get('line', '?')}" for p in report["problems"]]
    return {"id": case.get("id"), "passed": not failures, "failures": sorted(failures)}

"""Checking that every link in a Markdown page resolves, and that pages cite sources.

Understands Markdown links, Obsidian wikilinks, #heading anchors and file:// links.
Used for the Wiki (`wiki check`) and study packs (`check`).
"""
import html
import re
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

MD_LINK = re.compile(r'(?<!!)\[([^\]]*)\]\((<[^>]+>|[^)\s]+)(?:\s+"[^"]*")?\)')
WIKILINK = re.compile(r"!?\[\[([^\]|#]*)(#[^\]|]*)?(\|[^\]]*)?\]\]")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*#*\s*$", re.M)
FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)
SOURCES_LINE = re.compile(r"(?im)^\s*(?:[-*>]\s*)?(?:\*\*)?(sources|מקורות|source|מקור)(?:\*\*)?\s*:")
STUB_MARK = "<!-- unistudent:stub -->"
CODE_BLOCK = re.compile(r"```.*?```|<!--.*?-->", re.S)
HREF = re.compile(r'href="([^"]+)"')


def _links(page: Path, text: str):
    """(label, target) of every link: Markdown links, plus href attributes in an .html page."""
    found = MD_LINK.findall(text)
    return found + [("", html.unescape(h)) for h in HREF.findall(text)] if page.suffix == ".html" else found


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFC", text).strip().lower()
    text = re.sub(r"[^\w\s\-]", "", text)
    return re.sub(r"\s+", "-", text)


def headings(path: Path):
    try:
        text = path.read_text("utf-8")
    except (OSError, UnicodeDecodeError):
        return set()
    found = set()
    for title in HEADING.findall(CODE_BLOCK.sub("", text)):
        found.add(slugify(title))
        found.add(title.strip())
    return found


def _anchor_ok(target: Path, anchor: str) -> bool:
    if not anchor or target.suffix.lower() != ".md":
        return True
    anchor = unquote(anchor)
    names = headings(target)
    return anchor in names or slugify(anchor) in names


def _find_by_name(root: Path, name: str):
    for candidate in (name, name + ".md"):  # a numbered page ("4.2 Walkthrough") looks like it has a suffix, so try both
        matches = sorted(root.rglob(Path(candidate).name), key=lambda p: len(p.parts))
        for match in matches:
            if match.is_file() and match.as_posix().endswith(candidate):
                return match
    return None


def check_links(page: Path, root: Path):
    """Problems with links in one page. `root` is where wikilinks are resolved from."""
    text = CODE_BLOCK.sub("", page.read_text("utf-8"))
    problems = []
    for label, raw_target in _links(page, text):
        target = raw_target.strip("<>")
        parsed = urlparse(target)
        if parsed.scheme in ("http", "https", "mailto", "obsidian"):
            continue
        if parsed.scheme == "file":
            path = Path(url2pathname(parsed.path))
            if not path.exists():
                problems.append({"kind": "broken-link", "page": str(page), "link": target})
            continue
        path_part, _, anchor = target.partition("#")
        dest = page if not path_part else (page.parent / unquote(path_part)).resolve()
        if not dest.exists():
            problems.append({"kind": "broken-link", "page": str(page), "link": target})
        elif not _anchor_ok(dest, anchor):
            problems.append({"kind": "broken-anchor", "page": str(page), "link": target})
    for name, anchor, _ in WIKILINK.findall(text):
        if not name:
            dest = page
        else:
            dest = (root / name) if (root / name).exists() else _find_by_name(root, name)
        if dest is None or not dest.exists():
            problems.append({"kind": "broken-link", "page": str(page), "link": f"[[{name}{anchor}]]"})
        elif not _anchor_ok(dest, anchor.lstrip("#")):
            problems.append({"kind": "broken-anchor", "page": str(page), "link": f"[[{name}{anchor}]]"})
    return problems


def has_sources(page: Path) -> bool:
    text = page.read_text("utf-8")
    if STUB_MARK in text:
        return True
    front = FRONTMATTER.match(text)
    if front and re.search(r"(?m)^source:", front.group(1)):
        return True
    if SOURCES_LINE.search(text):
        return True
    # Pages of entries (glossary, question bank) cite per entry: a link into the material counts.
    body = CODE_BLOCK.sub("", text)
    links = [t for _, t in MD_LINK.findall(body)] + [name for name, _, _ in WIKILINK.findall(body)]
    for target in links:
        path = unquote(target.strip("<>").partition("#")[0])
        if re.search(r"(^|/)(sources|recordings)/", path) and (page.parent / path).exists():
            return True
    return False


def check_vault_page(page: Path, hidden: Path):
    """A page in the Study vault never links into the hidden folder (the Wiki is for the AI, not the student)."""
    problems = []
    for _, raw in _links(page, CODE_BLOCK.sub("", page.read_text("utf-8"))):
        target = raw.strip("<>")
        parsed = urlparse(target)
        if parsed.scheme not in ("", "file"):
            continue
        path = Path(url2pathname(parsed.path)) if parsed.scheme else (page.parent / unquote(target.partition("#")[0]))
        if path.resolve().is_relative_to(hidden.resolve()):
            problems.append({"kind": "link-into-hidden", "page": str(page), "link": target})
    return problems


PRACTICE_PAGE = re.compile(r"^\d+\.3(?!\d)")
WALKTHROUGH_PAGE = re.compile(r"^\d+\.2(?!\d)")
CLOSING_FROM = re.compile(r"(?im)^\s*(?:[-*>]\s*)?(?:\*\*)?(?:from|מתוך)(?:\*\*)?\s*:")
STAGE = re.compile(r"(?im)^\s*(?:#+\s*|[-*>]\s*)?(?:\*\*)?(?:stage|שלב)\s+\d")
TOPIC_TAG = re.compile(r"(?<![\w&])#(?:unit-\d+/|י\d+/)")
IMAGE = re.compile(r"!\[[^\]]*\]\(|!\[\[")


def check_pack_page(page: Path):
    """Study pack shape (ticket 18): a walkthrough topic closes with a "From:" line; the Practice page has no stages, tags or graphs; no `N.3b` page."""
    text = CODE_BLOCK.sub("", page.read_text("utf-8"))
    problems = []

    def problem(kind, text_=""):
        problems.append({"kind": kind, "page": str(page), "text": text_})

    if re.match(r"^\d+\.3b", page.name):
        problem("short-practice-page", "the Short version closes the Practice page; there is no separate page")
    elif PRACTICE_PAGE.match(page.name):
        for kind, pattern in (("practice-stage", STAGE), ("practice-tag", TOPIC_TAG), ("practice-graph", IMAGE)):
            if (hit := pattern.search(text)):
                problem(kind, hit.group(0).strip())
    elif WALKTHROUGH_PAGE.match(page.name):
        for section in re.split(r"(?m)^## ", text)[1:]:
            if re.search(r"(?m)^### ", section) and not CLOSING_FROM.search(section):
                problem("topic-missing-from-line", section.splitlines()[0][:80])
    return problems


SECTION = re.compile(r"(?ms)^## (Notation|Assumptions)\s*$(.*?)(?=^## |\Z)")
# A Latin symbol: up to four Latin letters, then digits or a _subscript (Y, MPC, C0, Y_d); a longer word is not one.
SYMBOL = re.compile(r"(?<![A-Za-z0-9_./#])[A-Za-z]{1,4}(?:_[A-Za-z0-9]+|[0-9]+)?(?!\.?[A-Za-z0-9])")
ASSUMPTION = re.compile(r"(?i)(?:assumption|הנחה)\D{0,8}?(\d+)")
MATH = re.compile(r"\$\$?(.+?)\$\$?", re.S)
NOT_PROSE = re.compile(r"!?\[\[[^\]]*\]\]|!?\[[^\]]*\]\([^)]*\)|https?://\S+|<[^>]+>|\[![^\]]*\]|\A---\n.*?\n---\n", re.S)
QUOTE = re.compile(r'(?<!\w)["“„](.+?)["”“](?!\w)', re.S)
LABEL_LINE = re.compile(r"^\s*(?:>\s*)*(?:[-*+]\s+)?\*\*")


def _normal(text):
    """Text with whitespace and punctuation gone, so a quote matches its source however it was wrapped."""
    return re.sub(r"[\W_]+", "", unicodedata.normalize("NFKC", text)).casefold()


def check_pack_against_unit(page: Path, course):
    """Notation and quotes of a pack page against its unit's Wiki (ticket 30): every Latin symbol and assumption number
    is listed in the unit page's Notation or Assumptions sections; every quote in a Say it or Model answer block occurs
    in the unit's source pages. Course-language terms are left to the verifier (the glossary)."""
    from .course import LABELS, parse_unit_folder, unit_dir
    known, unit = parse_unit_folder(page.parent.name)
    if not known or not isinstance(unit, int):
        return []
    unit_page = course.wiki / "units" / f"{unit_dir(unit)}.md"
    listed = " ".join(m.group(2) for m in SECTION.finditer(unit_page.read_text("utf-8") if unit_page.is_file() else ""))
    text = NOT_PROSE.sub(" ", CODE_BLOCK.sub("", page.read_text("utf-8")))
    problems = []

    def problem(kind, text_):
        problems.append({"kind": kind, "page": str(page), "text": text_})

    if listed:  # a unit page with neither section is not written yet: nothing to check against
        language = course.settings()["language"]
        prose = " ".join(MATH.findall(text)) if language == "en" else text  # in English every short word looks Latin
        symbols, numbers = set(SYMBOL.findall(listed)), set(re.findall(r"\d+", listed))
        for symbol in dict.fromkeys(SYMBOL.findall(prose)):
            if symbol not in symbols:
                problem("notation", symbol)
        for hit in ASSUMPTION.finditer(text):
            if hit.group(1) not in numbers:
                problem("notation", hit.group(0))

    labels = {_normal(table[key]) for table in LABELS.values() for key in ("model_answer", "say_it")}
    sources = None
    lines = text.split("\n")
    for i, line in enumerate(lines):
        head = re.match(r"^\s*(?:>\s*)*(?:[-*+]\s+)?\*\*([^*]+)\*\*", line)
        if not head or _normal(head.group(1)) not in labels:
            continue
        block = [line[head.end():]]
        for more in lines[i + 1:]:
            if not more.strip() or LABEL_LINE.match(more):
                break
            block.append(more)
        for quote in QUOTE.findall("\n".join(block)):
            if sources is None:
                folder = course.wiki / "sources"
                sources = _normal(" ".join(p.read_text("utf-8") for name in (unit_dir(unit), "general")
                                           for p in sorted((folder / name).glob("*.md"))))
            if _normal(quote) and _normal(quote) not in sources:
                problem("quote", quote.strip()[:80])
    return problems


RETURN_PAGE = re.compile(r"^\s*(?:[-*]\s+)?\d+\.\d\b\S*\s+\S")
RETURN_GAP = re.compile(r"^\s*[-*]\s+\w+\s+·\s+[^·]*\S[^·]*·\s*\S")


def check_return(path: Path):
    """The writer's return (ticket 30): the page list, one line per page, then `Known gaps:` and one line per gap as
    kind · page · what's missing (or `Known gaps: none`). One `return` problem names the first line out of shape."""
    lines = [line for line in path.read_text("utf-8").splitlines() if line.strip()]
    gaps = next((i for i, line in enumerate(lines) if re.match(r"^\s*(?:\*\*)?Known gaps:", line)), None)
    if gaps is None:
        bad = "no `Known gaps:` line"
    elif gaps == 0:
        bad = "no page list before `Known gaps:`"
    else:
        tail = lines[gaps].split(":", 1)[1].strip(" *")
        wrong = ([line for line in lines[:gaps] if not RETURN_PAGE.match(line)]
                 + ([lines[gaps]] if tail and tail.lower() != "none" else [])
                 + [line for line in lines[gaps + 1:] if not RETURN_GAP.match(line)])
        bad = wrong[0].strip()[:80] if wrong else None
    return [{"kind": "return", "page": str(path), "text": bad}] if bad else []

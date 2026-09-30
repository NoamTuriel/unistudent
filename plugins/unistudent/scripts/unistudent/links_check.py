"""Checking that every link in a Markdown page resolves, and that pages cite sources.

Understands Markdown links, Obsidian wikilinks, #heading anchors and file:// links.
Used for the Wiki (`wiki check`) and study packs (`check`).
"""
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
    name = name if Path(name).suffix else name + ".md"
    matches = sorted(root.rglob(Path(name).name), key=lambda p: len(p.parts))
    for match in matches:
        if match.as_posix().endswith(name):
            return match
    return None


def check_links(page: Path, root: Path):
    """Problems with links in one page. `root` is where wikilinks are resolved from."""
    text = CODE_BLOCK.sub("", page.read_text("utf-8"))
    problems = []
    for label, raw_target in MD_LINK.findall(text):
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

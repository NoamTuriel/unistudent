"""Assigning files to units on clear evidence only.

Evidence, strongest first: the file name, then the nearest parent folder name,
then the first lines of a PDF's first page. Exactly one unit number must be found;
anything ambiguous or missing goes to unsorted and the student is asked.
"""
import logging
import re
import warnings
from pathlib import Path

logging.getLogger("pypdf").setLevel(logging.CRITICAL)

ENGLISH_PATTERNS = [  # always, whatever the course language
    r"(?i)\bunit[\s_\-]*(\d{1,2})(?!\d)",
    r"(?i)\bchapter[\s_\-]*(\d{1,2})(?!\d)",
]


def _units_in(text, patterns):
    found = set()
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            found.add(int(match.group(1)))
    return found


def _pdf_first_lines(path: Path) -> str:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from pypdf import PdfReader  # optional
        reader = PdfReader(str(path))
        if not reader.pages:
            return ""
        return (reader.pages[0].extract_text() or "")[:400]
    except Exception:
        return ""


def detect_unit(rel_path: str, unit_label: str, file_path: Path = None):
    """Return (unit or None, reason). `unit_label`: the course's label for a unit folder ("יחידה {n}"), whose word
    before the number also names a unit, besides the English words."""
    word = unit_label.split("{n}")[0].strip()  # ponytail: a language that puts the number first ("{n}. Kapitel") adds no word
    patterns = ENGLISH_PATTERNS + ([rf"(?i){re.escape(word)}[\s_\-]*(\d{{1,2}})(?!\d)"] if word else [])
    parts = Path(rel_path).parts
    name = parts[-1]
    for label, text in [("file name", Path(name).stem)] + [
        ("folder name", folder) for folder in reversed(parts[:-1])
    ]:
        units = _units_in(text, patterns)
        if len(units) == 1:
            return units.pop(), label
        if len(units) > 1:
            return None, f"{label} names several units"
    if file_path is not None and Path(name).suffix.lower() == ".pdf":
        units = _units_in(_pdf_first_lines(file_path), patterns)
        if len(units) == 1:
            return units.pop(), "first page title"
    return None, "no unit evidence"

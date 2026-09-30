"""Turning course documents into text pages. Best available tool first, pure-Python fallback.

Returns a Conversion: a list of page texts, the method used, and warnings.
Pages whose text layer is (almost) empty are reported, so Claude can read them visually.
"""
import logging
import shutil
import subprocess
import tempfile
import warnings
from dataclasses import dataclass, field
from pathlib import Path

logging.getLogger("pypdf").setLevel(logging.CRITICAL)

DOCUMENTS = {".pdf", ".docx", ".doc", ".odt", ".rtf", ".pptx", ".ppt", ".odp", ".txt", ".md",
             ".xlsx", ".xls", ".html", ".htm", ".epub"}
MARKITDOWN_ONLY = {".xlsx", ".xls", ".html", ".htm", ".epub"}
RECORDINGS = {".mp4", ".mkv", ".mov", ".m4v", ".webm", ".avi", ".mp3", ".m4a", ".wav", ".aac"}
IMAGES = {".png", ".jpg", ".jpeg", ".heic", ".webp", ".gif", ".tif", ".tiff"}
OFFICE = {".docx", ".doc", ".odt", ".rtf", ".pptx", ".ppt", ".odp"}
EMPTY_PAGE_CHARS = 20


@dataclass
class Conversion:
    pages: list
    method: str
    warnings: list = field(default_factory=list)

    @property
    def empty_pages(self):
        return [i + 1 for i, text in enumerate(self.pages) if len(text.strip()) < EMPTY_PAGE_CHARS]


def kind(path) -> str:
    suffix = Path(path).suffix.lower()
    if suffix in DOCUMENTS:
        return "document"
    if suffix in RECORDINGS:
        return "recording"
    if suffix in IMAGES:
        return "image"
    return "other"


def _soffice():
    return shutil.which("soffice") or shutil.which("libreoffice")


def _pdf_pages(path: Path) -> Conversion:
    if shutil.which("pdftotext"):
        result = subprocess.run(["pdftotext", "-layout", "-enc", "UTF-8", str(path), "-"],
                                capture_output=True)
        if result.returncode == 0:
            pages = result.stdout.decode("utf-8", "replace").split("\f")
            if pages and not pages[-1].strip():
                pages = pages[:-1]
            return Conversion(pages, "pdftotext")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from pypdf import PdfReader
            reader = PdfReader(str(path))
            return Conversion([p.extract_text() or "" for p in reader.pages], "pypdf")
    except ImportError:
        return Conversion([], "none", ["No PDF tool: install poppler (pdftotext) or `pip install pypdf`."])
    except Exception as error:  # damaged file
        return Conversion([], "none", [f"Could not read PDF: {error}"])


def _via_pdf(path: Path) -> Conversion:
    """Office → PDF with LibreOffice first: direct text export loses formulas."""
    with tempfile.TemporaryDirectory() as out:
        result = subprocess.run([_soffice(), "--headless", "--convert-to", "pdf", "--outdir", out, str(path)],
                                capture_output=True, timeout=300)
        pdf = Path(out) / (path.stem + ".pdf")
        if result.returncode == 0 and pdf.exists():
            conversion = _pdf_pages(pdf)
            conversion.method = "soffice+" + conversion.method
            return conversion
    return None


def _docx_text(path: Path) -> Conversion:
    import docx
    document = docx.Document(str(path))
    parts = [p.text for p in document.paragraphs]
    for table in document.tables:
        for row in table.rows:
            parts.append(" | ".join(cell.text.strip() for cell in row.cells))
    return Conversion(["\n".join(parts)], "python-docx",
                      ["Formulas may be missing: install LibreOffice for full fidelity."])


def _markitdown(path: Path):
    """Microsoft MarkItDown (pip install 'markitdown[all]'), when installed: many formats, one page."""
    try:
        from markitdown import MarkItDown
    except ImportError:
        return None
    try:
        text = MarkItDown().convert(str(path)).text_content
    except Exception as error:
        return Conversion([], "none", [f"markitdown could not read it: {error}"])
    return Conversion([text], "markitdown")


def _pptx_text(path: Path) -> Conversion:
    from pptx import Presentation
    slides = []
    for slide in Presentation(str(path)).slides:
        texts = [shape.text_frame.text for shape in slide.shapes if shape.has_text_frame]
        slides.append("\n".join(texts))
    return Conversion(slides, "python-pptx")


def convert(path) -> Conversion:
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in (".txt", ".md"):
        return Conversion([path.read_text("utf-8", errors="replace")], "text")
    if suffix == ".pdf":
        return _pdf_pages(path)  # page by page, so citations can point at a page
    if suffix in MARKITDOWN_ONLY:
        return _markitdown(path) or Conversion([], "none", [f"Install markitdown to read {suffix} files."])
    if suffix in OFFICE:
        if _soffice():  # LibreOffice → PDF keeps formulas and pages
            conversion = _via_pdf(path)
            if conversion is not None:
                return conversion
        conversion = _markitdown(path)
        if conversion is not None and conversion.pages:
            return conversion
        try:
            if suffix == ".docx":
                return _docx_text(path)
            if suffix == ".pptx":
                return _pptx_text(path)
        except ImportError:
            pass
        return Conversion([], "none", [f"Cannot convert {suffix}: install LibreOffice."])
    return Conversion([], "none", [f"Not a document: {suffix}"])

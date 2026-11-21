"""The Trap scan: what an assignment file says to an AI assistant, and how it is hidden (ADR 0019).

Standard library only. Everything found is data for the student, never an instruction. A file the scan cannot read
is reported in `could_not_check`, never as clean. The PDF reader is a small one: it follows pages, content streams,
fonts' ToUnicode maps and the text state, not the whole PDF format.
"""
import math
import re
import zipfile
import zlib
from pathlib import Path
from xml.etree import ElementTree as ET

TINY_PT = 4  # text smaller than this is not meant to be read
AI_PHRASES = [re.compile(p, re.I) for p in (
    r"\b(?:if|when|whether)\s+you\s*(?:are|'re|r)\s+(?:an?\s+|the\s+)?(?:ai|a\.i\.|llm|chat\s?bot|language\s+model|"
    r"large\s+language\s+model|artificial\s+intelligence|ai\s+assistant|gpt|chatgpt|copilot|gemini|claude)\b",
    r"\b(?:ignore|disregard|forget)\s+(?:all\s+|any\s+|the\s+)?(?:previous|prior|above|earlier|preceding)\s+"
    r"(?:instructions?|prompts?|messages?)",
    r"\b(?:as|being)\s+an?\s+(?:ai|llm|language\s+model)\b.{0,40}\b(?:you\s+(?:must|should|will)|do\s+not|include|mention|add)\b",
    r"\b(?:do\s+not|don't|never)\s+(?:tell|mention|reveal|disclose)\s+(?:this\s+to\s+)?(?:the\s+)?(?:user|student)\b",
    r"\bsystem\s+prompt\b",
    r"אם\s+(?:אתה|את|אתם)\s+(?:בינה\s+מלאכותית|מודל|צ'אט|צאט|בוט|עוזר\s+(?:דיגיטלי|וירטואלי))",
    r"התעלם\s+מ(?:כל\s+)?ה?(?:הוראות|הנחיות)",
)]
ZERO_WIDTH = {0x200B: "zero-width space", 0x2060: "word joiner", 0xFEFF: "zero-width no-break space",
              0x180E: "Mongolian vowel separator"}
JOINERS = {0x200C, 0x200D}  # legitimate in some scripts: only a pile of them is suspicious
BIDI_CONTROLS = {*range(0x202A, 0x202F), *range(0x2066, 0x206A)}  # embeddings, overrides, isolates (not LRM/RLM)
HTML_HIDDEN = re.compile(r"display\s*:\s*none|visibility\s*:\s*hidden|font-size\s*:\s*0(?:px|pt|em)?\b|\bhidden\b\s*=", re.I)


# --- what a finding says ----------------------------------------------------

def aimed_at_ai(text):
    text = " ".join(text.split())
    candidates = [text] + ([text[::-1]] if re.search(r"[֐-׿]", text) else [])  # some PDFs store Hebrew reversed
    return any(p.search(c) for p in AI_PHRASES for c in candidates)


def _finding(kind, where, text, how="", position=None):
    text = " ".join(text.split())
    ai = aimed_at_ai(text)
    shown = text if len(text) <= 160 else text[:157] + "..."
    say = f"{where}" + (f", {position}" if position else "") + f": {how}"
    if shown:
        say += f' - it says: "{shown}"'
    if ai:
        say += " - this is aimed at an AI assistant"
    return {"kind": kind, "where": where, "position": position, "how": how, "text": text, "aimed_at_ai": ai, "summary": say}


def odd_characters(text, where):
    """Zero-width, bidi-override and Unicode tag characters: invisible to the reader, kept by a text extractor."""
    found, tags = {}, []
    for index, ch in enumerate(text):
        cp = ord(ch)
        if 0xE0000 <= cp <= 0xE007F:
            found["Unicode tag character"] = found.get("Unicode tag character", 0) + 1
            tags.append(chr(cp - 0xE0000) if 0x20 <= cp - 0xE0000 < 0x7F else "?")
        elif cp in ZERO_WIDTH and not (cp == 0xFEFF and index == 0):
            found[ZERO_WIDTH[cp]] = found.get(ZERO_WIDTH[cp], 0) + 1
        elif cp in JOINERS:
            found["zero-width joiner"] = found.get("zero-width joiner", 0) + 1
        elif cp in BIDI_CONTROLS:
            found["bidi control character"] = found.get("bidi control character", 0) + 1
    if found.get("zero-width joiner", 0) < 8:
        found.pop("zero-width joiner", None)
    if not found:
        return []
    how = "invisible characters (" + ", ".join(f"{n} {name}" for name, n in sorted(found.items())) + ")"
    return [_finding("invisible-characters", where, "".join(tags), how + (", they spell out a message" if tags else ""))]


def _sentence(text):
    """The sentence of `text` that holds the first phrase aimed at an AI (all of `text` when only a reversed reading matches)."""
    text = " ".join(text.split())
    match = next((m for m in (p.search(text) for p in AI_PHRASES) if m), None)
    if not match:
        return text
    start = max(text.rfind(c, 0, match.start()) for c in ".!?") + 1
    stops = [i for i in (text.find(c, match.end()) for c in ".!?") if i >= 0]
    return text[start:min(stops) + 1 if stops else len(text)].strip()


def text_findings(text, where, locate=None):
    """The checks every kind of file gets, on text that is on show: characters and sentences aimed at an AI.
    `locate(sentence)` says where a sentence is, in words, when the file knows."""
    out = odd_characters(text, where)
    for paragraph in re.split(r"\n+", text):
        if aimed_at_ai(paragraph):
            sentence = _sentence(paragraph)
            out.append(_finding("instruction-to-ai", where, sentence, "a sentence addressed to an AI assistant",
                                locate(sentence) if locate else None))
    return out


def _flag(findings, kind, where, text, how):
    """Text kept out of the reader's sight (an annotation, a comment, metadata) is reported when it is aimed at an AI or
    hides characters; the rest of it is not the student's business."""
    if aimed_at_ai(text) or odd_characters(text, ""):
        findings.append(_finding(kind, where, text, how))


def _place(x, y, box):
    """Plain words for a point on a page whose box is (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = box
    if not (x0 - 1 <= x <= x1 + 1 and y0 - 1 <= y <= y1 + 1):
        return f"outside the page (x={x:.0f}, y={y:.0f})"
    row = "top" if y > y0 + 2 * (y1 - y0) / 3 else "bottom" if y < y0 + (y1 - y0) / 3 else "middle"
    column = "left" if x < x0 + (x1 - x0) / 3 else "right" if x > x0 + 2 * (x1 - x0) / 3 else "centre"
    return f"{row} {column} of the page"


# --- PDF --------------------------------------------------------------------

_OBJ = re.compile(rb"(\d+)\s+(\d+)\s+obj\b(.*?)\bendobj", re.S)


def _stream(body):
    m = re.search(rb"stream(?:\r\n|\n|\r)", body)
    if not m:
        return b""
    length = re.search(rb"/Length\s+(\d+)(?!\s+\d+\s+R)", body[:m.start()])  # a direct length is exact; else look for endstream
    stop = m.end() + int(length.group(1)) if length else -1
    if stop < 0 or not body[stop:].lstrip().startswith(b"endstream"):
        stop = body.rfind(b"endstream")
        stop = len(body) if stop < m.end() else stop
    raw = body[m.end():stop]
    if b"FlateDecode" in body[:m.start()]:
        try:
            return zlib.decompress(raw)
        except zlib.error:
            try:
                return zlib.decompressobj().decompress(raw)  # damaged or padded: keep what decodes
            except zlib.error:
                return b""
    return raw


def _objects(data):
    objs = {int(m.group(1)): m.group(3) for m in _OBJ.finditer(data)}
    for body in [b for b in objs.values() if b"/ObjStm" in b]:
        stream, n, first = _stream(body), re.search(rb"/N\s+(\d+)", body), re.search(rb"/First\s+(\d+)", body)
        if not (stream and n and first):
            continue
        numbers, first = stream[:int(first.group(1))].split(), int(first.group(1))
        pairs = [(int(numbers[i]), int(numbers[i + 1])) for i in range(0, min(len(numbers), 2 * int(n.group(1))) - 1, 2)]
        for i, (number, offset) in enumerate(pairs):
            end = pairs[i + 1][1] if i + 1 < len(pairs) else len(stream) - first
            objs[number] = stream[first + offset:first + end]
    return objs


def _ref(body, key):
    m = re.search(rb"/" + key + rb"\s+(\d+)\s+0\s+R", body)
    return int(m.group(1)) if m else None


def _inherited(objs, body, key):
    """A page's value of `key` (MediaBox, CropBox, Resources), taken from its parents when it has none."""
    for _ in range(20):
        m = re.search(rb"/" + key + rb"\s*(\[[^\]]*\]|<<.*?>>\s*(?=/|>>)|\d+\s+0\s+R)", body, re.S)
        if m:
            value = m.group(1)
            ref = re.fullmatch(rb"(\d+)\s+0\s+R", value)
            return objs.get(int(ref.group(1)), b"") if ref else value
        parent = _ref(body, b"Parent")
        if parent is None or parent not in objs:
            return None
        body = objs[parent]
    return None


def _xobjects(objs, resources):
    """The bodies of the objects a page can draw with `Do` (pictures and reusable page parts)."""
    m = re.search(rb"/XObject\s*<<(.*?)>>", resources or b"", re.S)
    return [objs.get(int(n), b"") for n in re.findall(rb"/[^\s/<>\[\]()]+\s+(\d+)\s+0\s+R", m.group(1))] if m else []


def _annotation_numbers(objs, body):
    listed = re.search(rb"/Annots\s*\[(.*?)\]", body, re.S)
    if listed:
        found = listed.group(1)
    else:
        ref = _ref(body, b"Annots")
        found = objs.get(ref, b"") if ref else b""
    return [int(n) for n in re.findall(rb"(\d+)\s+0\s+R", found)]


def _page_order(objs, data):
    pages = {n for n, b in objs.items() if re.search(rb"/Type\s*/Page(?![a-zA-Z])", b)}
    root = re.search(rb"/Root\s+(\d+)\s+0\s+R", data)
    ordered = []

    def walk(number, depth=0):
        body = objs.get(number, b"")
        if depth > 30:
            return
        kids = re.search(rb"/Kids\s*\[(.*?)\]", body, re.S)
        if kids and number not in pages:
            for k in re.findall(rb"(\d+)\s+0\s+R", kids.group(1)):
                walk(int(k), depth + 1)
        elif number in pages:
            ordered.append(number)

    if root and _ref(objs.get(int(root.group(1)), b""), b"Pages"):
        walk(_ref(objs[int(root.group(1))], b"Pages"))
    return ordered if ordered and set(ordered) == pages else sorted(pages)


def _pdf_string(raw):
    """A PDF literal string's bytes, with its escapes undone."""
    out, i = bytearray(), 0
    escapes = {ord("n"): 10, ord("r"): 13, ord("t"): 9, ord("b"): 8, ord("f"): 12}
    while i < len(raw):
        c = raw[i]
        if c == 0x5C and i + 1 < len(raw):
            i += 1
            c = raw[i]
            if 0x30 <= c <= 0x37:
                digits = bytes(raw[i:i + 3])
                m = re.match(rb"[0-7]{1,3}", digits)
                out.append(int(m.group(0), 8) & 255)
                i += len(m.group(0))
                continue
            out.append(escapes.get(c, c))
        else:
            out.append(c)
        i += 1
    return bytes(out)


def _text_of(raw):
    """Human text of a PDF string used outside the page content (metadata, annotations): UTF-16 or Latin-1."""
    if raw[:2] == b"\xfe\xff":
        return raw[2:].decode("utf-16-be", "replace")
    return raw.decode("latin-1")


def _cmap(stream):
    """A ToUnicode map: {code: text} and the code length in bytes."""
    table, width = {}, 1
    for block in re.findall(rb"beginbfchar(.*?)endbfchar", stream, re.S):
        for src, dst in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block):
            width = max(width, len(src) // 2)
            table[int(src, 16)] = bytes.fromhex(dst.decode()).decode("utf-16-be", "replace")
    for block in re.findall(rb"beginbfrange(.*?)endbfrange", stream, re.S):
        for lo, hi, dst in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block):
            width = max(width, len(lo) // 2)
            base = bytes.fromhex(dst.decode()).decode("utf-16-be", "replace")
            for offset in range(min(int(hi, 16) - int(lo, 16), 0xFFFF) + 1):
                table[int(lo, 16) + offset] = base[:-1] + chr(ord(base[-1]) + offset)
    return table, width


def _fonts(objs, resources):
    """{font name: (cmap or None, is_composite)} from a page's Resources."""
    fonts = {}
    if not resources:
        return fonts
    m = re.search(rb"/Font\s*<<(.*?)>>", resources, re.S)
    ref = re.search(rb"/Font\s+(\d+)\s+0\s+R", resources)
    table = m.group(1) if m else objs.get(int(ref.group(1)), b"")[2:-2] if ref else b""
    for name, number in re.findall(rb"/([^\s/<>\[\]()]+)\s+(\d+)\s+0\s+R", table):
        body = objs.get(int(number), b"")
        to_unicode = _ref(body, b"ToUnicode")
        fonts[name.decode("latin-1")] = (_cmap(_stream(objs[to_unicode])) if to_unicode in objs else None,
                                         b"/Type0" in body)
    return fonts


_TOKEN = re.compile(rb"<<|>>|\[|\]|/[^\s/<>\[\]()]*|<[0-9A-Fa-f\s]*>|[-+]?\d*\.?\d+|[A-Za-z'\"*]+")


def _tokens(stream):
    stream = re.sub(rb"\bBI\b.*?\bEI\b", b" ", stream, flags=re.S)  # inline images are binary
    i = 0
    while i < len(stream):
        c = stream[i:i + 1]
        if c == b"(":
            depth, j = 1, i + 1
            while j < len(stream) and depth:
                if stream[j] == 0x5C:
                    j += 1
                elif stream[j] == 0x28:
                    depth += 1
                elif stream[j] == 0x29:
                    depth -= 1
                j += 1
            yield ("s", _pdf_string(stream[i + 1:j - 1]))
            i = j
        elif c == b"%":
            i = stream.find(b"\n", i) + 1 or len(stream)
        else:
            m = _TOKEN.match(stream, i)
            if not m:
                i += 1
                continue
            tok = m.group(0)
            i = m.end()
            yield (("h", bytes.fromhex(re.sub(rb"\s", b"", tok[1:-1]).decode() + ("0" if len(re.sub(rb"\s", b"", tok[1:-1])) % 2 else "")))
                   if tok[:1] == b"<" and tok[:2] != b"<<" else ("t", tok))


def _mul(m, n):
    a, b, c, d, e, f = m
    p, q, r, s, t, u = n
    return (a * p + b * r, a * q + b * s, c * p + d * r, c * q + d * s, e * p + f * r + t, e * q + f * s + u)


def _colour(values):
    if len(values) == 1:
        return (values[0],) * 3
    if len(values) == 3:
        return tuple(values)
    if len(values) == 4:
        c, m, y, k = values
        return tuple((1 - v) * (1 - k) for v in (c, m, y))
    return None


def _decode(raw, font, fonts, notes):
    cmap, composite = fonts.get(font, (None, False))
    if cmap:
        table, width = cmap
        return "".join(table.get(int.from_bytes(raw[i:i + width], "big"), "") for i in range(0, len(raw), width))
    if composite:
        notes.add(f"text in the font {font} has no ToUnicode map, so it could not be read")
        return ""
    return raw.decode("latin-1")


def _page_segments(stream, fonts, notes):
    """Every piece of text drawn on a page, in order, with where, how big and in what colour."""
    ctm, stack, fill, mode, font, size, leading = (1, 0, 0, 1, 0, 0), [], (0, 0, 0), 0, None, 0, 0
    tm = tlm = (1, 0, 0, 1, 0, 0)
    dark, segments, operands, array = [], [], [], None

    def show(raw):
        text = _decode(raw, font, fonts, notes)
        if not text:
            return
        x = tlm[4] * ctm[0] + tlm[5] * ctm[2] + ctm[4]  # where the line starts: glyph widths are not read
        y = tlm[4] * ctm[1] + tlm[5] * ctm[3] + ctm[5]
        scale = math.hypot(tm[2], tm[3]) * math.hypot(ctm[2], ctm[3])
        segments.append({"text": text, "x": x, "y": y, "size": size * scale, "fill": fill, "mode": mode})

    for kind, tok in _tokens(stream):
        if kind in ("s", "h"):
            if array is not None:
                array.append(tok)
            else:
                operands.append(tok)
            continue
        if tok == b"[":
            array = []
            continue
        if tok == b"]":
            operands.append(array)
            array = None
            continue
        if re.fullmatch(rb"[-+]?\d*\.?\d+", tok):
            (array if array is not None else operands).append(float(tok))
            continue
        if tok[:1] == b"/" or tok in (b"<<", b">>"):
            operands.append(tok[1:].decode("latin-1") if tok[:1] == b"/" else None)
            continue
        nums = [o for o in operands if isinstance(o, float)]
        if tok == b"q":
            stack.append((ctm, fill, mode, font, size, leading))
        elif tok == b"Q" and stack:
            ctm, fill, mode, font, size, leading = stack.pop()
        elif tok == b"cm" and len(nums) >= 6:
            ctm = _mul(tuple(nums[-6:]), ctm)
        elif tok in (b"rg", b"g", b"k", b"sc", b"scn") and _colour(nums):
            fill = _colour(nums)
        elif tok == b"BT":
            tm = tlm = (1, 0, 0, 1, 0, 0)
        elif tok == b"Tf" and nums:
            font = next((o for o in operands if isinstance(o, str)), font)
            size = nums[-1]
        elif tok == b"Tr" and nums:
            mode = int(nums[-1])
        elif tok == b"TL" and nums:
            leading = nums[-1]
        elif tok in (b"Td", b"TD") and len(nums) >= 2:
            if tok == b"TD":
                leading = -nums[-1]
            tlm = tm = _mul((1, 0, 0, 1, nums[-2], nums[-1]), tlm)
        elif tok == b"Tm" and len(nums) >= 6:
            tlm = tm = tuple(nums[-6:])
        elif tok in (b"T*", b"'", b'"'):
            tlm = tm = _mul((1, 0, 0, 1, 0, -leading), tlm)
        if tok in (b"Tj", b"'", b'"') and operands and isinstance(operands[-1], bytes):
            show(operands[-1])
        elif tok == b"TJ" and operands and isinstance(operands[-1], list):
            for part in operands[-1]:
                if isinstance(part, bytes):
                    show(part)
        elif tok == b"re" and len(nums) >= 4:
            x, y, w, h = nums[-4:]
            p, q = ctm[0] * x + ctm[2] * y + ctm[4], ctm[1] * x + ctm[3] * y + ctm[5]
            r, s = ctm[0] * (x + w) + ctm[2] * (y + h) + ctm[4], ctm[1] * (x + w) + ctm[3] * (y + h) + ctm[5]
            dark.append((min(p, r), min(q, s), max(p, r), max(q, s), fill))
        operands = []
    return segments, [r for r in dark if sum(r[4]) < 2.4]


def _locate(segments, sentence, box):
    """Where the on-show text segment holding the start of `sentence` is drawn, in words."""
    head = sentence[:20]
    spot = next((s for s in segments if head in " ".join(s[0].split())), None)
    return _place(spot[1], spot[2], box) if spot else None


def _hidden_why(seg, dark_rects, box):
    why = []
    if seg["mode"] in (3, 7):
        why.append("invisible (render mode %d)" % seg["mode"])
    if min(seg["fill"]) >= 0.95 and not any(r[0] <= seg["x"] <= r[2] and r[1] <= seg["y"] <= r[3] for r in dark_rects):
        why.append("white text")
    if 0 < seg["size"] < TINY_PT:
        why.append(f"tiny text, {seg['size']:.1f} pt")
    if not (box[0] - 1 <= seg["x"] <= box[2] + 1 and box[1] - 1 <= seg["y"] <= box[3] + 1):
        why.append("text outside the page")
    return why


def _scan_pdf(path):
    data = Path(path).read_bytes()
    notes, findings = set(), []
    if re.search(rb"/Encrypt(?![A-Za-z])", data):
        return [], ["the PDF is encrypted: its content was not read"]
    objs = _objects(data)
    order = _page_order(objs, data)
    if not order:
        return [], ["no pages could be read from the PDF"]
    annots, read_any = {}, False
    for number, page in enumerate(order, 1):
        body = objs[page]
        box_raw = _inherited(objs, body, b"CropBox") or _inherited(objs, body, b"MediaBox") or b"[0 0 612 792]"
        numbers = [float(v) for v in re.findall(rb"[-+]?\d*\.?\d+", box_raw)]
        box = tuple(numbers[:4]) if len(numbers) >= 4 else (0, 0, 612, 792)
        listed = re.search(rb"/Contents\s*\[(.*?)\]", body, re.S)
        refs = [int(n) for n in re.findall(rb"(\d+)\s+0\s+R", listed.group(1))] if listed else [_ref(body, b"Contents")]
        stream = b"\n".join(_stream(objs.get(r, b"")) for r in refs)
        resources = _inherited(objs, body, b"Resources")
        xobjects = [re.sub(rb"\s", b"", x) for x in _xobjects(objs, resources)]
        if any(b"/Subtype/Form" in x for x in xobjects):
            notes.add("a page draws reusable page parts (form XObjects): text inside them was not scanned")
        has_image = any(b"/Subtype/Image" in x for x in xobjects)
        segments, dark = _page_segments(stream, _fonts(objs, resources), notes)
        read_any = read_any or bool(segments)
        visible, shown, groups = "", [], []
        for seg in segments:
            why = _hidden_why(seg, dark, box)
            if why and groups and groups[-1]["why"] == why and abs(groups[-1]["y"] - seg["y"]) < 40:
                groups[-1]["text"] += seg["text"]
            elif why:
                groups.append({"why": why, "text": seg["text"], "x": seg["x"], "y": seg["y"]})
            else:
                shown.append((seg["text"], seg["x"], seg["y"]))
                visible += seg["text"] + " "
        for g in groups:
            text = " ".join(g["text"].split())
            if not text:
                continue
            if g["why"] == ["invisible (render mode 3)"] and has_image and not aimed_at_ai(text) and not odd_characters(text, ""):
                notes.add(f"page {number} has invisible text over a picture (usually a scan's text layer): not reported")
                continue
            findings.append(_finding("hidden-text", f"page {number}", text, "hidden text: " + ", ".join(g["why"]),
                                     _place(g["x"], g["y"], box)))
        findings += text_findings(visible, f"page {number}", lambda sentence: _locate(shown, sentence, box))
        annots.update({n: number for n in _annotation_numbers(objs, body)})
    # text kept outside the pages: annotations and form fields, document information and XMP metadata
    for number, body in objs.items():
        if re.search(rb"/Subtype\s*/(?:Text|FreeText|Popup|Stamp|Widget|Highlight|Link)\b", body) or number in annots:
            for key in (rb"Contents", rb"TU", rb"V", rb"RC"):
                for m in re.finditer(rb"/" + key + rb"\s*\(((?:\\.|[^\\)])*)\)", body):
                    where = f"page {annots[number]}" if number in annots else "a form field or annotation"
                    _flag(findings, "annotation", where, _text_of(_pdf_string(m.group(1))), "text in a PDF annotation or form field")
        if b"/Title" in body and re.search(rb"/(?:Title|Subject|Keywords|Author|Creator|Producer)\s*\(", body):
            for m in re.finditer(rb"/(Title|Subject|Keywords|Author|Creator)\s*\(((?:\\.|[^\\)])*)\)", body):
                _flag(findings, "metadata", "the document's properties", _text_of(_pdf_string(m.group(2))),
                      f"text in the PDF's {m.group(1).decode().lower()} field")
        if b"<x:xmpmeta" in _stream(body) or b"<x:xmpmeta" in body:
            xmp = (_stream(body) or body).decode("utf-8", "replace")
            for text in re.findall(r">([^<>]{12,})<", xmp):
                _flag(findings, "metadata", "the document's properties", text, "text in the PDF's metadata")
    if not read_any:
        notes.add("no text could be read from this PDF (a scan, a picture, or content this reader does not handle): "
                  "this is not a clean result")
    notes.add("text hidden under pictures or shapes, camouflaged colours and text drawn as pictures are not detected by this scan")
    return findings, sorted(notes)


# --- Office files -----------------------------------------------------------

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
A = "{http://schemas.openxmlformats.org/drawingml/2006/main}"


def _near_white(value):
    value = (value or "").lstrip("#")
    return len(value) == 6 and all(int(value[i:i + 2], 16) >= 0xF0 for i in (0, 2, 4)) if re.fullmatch(r"[0-9A-Fa-f]{6}", value) else False


def _parse(zf, name):
    try:
        return ET.fromstring(zf.read(name))
    except (KeyError, ET.ParseError):
        return None


def _scan_docx(path):
    findings, notes = [], set()
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        parts = [n for n in names if re.fullmatch(r"word/(document|header\d*|footer\d*|footnotes|endnotes)\.xml", n)]
        for part in parts:
            root = _parse(zf, part)
            if root is None:
                notes.add(f"{part} could not be parsed")
                continue
            label = {"document": ""}.get(Path(part).stem, Path(part).stem + " of the document")
            page, visible_all = 1, []
            for number, para in enumerate(root.iter(W + "p"), 1):
                page += sum(1 for _ in para.iter(W + "lastRenderedPageBreak")) + sum(
                    1 for br in para.iter(W + "br") if br.get(W + "type") == "page")
                where = (label + ", " if label else "") + f"paragraph {number}" + (f" (about page {page})" if page > 1 else "")
                visible, hidden = "", []
                for run in para.iter(W + "r"):
                    props = run.find(W + "rPr")
                    text = "".join(t.text or "" for t in run.iter(W + "t"))
                    if not text:
                        continue
                    why = []
                    if props is not None:
                        if any(props.find(W + tag) is not None for tag in ("vanish", "specVanish", "webHidden")):
                            why.append("Word's hidden formatting")
                        colour = props.find(W + "color")
                        if colour is not None and (_near_white(colour.get(W + "val")) or colour.get(W + "themeColor") == "background1"):
                            why.append("white text")
                        size = props.find(W + "sz")
                        if size is not None and size.get(W + "val", "99").isdigit() and int(size.get(W + "val")) < TINY_PT * 2:
                            why.append(f"tiny text, {int(size.get(W + 'val')) / 2:g} pt")
                    if why:
                        hidden.append((why, text))
                    else:
                        visible += text
                before = visible[-40:].strip()
                grouped = []
                for why, text in hidden:
                    if grouped and grouped[-1][0] == why:
                        grouped[-1][1] += text
                    else:
                        grouped.append([why, text])
                for why, text in grouped:
                    findings.append(_finding("hidden-text", where, text, "hidden text: " + ", ".join(why),
                                             f'after the visible words "{before}"' if before else None))
                visible_all.append(visible)
                deleted = " ".join("".join(t.text or "" for t in d.iter(W + "delText")) for d in para.iter(W + "del"))
                _flag(findings, "tracked-deletion", where, deleted, "deleted text still stored in the file")
            findings += text_findings("\n".join(visible_all), label or "the document")
        comments = _parse(zf, "word/comments.xml")
        for c in (comments.iter(W + "comment") if comments is not None else []):
            _flag(findings, "comment", "a comment", " ".join(t.text or "" for t in c.iter(W + "t")), "text in a Word comment")
        for part in [n for n in names if re.fullmatch(r"word/(document|header\d*|footer\d*)\.xml", n)]:
            root = _parse(zf, part)
            for el in (root.iter() if root is not None else []):
                if el.tag.endswith(("}docPr", "}cNvPr")):
                    for key in ("descr", "title"):
                        _flag(findings, "alt-text", "a picture's description", el.get(key) or "", "text in a picture's alt text")
        for name in names:
            if name.startswith("customXml/") and name.endswith(".xml"):
                text = " ".join(re.findall(r">([^<>]{12,})<", zf.read(name).decode("utf-8", "replace")))
                _flag(findings, "custom-xml", "the file's custom data", text, "text in the file's custom data parts")
    notes.add("text hidden under pictures or shapes and camouflaged colours are not detected by this scan")
    return findings, sorted(notes)


def _scan_pptx(path):
    findings, notes = [], set()
    with zipfile.ZipFile(path) as zf:
        presentation = _parse(zf, "ppt/presentation.xml")
        sld = presentation.find(".//{http://schemas.openxmlformats.org/presentationml/2006/main}sldSz") if presentation is not None else None
        width, height = (int(sld.get("cx")), int(sld.get("cy"))) if sld is not None else (9144000, 6858000)
        for name in sorted(n for n in zf.namelist() if re.fullmatch(r"ppt/(slides/slide|notesSlides/notesSlide)\d+\.xml", n)):
            root = _parse(zf, name)
            if root is None:
                notes.add(f"{name} could not be parsed")
                continue
            number = re.search(r"(\d+)\.xml$", name).group(1)
            where = ("slide " if "/slides/" in name else "the notes of slide ") + number
            if root.get("show") == "0":
                findings.append(_finding("hidden-slide", where, "", "a slide that is hidden in the slideshow"))
            shown = []
            for shape in root.iter():
                if not shape.tag.endswith("}sp"):
                    continue
                off = next(shape.iter(A + "off"), None)
                outside = off is not None and not (0 <= int(off.get("x", 0)) <= width and 0 <= int(off.get("y", 0)) <= height)
                for run in shape.iter(A + "r"):
                    text = "".join(t.text or "" for t in run.iter(A + "t"))
                    props, why = run.find(A + "rPr"), []
                    if props is not None:
                        if props.get("sz", "9999").isdigit() and int(props.get("sz")) < TINY_PT * 100:
                            why.append(f"tiny text, {int(props.get('sz')) / 100:g} pt")
                        colour = props.find(f"{A}solidFill/{A}srgbClr")
                        if colour is not None and _near_white(colour.get("val")):
                            why.append("white text")
                    if outside:
                        why.append("text outside the slide")
                    if text.strip() and (why or "notesSlide" in name and aimed_at_ai(text)):
                        findings.append(_finding("hidden-text", where, text, "hidden text: " + (", ".join(why) or "in the speaker notes")))
                    else:
                        shown.append(text)
            findings += odd_characters("\n".join(t.text or "" for t in root.iter(A + "t")), where)
            findings += [f for f in text_findings("\n".join(shown), where) if f["kind"] == "instruction-to-ai"]
    notes.add("text hidden under pictures or shapes and camouflaged colours are not detected by this scan")
    return findings, sorted(notes)


def _scan_xlsx(path):
    findings = []
    with zipfile.ZipFile(path) as zf:
        book = _parse(zf, "xl/workbook.xml")
        for sheet in (book.iter() if book is not None else []):
            if sheet.tag.endswith("}sheet") and sheet.get("state") in ("hidden", "veryHidden"):
                findings.append(_finding("hidden-sheet", f"the sheet {sheet.get('name')}", "", "a sheet that is hidden in the workbook"))
        shared = _parse(zf, "xl/sharedStrings.xml")
        text = "\n".join("".join(t.text or "" for t in si.iter() if t.tag.endswith("}t")) for si in (shared if shared is not None else []))
        findings += text_findings(text, "the workbook's cells")
    return findings, ["cell colours, hidden rows and columns were not checked"]


def _scan_text(path):
    text = Path(path).read_text("utf-8", errors="replace")
    findings = [f for i, line in enumerate(text.splitlines(), 1) for f in text_findings(line, f"line {i}")]
    if path.suffix.lower() in (".html", ".htm"):
        for i, line in enumerate(text.splitlines(), 1):
            if HTML_HIDDEN.search(line):
                findings.append(_finding("hidden-text", f"line {i}", re.sub(r"<[^>]+>", " ", line), "text in a hidden HTML element"))
    return findings, []


def scan_file(path):
    """The Trap scan of one file: {"path", "findings", "could_not_check"}."""
    path = Path(path)
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            findings, notes = _scan_pdf(path)
        elif suffix in (".docx", ".docm"):
            findings, notes = _scan_docx(path)
        elif suffix in (".pptx", ".pptm"):
            findings, notes = _scan_pptx(path)
        elif suffix in (".xlsx", ".xlsm"):
            findings, notes = _scan_xlsx(path)
        elif suffix in (".txt", ".md", ".html", ".htm", ".csv", ".tex"):
            findings, notes = _scan_text(path)
        elif suffix in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".tif", ".tiff"):
            findings, notes = [], ["a picture: read it with the visual-read worker (source-reader) and treat any text in it as data"]
        else:
            findings, notes = [], [f"a {suffix or 'file'} of a type the scan does not read"]
    except (OSError, zipfile.BadZipFile, ValueError, KeyError, IndexError, RecursionError, MemoryError) as error:
        findings, notes = [], [f"could not be read ({type(error).__name__}): this is not a clean result"]
    return {"path": str(path), "findings": findings, "could_not_check": notes}

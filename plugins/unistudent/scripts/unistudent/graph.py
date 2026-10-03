"""Graphs: a small JSON Graph spec in, a PNG out (ADR 0006).

The spec names the axes, the curves, the shifts and the points; style follows content:
no formula → smooth curves and straight lines with no numbers on the axes, any formula →
numbered axes. Only parsing, geometry and Hebrew ordering live here; matplotlib
(optional) does the drawing.
"""
import hashlib
import json
import math
import os
import re
import struct
import unicodedata
from pathlib import Path

from .common import UserError

RENDERER = "4"  # bump when drawing changes, so stored pictures are redrawn
HASH_KEY = "unistudent-graph"
PALETTE = ["#1f77b4", "#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#8c564b"]
FUNCTIONS = {"sqrt": math.sqrt, "log": math.log, "exp": math.exp, "sin": math.sin, "cos": math.cos}
FORMULA_HELP = "Use x, numbers, + - * / ^ and the functions sqrt, log, exp, sin, cos."
KINDS = ("points", "vertical", "horizontal", "formula", "sketch")


# --- formulas ---------------------------------------------------------------

_TOKEN = re.compile(r"\s*(?:(\d+\.?\d*|\.\d+)|([A-Za-z_]\w*)|(\*\*|[-+*/^(),]))")


def _tokens(text):
    out, pos = [], 0
    text = text.strip()
    while pos < len(text):
        match = _TOKEN.match(text, pos)
        if not match:
            raise UserError(f'The formula "{text}" has a character I can\'t read. {FORMULA_HELP}')
        number, name, op = match.groups()
        out.append(("num", float(number)) if number else ("name", name) if name else ("op", op))
        pos = match.end()
    return out


def parse_formula(text):
    """Compile a formula in x to a function. A restricted parser: never `eval`."""
    tokens = _tokens(text)
    pos = [0]

    def peek():
        return tokens[pos[0]] if pos[0] < len(tokens) else (None, None)

    def take():
        pos[0] += 1
        return tokens[pos[0] - 1]

    def fail(why):
        raise UserError(f'The formula "{text}" {why}. {FORMULA_HELP}')

    def expr():
        left = term()
        while peek() in (("op", "+"), ("op", "-")):
            sign, right = take()[1], term()
            left = (lambda a, b, s: lambda x: a(x) + b(x) if s == "+" else a(x) - b(x))(left, right, sign)
        return left

    def term():
        left = unary()
        while True:
            kind, value = peek()
            if (kind, value) in (("op", "*"), ("op", "/")):
                take()
                right = unary()
                left = (lambda a, b, s: lambda x: a(x) * b(x) if s == "*" else a(x) / b(x))(left, right, value)
            elif kind == "name" or (kind, value) == ("op", "("):  # 2x, 3(x+1)
                right = unary()
                left = (lambda a, b: lambda x: a(x) * b(x))(left, right)
            else:
                return left

    def unary():
        if peek() in (("op", "-"), ("op", "+")):
            sign = take()[1]
            inner = unary()
            return (lambda x: -inner(x)) if sign == "-" else inner
        return power()

    def power():
        base = atom()
        if peek() in (("op", "^"), ("op", "**")):
            take()
            exponent = unary()
            return lambda x: base(x) ** exponent(x)
        return base

    def atom():
        kind, value = take() if pos[0] < len(tokens) else (None, None)
        if kind == "num":
            return lambda x: value
        if kind == "name" and value == "x":
            return lambda x: x
        if kind == "name" and value in ("pi", "e"):
            constant = math.pi if value == "pi" else math.e
            return lambda x: constant
        if kind == "name" and value in FUNCTIONS:
            if take() != ("op", "("):
                fail(f"needs brackets after {value}")
            inner = expr()
            if take() != ("op", ")"):
                fail("is missing a closing bracket")
            function = FUNCTIONS[value]
            return lambda x: function(inner(x))
        if kind == "name":
            fail(f"uses '{value}', which isn't allowed")
        if (kind, value) == ("op", "("):
            inner = expr()
            if take() != ("op", ")"):
                fail("is missing a closing bracket")
            return inner
        fail("is incomplete")

    function = expr()
    if pos[0] != len(tokens):
        fail(f"has something unexpected at '{tokens[pos[0]][1]}'")

    def safe(x):
        try:
            value = function(x)
            return value if isinstance(value, float) and math.isfinite(value) else (
                float(value) if isinstance(value, (int, float)) and math.isfinite(value) else math.nan)
        except (ValueError, ZeroDivisionError, OverflowError, TypeError):
            return math.nan
    return safe


# --- spec -------------------------------------------------------------------

def _number(value, what):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise UserError(f"{what} must be a number.")
    return float(value)


def _pairs(value, what, count=None):
    ok = isinstance(value, list) and all(isinstance(p, list) and len(p) == 2 for p in value)
    if not ok or (count is not None and len(value) != count) or (count is None and len(value) < 2):
        raise UserError(f"{what} must be a list of [x, y] pairs ({count or 'at least 2'}).")
    return [(_number(a, what), _number(b, what)) for a, b in value]


def load_spec(path):
    try:
        raw = json.loads(Path(path).read_text("utf-8"))
    except (OSError, ValueError) as error:
        raise UserError(f"Can't read the Graph spec {path}: {error}")
    if not isinstance(raw, dict) or not isinstance(raw.get("curves"), list) or not raw["curves"]:
        raise UserError('The Graph spec needs a "curves" list with at least one curve.')
    curves, names = [], set()
    for item in raw["curves"]:
        name = item.get("name") if isinstance(item, dict) else None
        if not isinstance(name, str) or not name.strip():
            raise UserError("Every curve needs a name.")
        if name in names:
            raise UserError(f'Two curves are named "{name}".')
        names.add(name)
        kinds = [k for k in KINDS if k in item]
        if len(kinds) != 1:
            raise UserError(f'Curve "{name}" needs exactly one of: {", ".join(KINDS)}.')
        kind = kinds[0]
        curve = {"name": name, "kind": kind, "shift_of": item.get("shift_of")}
        if kind == "points":
            curve["data"] = _pairs(item["points"], f'"{name}" points', 2)
        elif kind == "sketch":
            curve["data"] = _pairs(item["sketch"], f'"{name}" sketch')
        elif kind == "formula":
            if not isinstance(item["formula"], str):
                raise UserError(f'"{name}" formula must be text.')
            curve["data"] = parse_formula(item["formula"])
            curve["range"] = tuple(_pairs([item["range"]], f'"{name}" range', 1)[0]) if "range" in item else None
        else:
            curve["data"] = _number(item[kind], f'"{name}" {kind}')
        curves.append(curve)
    for curve in curves:
        target = curve["shift_of"]
        if target is not None and not isinstance(target, str):
            raise UserError(f'"shift_of" on curve "{curve["name"]}" must be the name of another curve.')
        if target is not None and (target not in names or target == curve["name"]):
            raise UserError(f'Curve "{curve["name"]}" is a shift of "{target}", which is not another curve in the spec.')
    points = []
    for item in raw.get("points") or []:
        at = item.get("at") if isinstance(item, dict) else None
        if not (isinstance(at, list) and len(at) == 2):
            raise UserError("Every point needs a label and an \"at\": two curve names or two numbers.")
        if all(isinstance(a, str) for a in at):
            for a in at:
                if a not in names:
                    raise UserError(f'Point "{item.get("label", "")}" refers to "{a}", which is not a curve in the spec.')
        else:
            at = [_number(a, "A point's coordinates") for a in at]
        points.append({"label": str(item.get("label", "")), "at": at})
    view = raw.get("view") or {}
    if not isinstance(view, dict):
        raise UserError('"view" must look like {"x": [low, high], "y": [low, high]}.')
    return {"x": str(raw.get("x", "")), "y": str(raw.get("y", "")), "curves": curves, "points": points,
            "view": {k: tuple(_pairs([view[k]], f"view {k}", 1)[0]) for k in ("x", "y") if k in view}}


# --- geometry ---------------------------------------------------------------

def _smooth(points, per_segment=24):
    """Catmull-Rom curve through the points."""
    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for k in range(per_segment):
            t = k / per_segment
            out.append(tuple(0.5 * (2 * p1[d] + (p2[d] - p0[d]) * t + (2 * p0[d] - 5 * p1[d] + 4 * p2[d] - p3[d]) * t * t
                                    + (3 * p1[d] - p0[d] - 3 * p2[d] + p3[d]) * t ** 3) for d in (0, 1)))
    out.append(tuple(points[-1]))
    return out


def _sample(function, lo, hi, count=200):
    return [(lo + (hi - lo) * i / (count - 1), function(lo + (hi - lo) * i / (count - 1))) for i in range(count)]


def _segment_cross(a, b, c, d):
    r, s = (b[0] - a[0], b[1] - a[1]), (d[0] - c[0], d[1] - c[1])
    denom = r[0] * s[1] - r[1] * s[0]
    if denom == 0:
        return None
    t = ((c[0] - a[0]) * s[1] - (c[1] - a[1]) * s[0]) / denom
    u = ((c[0] - a[0]) * r[1] - (c[1] - a[1]) * r[0]) / denom
    return (a[0] + t * r[0], a[1] + t * r[1]) if 0 <= t <= 1 and 0 <= u <= 1 else None


def intersection(first, second):
    for a, b in zip(first, first[1:]):
        for c, d in zip(second, second[1:]):
            if any(math.isnan(v) for v in (*a, *b, *c, *d)):
                continue
            found = _segment_cross(a, b, c, d)
            if found:
                return found
    return None


def layout(spec):
    """Resolve every curve to a polyline and fix the view. Returns (lines, view, sketch_only)."""
    curves = spec["curves"]
    sketch_only = not any(c["kind"] == "formula" for c in curves)
    xs = []
    for c in curves:
        if c["kind"] in ("points", "sketch"):
            xs.append((min(p[0] for p in c["data"]), max(p[0] for p in c["data"])))
        elif c["kind"] == "formula" and c["range"]:
            xs.append(c["range"])
        elif c["kind"] == "vertical":
            xs.append((c["data"], c["data"]))
    if sketch_only or not xs or any(c["kind"] == "formula" and not c["range"] for c in curves):
        xs.append((0.0, 10.0))
    xlo, xhi = spec["view"].get("x") or (min(a for a, _ in xs), max(b for _, b in xs))
    if sketch_only:
        xlo, xhi = 0.0, 10.0
    if xhi - xlo < 1e-9:
        xlo, xhi = xlo - 1, xhi + 1
    lines = {}
    for c in curves:
        kind, data = c["kind"], c["data"]
        if kind == "sketch":
            lines[c["name"]] = _smooth(data)
        elif kind == "points":
            (x1, y1), (x2, y2) = data
            if x1 == x2:
                lines[c["name"]] = [(x1, y1), (x2, y2)]
            else:
                slope = (y2 - y1) / (x2 - x1)
                lines[c["name"]] = [(xlo, y1 + slope * (xlo - x1)), (xhi, y1 + slope * (xhi - x1))]
        elif kind == "formula":
            lo, hi = c["range"] or (xlo, xhi)
            lines[c["name"]] = _sample(data, lo, hi)
    ys = [p[1] for line in lines.values() for p in line if math.isfinite(p[1])]
    ys += [c["data"] for c in curves if c["kind"] == "horizontal"]
    if "y" in spec["view"]:
        ylo, yhi = spec["view"]["y"]
    elif sketch_only:
        ylo, yhi = 0.0, 10.0
    elif ys:
        ylo, yhi = min(ys), max(ys)
        if yhi - ylo < 1e-9:
            ylo, yhi = ylo - 1, yhi + 1
        pad = 0.08 * (yhi - ylo)
        ylo, yhi = ylo - pad, yhi + pad
    else:
        ylo, yhi = 0.0, 10.0
    for c in curves:
        if c["kind"] == "horizontal":
            lines[c["name"]] = [(xlo, c["data"]), (xhi, c["data"])]
        elif c["kind"] == "vertical":
            lines[c["name"]] = [(c["data"], ylo), (c["data"], yhi)]
    if "y" in spec["view"]:  # a fixed view hides what is outside it
        for name, line in lines.items():
            lines[name] = [(x, y if ylo <= y <= yhi else math.nan) for x, y in line]
    return lines, ((xlo, xhi), (ylo, yhi)), sketch_only


def point_positions(spec, lines):
    out = []
    for p in spec["points"]:
        if isinstance(p["at"][0], str):
            found = intersection(lines[p["at"][0]], lines[p["at"][1]])
            if not found:
                raise UserError(f'The curves "{p["at"][0]}" and "{p["at"][1]}" do not cross, '
                                f'so point "{p["label"]}" has no place.')
            out.append((p["label"], found))
        else:
            out.append((p["label"], tuple(p["at"])))
    return out


def shift_arrow(original, moved):
    """From the middle of the original curve to the nearest point on the moved one."""
    ok = [p for p in original if all(math.isfinite(v) for v in p)]
    others = [p for p in moved if all(math.isfinite(v) for v in p)]
    if not ok or not others:
        return None
    start = ok[len(ok) // 2]
    end = min(others, key=lambda p: (p[0] - start[0]) ** 2 + (p[1] - start[1]) ** 2)
    return start, end


# --- Hebrew -----------------------------------------------------------------

def _kind(ch):
    bidi = unicodedata.bidirectional(ch)
    return "R" if bidi in ("R", "AL") else "L" if bidi in ("L", "EN", "AN") else "N"


def _native_bidi():
    """Whether matplotlib orders right-to-left text itself (3.11+, through libraqm)."""
    try:
        from matplotlib import ft2font
    except ImportError:
        return False
    return bool(getattr(ft2font, "__libraqm_version__", ""))


def visual(text):
    """Reorder a label for drawing without a bidi engine: Hebrew runs right-to-left, English symbols
    and numbers inside them kept in reading order."""
    if not any(_kind(ch) == "R" for ch in text):
        return text
    if _native_bidi():
        strong = [_kind(ch) for ch in text if _kind(ch) != "N"]
        # "Y*" inside Hebrew: an invisible left-to-right mark keeps the trailing symbol after the Y
        return text + "\u200e" if strong and strong[-1] == "L" and _kind(text[-1]) == "N" else text
    runs = []  # [kind, chars]
    for ch in text:
        k = _kind(ch)
        if runs and runs[-1][0] == k:
            runs[-1][1] += ch
        else:
            runs.append([k, ch])
    for i, (k, chars) in enumerate(runs):  # neutrals between like runs join them; others follow the base (R)
        if k == "N":
            before = runs[i - 1][0] if i else "R"
            after = runs[i + 1][0] if i + 1 < len(runs) else "R"
            runs[i][0] = before if before == after else "R"
    merged = []
    for k, chars in runs:
        if merged and merged[-1][0] == k:
            merged[-1][1] += chars
        else:
            merged.append([k, chars])
    mirror = str.maketrans("()[]<>", ")(][><")
    return "".join(chars[::-1].translate(mirror) if k == "R" else chars for k, chars in reversed(merged))


# --- drawing ----------------------------------------------------------------

def _matplotlib():
    if os.environ.get("UNISTUDENT_NO_MATPLOTLIB"):
        return None
    try:
        from matplotlib.figure import Figure
    except ImportError:
        return None
    return Figure


def spec_hash(spec_path):
    data = json.dumps(json.loads(Path(spec_path).read_text("utf-8")), sort_keys=True, ensure_ascii=False)
    return hashlib.sha256((RENDERER + data).encode("utf-8")).hexdigest()


def stored_hash(png):
    """The spec hash saved inside a PNG, or None."""
    try:
        data = Path(png).read_bytes()
    except OSError:
        return None
    pos = 8
    while pos + 8 <= len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        if kind == b"tEXt":
            key, _, value = data[pos + 8:pos + 8 + length].partition(b"\0")
            if key == HASH_KEY.encode():
                return value.decode("latin-1")
        pos += 12 + length
    return None


def _overlap(a, b):
    width = min(a.x1, b.x1) - max(a.x0, b.x0)
    height = min(a.y1, b.y1) - max(a.y0, b.y0)
    return width * height if width > 0 and height > 0 else 0


def _avoid_overlaps(fig, labels, obstacles):
    """Move each label to the first nearby spot where it overlaps no other label and stays inside the
    picture; if none exists, shrink every label a little and try again."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    renderer = FigureCanvasAgg(fig).get_renderer()
    for size in (11, 10, 9, 8):
        placed, worst = [], 0
        for text, options in labels:
            text.set_fontsize(size)
            best = None
            for dx, dy, ha, va in options:
                text.xyann, _ = (dx, dy), text.set_ha(ha)
                text.set_va(va)
                box = text.get_window_extent(renderer)
                cost = sum(_overlap(box, other) for other in placed)
                cost += 40 * sum(1 for x, y in obstacles if box.x0 <= x <= box.x1 and box.y0 <= y <= box.y1)
                inside = fig.bbox.x0 <= box.x0 and box.x1 <= fig.bbox.x1 and fig.bbox.y0 <= box.y0 and box.y1 <= fig.bbox.y1
                cost += 0 if inside else 1e6
                if best is None or cost < best[0]:
                    best = (cost, dx, dy, ha, va, box)
                if cost == 0:
                    break
            text.xyann, _ = (best[1], best[2]), text.set_ha(best[3])
            text.set_va(best[4])
            placed.append(best[5])
            worst = max(worst, best[0])
        if worst == 0:
            return


def draw(spec_path, force=False):
    """Draw the spec to a PNG beside it. Returns {png, drawn}."""
    spec_path = Path(spec_path)
    spec = load_spec(spec_path)
    lines, ((xlo, xhi), (ylo, yhi)), sketch_only = layout(spec)
    points = point_positions(spec, lines)
    png = spec_path.with_suffix(".png")
    digest = spec_hash(spec_path)
    if not force and stored_hash(png) == digest:
        return {"png": str(png), "drawn": False}
    Figure = _matplotlib()  # the dispatcher (draw.py) has already made sure matplotlib is importable

    fig = Figure(figsize=(5.2, 4.0), dpi=150)
    ax = fig.subplots()
    fig.subplots_adjust(left=0.1, right=0.93, bottom=0.14, top=0.9)
    xpad, ypad = 0.1 * (xhi - xlo), 0.04 * (yhi - ylo)
    ax.set_xlim(xlo, xhi + xpad)
    ax.set_ylim(ylo, yhi + ypad)
    colours, labels = {}, []
    for c in spec["curves"]:
        if not c["shift_of"]:
            colours[c["name"]] = PALETTE[len(colours) % len(PALETTE)]
    for c in spec["curves"]:
        if c["shift_of"]:
            colours[c["name"]] = colours.get(c["shift_of"]) or PALETTE[len(colours) % len(PALETTE)]
    for c in spec["curves"]:
        line = lines[c["name"]]
        shown = line
        xs_, ys_ = [p[0] for p in shown], [p[1] for p in shown]
        dashed = bool(c["shift_of"]) is False and any(o["shift_of"] == c["name"] for o in spec["curves"])
        ax.plot(xs_, ys_, color=colours[c["name"]], linewidth=2.2, solid_capstyle="round",
                linestyle=(0, (5, 3)) if dashed else "-")
        end = next((p for p in reversed(shown) if all(math.isfinite(v) for v in p)), None)
        if end:
            labels.append((ax.annotate(visual(c["name"]), end, xytext=(5, 3), textcoords="offset points",
                                       color=colours[c["name"]], fontsize=11, annotation_clip=False),
                           [(5, 3, "left", "baseline"), (0, 7, "right", "baseline"), (5, -14, "left", "baseline"),
                            (-5, -14, "right", "baseline"), (-5, 3, "right", "baseline")]))
    for c in spec["curves"]:
        if c["shift_of"]:
            arrow = shift_arrow(lines[c["shift_of"]], lines[c["name"]])
            if arrow:
                ax.annotate("", arrow[1], arrow[0], arrowprops={"arrowstyle": "-|>", "color": "#444444", "lw": 1.6})
    for label, (px, py) in points:
        ax.plot([px, px], [ylo, py], color="#777777", linewidth=1, linestyle=(0, (3, 3)))
        ax.plot([xlo, px], [py, py], color="#777777", linewidth=1, linestyle=(0, (3, 3)))
        ax.plot([px], [py], "o", color="black", markersize=5)
        labels.append((ax.annotate(visual(label), (px, py), xytext=(6, 6), textcoords="offset points", fontsize=11),
                       [(6, 6, "left", "baseline"), (6, -14, "left", "baseline"),
                        (-6, 6, "right", "baseline"), (-6, -14, "right", "baseline")]))
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    if sketch_only:
        ax.set_xticks([])
        ax.set_yticks([])
    ax.annotate(visual(spec["x"]), (1, 0), xycoords="axes fraction", xytext=(0, -22), textcoords="offset points",
                ha="right", va="top", fontsize=11)
    ax.annotate(visual(spec["y"]), (0, 1), xycoords="axes fraction", xytext=(0, 8), textcoords="offset points",
                ha="left", va="bottom", fontsize=11)
    ax.annotate("", (1, 0), (0.9, 0), xycoords="axes fraction", arrowprops={"arrowstyle": "-|>", "color": "black", "lw": 1})
    ax.annotate("", (0, 1), (0, 0.9), xycoords="axes fraction", arrowprops={"arrowstyle": "-|>", "color": "black", "lw": 1})
    obstacles = []  # every line, as many points in picture coordinates, so labels avoid them too
    for line in lines.values():
        dense = [(a[0] + (b[0] - a[0]) * t / 40, a[1] + (b[1] - a[1]) * t / 40)
                 for a, b in zip(line, line[1:]) for t in range(40)]
        obstacles += [pt for pt in ax.transData.transform([p for p in dense if all(math.isfinite(v) for v in p)])]
    _avoid_overlaps(fig, labels, obstacles)
    fig.savefig(png, format="png", metadata={"Software": None, HASH_KEY: digest})
    return {"png": str(png), "drawn": True}

"""Check a graph SVG without looking at it: portability, labels, dots on curves, area corners, text overlaps.

Standard library only. Geometry is a heuristic: a "curve" is any stroke at least 1.8 wide (axes included);
thinner strokes are guide lines. `check(svg_text, case)` returns a list of plain-words problems.
"""
import math
import re
import sys
import xml.etree.ElementTree as ET

NUM = r"[-+]?(?:\d*\.\d+|\d+\.?)(?:[eE][-+]?\d+)?"
NOT_PORTABLE = [("var(", "uses CSS variables: outside a browser the picture comes out black"),
                ("@media", "uses a CSS media query, which only a browser applies"),
                ("<foreignObject", "uses foreignObject, which only a browser draws"),
                ("<script", "has a script"), ("@import", "imports a stylesheet or font"), ("<image", "embeds another image file")]


def _matrix(text):
    m = (1, 0, 0, 1, 0, 0)
    for name, args in re.findall(r"(\w+)\s*\(([^)]*)\)", text or ""):
        v = [float(n) for n in re.findall(NUM, args)]
        if name == "translate":
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == "scale":
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == "rotate":
            c, s = math.cos(math.radians(v[0])), math.sin(math.radians(v[0]))
            t = (c, s, -s, c, 0, 0)
            if len(v) == 3:
                t = _mul(_mul((1, 0, 0, 1, v[1], v[2]), t), (1, 0, 0, 1, -v[1], -v[2]))
        elif name == "matrix":
            t = tuple(v)
        else:
            continue
        m = _mul(m, t)
    return m


def _mul(a, b):
    return (a[0] * b[0] + a[2] * b[1], a[1] * b[0] + a[3] * b[1], a[0] * b[2] + a[2] * b[3], a[1] * b[2] + a[3] * b[3],
            a[0] * b[4] + a[2] * b[5] + a[4], a[1] * b[4] + a[3] * b[5] + a[5])


def _apply(m, p):
    return (m[0] * p[0] + m[2] * p[1] + m[4], m[1] * p[0] + m[3] * p[1] + m[5])


def _path(d):
    """Flatten a path to polylines. Arcs become a straight line to their end point."""
    out, cur, start, pos, last, prev = [], [], (0, 0), (0, 0), None, None
    for cmd, args in re.findall(r"([MmLlHhVvCcSsQqTtAaZz])([^MmLlHhVvCcSsQqTtAaZz]*)", d):
        v = [float(n) for n in re.findall(NUM, args)]
        rel, c = cmd.islower(), cmd.upper()
        size = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}[c]
        if c == "Z":
            cur.append(start)
            pos = start
            continue
        for i in range(0, len(v) - size + 1, size):
            a = v[i:i + size]
            ox, oy = pos if rel else (0, 0)
            if c == "M":
                if cur:
                    out.append(cur)
                pos = start = (a[0] + ox, a[1] + oy)
                cur, c = [pos], "L"
            elif c == "L":
                pos = (a[0] + ox, a[1] + oy)
                cur.append(pos)
            elif c == "H":
                pos = (a[0] + ox, pos[1])
                cur.append(pos)
            elif c == "V":
                pos = (pos[0], a[0] + oy)
                cur.append(pos)
            elif c == "A":
                pos = (a[5] + ox, a[6] + oy)
                cur.append(pos)
            else:
                pts = [(a[j] + ox, a[j + 1] + oy) for j in range(0, size, 2)]
                if c in "ST":  # the missing control point mirrors the previous one
                    mirror = (2 * pos[0] - last[0], 2 * pos[1] - last[1]) if last and prev in ("CS" if c == "S" else "QT") else pos
                    pts = [mirror] + pts
                ctrl = [pos] + pts
                for k in range(1, 25):
                    t, q = k / 24, ctrl
                    while len(q) > 1:
                        q = [(q[j][0] + (q[j + 1][0] - q[j][0]) * t, q[j][1] + (q[j + 1][1] - q[j][1]) * t) for j in range(len(q) - 1)]
                    cur.append(q[0])
                last, pos = ctrl[-2], ctrl[-1]
            prev = c
    if cur:
        out.append(cur)
    return out


def _dist(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = 0 if dx == dy == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / (dx * dx + dy * dy)))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def parse(svg_text):
    root = ET.fromstring(svg_text)
    rules = {}
    for style in root.iter("{http://www.w3.org/2000/svg}style"):
        for selector, body in re.findall(r"([^{}]+)\{([^}]*)\}", style.text or ""):
            for name in selector.split(","):
                rules.setdefault(name.strip(), {}).update(dict(re.findall(r"([\w-]+)\s*:\s*([^;]+)", body)))
    box = [float(n) for n in re.findall(NUM, root.get("viewBox", ""))] or [0, 0, float(re.findall(NUM, root.get("width", "520"))[0]),
                                                                           float(re.findall(NUM, root.get("height", "420"))[0])]
    strokes, dots, areas, texts = [], [], [], []

    def walk(node, style, matrix, hidden):
        tag = node.tag.split("}")[-1]
        hidden = hidden or tag in ("defs", "pattern", "marker", "clipPath", "symbol", "mask")
        style = dict(style)
        for selector in [tag] + ["." + c for c in (node.get("class") or "").split()] + ["#" + node.get("id", "")]:
            style.update(rules.get(selector, {}))
        style.update({k: v for k, v in node.attrib.items() if k in ("stroke", "stroke-width", "fill", "font-size", "text-anchor", "fill-opacity", "opacity")})
        style.update(dict(re.findall(r"([\w-]+)\s*:\s*([^;]+)", node.get("style") or "")))
        matrix = _mul(matrix, _matrix(node.get("transform")))
        f = lambda name, default=0.0: float((re.findall(NUM, node.get(name) or "") or [default])[0])
        lines = []
        if tag == "line":
            lines = [[(f("x1"), f("y1")), (f("x2"), f("y2"))]]
        elif tag in ("polyline", "polygon"):
            v = [float(n) for n in re.findall(NUM, node.get("points") or "")]
            lines = [list(zip(v[::2], v[1::2]))]
            if tag == "polygon" and lines[0]:
                lines[0].append(lines[0][0])
        elif tag == "path":
            lines = _path(node.get("d") or "")
        elif tag == "rect":
            x, y, w, h = f("x"), f("y"), f("width"), f("height")
            if "%" in (node.get("width") or ""):
                w, h = box[2], box[3]
            lines = [[(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]]
        lines = [[_apply(matrix, p) for p in line] for line in lines if len(line) > 1]
        scale = math.sqrt(abs(matrix[0] * matrix[3] - matrix[1] * matrix[2])) or 1
        width = float((re.findall(NUM, style.get("stroke-width", "1")) or [1])[0]) * scale
        if not hidden:
            filled = style.get("fill", "#000" if tag != "line" else "none").strip() not in ("none", "transparent")
            for line in lines:
                xs, ys = [p[0] for p in line], [p[1] for p in line]
                background = max(xs) - min(xs) > .9 * box[2] and max(ys) - min(ys) > .9 * box[3]
                closed = len(line) > 3 and math.dist(line[0], line[-1]) < .01
                arrowhead = max(max(xs) - min(xs), max(ys) - min(ys)) < 20
                if filled and closed and not background and not arrowhead and tag != "line":
                    areas.append(line)
                if style.get("stroke", "none").strip() not in ("none", "transparent") and not background:
                    strokes.append((width, line, not (filled and closed)))
            if tag == "circle" and f("r") * scale <= 9:
                dots.append(_apply(matrix, (f("cx"), f("cy"))))
            if tag == "text":
                content = "".join(node.itertext()).strip()
                size = float((re.findall(NUM, style.get("font-size", "16")) or [16])[0]) * scale
                x, y = _apply(matrix, (f("x"), f("y")))
                w = .58 * size * len(content)
                anchor = style.get("text-anchor", "start").strip()
                left = x - w if anchor == "end" else x - w / 2 if anchor == "middle" else x
                if content and "rotate" not in (node.get("transform") or ""):
                    texts.append((content, (left, y - .8 * size, left + w, y + .2 * size)))
        for child in node:
            walk(child, style, matrix, hidden)
    walk(root, {}, (1, 0, 0, 1, 0, 0), False)
    return {"box": box, "strokes": strokes, "dots": dots, "areas": areas, "texts": texts,
            "all_text": " ".join("".join(t.itertext()) for t in root.iter("{http://www.w3.org/2000/svg}text"))}


def check(svg_text, case=None):
    problems = [why for needle, why in NOT_PORTABLE if needle in svg_text]
    try:
        g = parse(svg_text)
    except ET.ParseError as error:
        return [f"is not valid XML ({error})"]
    box, tolerance = g["box"], 2.5 * g["box"][2] / 520
    curves = [line for width, line, open_ in g["strokes"] if width >= 1.8]
    near = lambda p, lines: min((_dist(p, a, b) for line in lines for a, b in zip(line, line[1:])), default=1e9)
    for dot in g["dots"]:
        if near(dot, curves) > tolerance:
            problems.append(f"the dot at ({dot[0]:.0f}, {dot[1]:.0f}) is {near(dot, curves):.0f} px away from every curve and axis")
    open_curves = [line for width, line, open_ in g["strokes"] if width >= 1.8 and open_]
    for area in g["areas"]:
        off = [p for p in area[:-1] if near(p, open_curves) > 1.6 * tolerance]
        if off and len(area) <= 8:
            problems.append("an area has a corner off every curve and axis: " + ", ".join(f"({x:.0f}, {y:.0f})" for x, y in off))
    for content, (x0, y0, x1, y1) in g["texts"]:
        if x0 < box[0] - 2 or x1 > box[0] + box[2] + 2 or y0 < box[1] - 2 or y1 > box[1] + box[3] + 2:
            problems.append(f'the text "{content}" runs outside the picture')
    for i, (a, ab) in enumerate(g["texts"]):
        for b, bb in g["texts"][i + 1:]:
            if min(ab[2], bb[2]) - max(ab[0], bb[0]) > 3 and min(ab[3], bb[3]) - max(ab[1], bb[1]) > 3:
                problems.append(f'the texts "{a}" and "{b}" overlap')
    if case:
        missing = [label for label in case["labels"] if not re.search(rf"(?<![A-Za-z0-9]){re.escape(label)}(?![A-Za-z0-9])", g["all_text"])]
        if missing:
            problems.append("missing labels: " + ", ".join(missing))
        if len(g["areas"]) < case["areas"]:
            problems.append(f'{len(g["areas"])} filled areas, the graph needs {case["areas"]}')
    return problems


if __name__ == "__main__":
    for problem in check(open(sys.argv[1], encoding="utf-8").read()) or ["no problems found"]:
        print("-", problem)

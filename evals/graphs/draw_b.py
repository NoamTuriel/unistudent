"""Eval prototype of an upgraded Graph spec: formulas, points on curves, areas, arrows -> one portable SVG.

Not plugin code: it exists so the eval can compare "the model fills a spec" with "the model writes the SVG".
"""
import json
import math
import sys
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "plugins" / "unistudent" / "scripts"))
from unistudent.graph import intersection, parse_formula  # noqa: E402

SPEC_DOC = """\
{
 "x": "כמות (Q)", "y": "מחיר (P)",                  axis names
 "view": {"x": [0, 100], "y": [0, 100]},             the part of the plane that is drawn
 "curves": [
  {"name": "D", "formula": "100 - x"},               a formula in x (the horizontal axis); + - * / ^ sqrt()
  {"name": "S1", "formula": "x", "dashed": true, "same_color_as": "S"},
  {"name": "Pw", "horizontal": 20, "label": "S1 (מחיר עולמי)"},      or "vertical": 40
  {"name": "T", "formula": "12.5 - 0.75*x", "range": [2, 10], "thin": true}
 ],
 "points": [                                         each point has a name; later items may use earlier points
  {"name": "E0", "at": ["S", "D"], "label": ""},     the crossing of two curves; "label": "" shows no letter
  {"name": "B", "on": "S", "x": "E1.x"},             on a curve at an x; "E1.x" / "E1.y" reuse another point
  {"name": "A", "at": [0, "B.y"], "dot": false},     plain coordinates
  {"name": "C", "at": ["S1", "D"], "side": "se", "guides": true, "tick_x": "Q1", "tick_y": "P1 צרכן"}
 ],                                                  side: where the letter sits (n s e w ne nw se sw);
                                                     guides: thin dashed lines to both axes;
                                                     tick_x / tick_y: a name written on that axis
 "areas": [{"points": ["A", "B", "C", "E"], "style": "government", "label": ""}],
                                                     style: consumer (pink) producer (blue) government (hatched) loss (yellow)
 "arrows": [{"from": "L1p", "to": "L2p", "double": true, "label": "אבטלה"}],
 "notes": [{"text": "קו המחירים", "at": [7, 9]}]     free text at coordinates
}"""

W, H, LEFT, RIGHT, TOP, BOTTOM = 520, 420, 78, 40, 34, 52
PALETTE = ["#c0392b", "#1f5fa8", "#2e8b57", "#8e44ad", "#d35400"]
FILLS = {"consumer": ("#f4a6c0", .6), "producer": ("#8fbcee", .6), "government": ("url(#hatch)", 1), "loss": ("#f4d03f", .9)}
SIDES = {"n": (0, -10, "middle"), "s": (0, 20, "middle"), "e": (9, 5, "start"), "w": (-9, 5, "end"),
         "ne": (8, -8, "start"), "nw": (-8, -8, "end"), "se": (8, 18, "start"), "sw": (-8, 18, "end")}


def draw(spec):
    (x0, x1), (y0, y1) = spec["view"]["x"], spec["view"]["y"]
    X = lambda x: round(LEFT + (x - x0) / (x1 - x0) * (W - LEFT - RIGHT), 2)
    Y = lambda y: round(H - BOTTOM - (y - y0) / (y1 - y0) * (H - TOP - BOTTOM), 2)
    lines, funcs = {}, {}
    for c in spec["curves"]:
        if "formula" in c:
            f = funcs[c["name"]] = parse_formula(c["formula"])
            lo, hi = c.get("range") or (x0, x1)
            pts = [(lo + (hi - lo) * i / 400, f(lo + (hi - lo) * i / 400)) for i in range(401)]
            lines[c["name"]] = [p for p in pts if math.isfinite(p[1]) and y0 - 1e-9 <= p[1] <= y1 + 1e-9]
        elif "horizontal" in c:
            funcs[c["name"]] = lambda x, v=c["horizontal"]: v
            lines[c["name"]] = [(x0, c["horizontal"]), (x1, c["horizontal"])]
        else:
            lines[c["name"]] = [(c["vertical"], y0), (c["vertical"], y1)]
    pts = {}

    def num(v):
        if isinstance(v, str):
            name, _, axis = v.rpartition(".")
            return pts[name][axis == "y"]
        return float(v)
    for p in spec.get("points", []):
        if "on" in p:
            x = num(p["x"])
            pts[p["name"]] = (x, funcs[p["on"]](x))
        elif all(isinstance(a, str) and a in lines for a in p["at"]):
            found = intersection(lines[p["at"][0]], lines[p["at"][1]])
            if not found:
                raise ValueError(f'{p["at"][0]} and {p["at"][1]} do not cross inside the view, so point {p["name"]} has no place.')
            pts[p["name"]] = found
        else:
            pts[p["name"]] = (num(p["at"][0]), num(p["at"][1]))
    text = lambda x, y, s, anchor="start", size=14, weight="400", fill="#1d1d1f": (
        f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" fill="{fill}">{escape(str(s))}</text>')
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" font-family="Arial, Helvetica, sans-serif">',
           '<defs><pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
           '<rect width="7" height="7" fill="#e3f3ea"/><line x1="0" y1="0" x2="0" y2="7" stroke="#2e8b57" stroke-width="2"/></pattern>'
           '<marker id="head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
           '<path d="M0,0 L10,5 L0,10 z" fill="#333"/></marker></defs>',
           f'<rect width="{W}" height="{H}" rx="12" fill="#ffffff"/>']
    for a in spec.get("areas", []):
        fill, opacity = FILLS[a["style"]]
        corners = [pts[n] for n in a["points"]]
        out.append(f'<polygon points="{" ".join(f"{X(x)},{Y(y)}" for x, y in corners)}" fill="{fill}" fill-opacity="{opacity}"/>')
        if a.get("label"):
            out.append(text(X(sum(x for x, _ in corners) / len(corners)), Y(sum(y for _, y in corners) / len(corners)) + 4,
                            a["label"], "middle", 12))
    for p in spec.get("points", []):
        x, y = pts[p["name"]]
        if p.get("guides"):
            out.append(f'<path d="M{X(x0)},{Y(y)} L{X(x)},{Y(y)} L{X(x)},{Y(y0)}" fill="none" stroke="#777" stroke-width="1" stroke-dasharray="3 4"/>')
        if p.get("tick_x"):
            out.append(text(X(x), Y(y0) + 18, p["tick_x"], "middle", 13))
        if p.get("tick_y"):
            out.append(text(X(x0) - 7, Y(y) + 5, p["tick_y"], "end", 13))
    colors = {}
    for c in spec["curves"]:
        colors[c["name"]] = colors.get(c.get("same_color_as")) or PALETTE[len(set(colors.values())) % len(PALETTE)]
        line = lines[c["name"]]
        if not line:
            raise ValueError(f'Curve {c["name"]} is outside the view.')
        dash = ' stroke-dasharray="9 6"' if c.get("dashed") else ""
        out.append(f'<polyline points="{" ".join(f"{X(x)},{Y(y)}" for x, y in line)}" fill="none" '
                   f'stroke="{colors[c["name"]]}" stroke-width="{1.6 if c.get("thin") else 3}"{dash}/>')
        ex, ey = line[-1]
        out.append(text(min(X(ex) + 6, W - 6), Y(ey) - 6 if Y(ey) > TOP + 12 else Y(ey) + 16, c.get("label", c["name"]),
                        "end" if X(ex) > W - 90 else "start", 15, "700", colors[c["name"]]))
    out.append(f'<path d="M{X(x0)},{TOP - 14} L{X(x0)},{Y(y0)} L{W - RIGHT + 14},{Y(y0)}" fill="none" stroke="#333" stroke-width="2"/>')
    out.append(text(X(x0) - 8, TOP - 14, spec.get("y", ""), "middle", 14))
    out.append(text(W - 12, H - 10, spec.get("x", ""), "end", 14))
    for a in spec.get("arrows", []):
        (ax, ay), (bx, by) = pts[a["from"]], pts[a["to"]]
        start = ' marker-start="url(#head)"' if a.get("double") else ""
        out.append(f'<line x1="{X(ax)}" y1="{Y(ay)}" x2="{X(bx)}" y2="{Y(by)}" stroke="#333" stroke-width="1.6" marker-end="url(#head)"{start}/>')
        if a.get("label"):
            out.append(text((X(ax) + X(bx)) / 2, (Y(ay) + Y(by)) / 2 - 9, a["label"], "middle", 13))
    for p in spec.get("points", []):
        x, y = pts[p["name"]]
        if p.get("dot", True):
            out.append(f'<circle cx="{X(x)}" cy="{Y(y)}" r="4.5" fill="#333"/>')
        label = p.get("label", p["name"])
        if label:
            dx, dy, anchor = SIDES[p.get("side", "ne")]
            out.append(text(X(x) + dx, Y(y) + dy, label, anchor, 15, "700"))
    for n in spec.get("notes", []):
        out.append(text(X(num(n["at"][0])), Y(num(n["at"][1])), n["text"], "middle", 13))
    return "\n".join(out) + "\n</svg>\n"


if __name__ == "__main__":
    source = Path(sys.argv[1])
    source.with_suffix(".svg").write_text(draw(json.loads(source.read_text("utf-8"))), "utf-8")

"""The Before-the-test page: merge the exam indexers' rows, then write the page from the rows and the clusters."""
import html
import json
import shutil
import subprocess
from pathlib import Path

from .common import UserError

KEYS = {"exam", "part", "q", "qpages", "solpages", "unit", "topic", "skill", "style", "points", "confidence"}
TEXT = {
    "he": {"q": "שאלה", "part": "חלק", "pts": "נק׳", "page": "עמוד", "sol": "פתרון", "nosol": "אין פתרון בקבצים",
           "shown": "כולל תשובה בכתב יד", "unit": "יחידה", "other": "שאלות בודדות", "notes": "מה לא נבדק",
           "intro": "שאלות ממבחנים קודמים בלבד, מקובצות לפי שיטת הפתרון, מהקל לקשה. נכשלת בשאלה? פתח את הפתרון, ופתור את הבאה בקבוצה.",
           "n1": "קישור \"שאלה\" פותח עמוד בודד בלי הפתרון; כשהתשובה על אותו עמוד של השאלה אי אפשר להסתיר אותה, והקישור אומר זאת.",
           "n2": "חלוקה לקבוצות, כותרות ורמזים הם סיווג של ה-AI, לא של הקורס, ויתכנו בו טעויות. השיוך ליחידה לפי תוכן השאלה.",
           "nlow": "שאלות שמיפוי העמודים או היחידה שלהן בביטחון נמוך: {n}.", "nnosol": "מבחנים עם שאלות ללא פתרון בקבצים: {x}.",
           "nnocopy": "לא נוצרו עמודי שאלות בודדים (חסר pdfseparate); הקישורים מובילים לעמוד המקורי, ולעיתים הפתרון נראה בו."},
    "en": {"q": "Question", "part": "part", "pts": "pts", "page": "page", "sol": "Solution", "nosol": "no solution in the files",
           "shown": "includes the handwritten answer", "unit": "Unit", "other": "Standalone questions", "notes": "What was not verified",
           "intro": "Past-exam questions only, grouped by solving method, easy to hard. Failed one? Open its solution, then do the next in the group.",
           "n1": "The \"Question\" link opens a single page without the solution; when the answer sits on the question's own page it cannot be hidden, and the link says so.",
           "n2": "The groups, titles and hints are the AI's classification, not the course's, and may be wrong. A question is placed by its content.",
           "nlow": "Questions whose page mapping or unit has low confidence: {n}.", "nnosol": "Exams with questions that have no solution in the files: {x}.",
           "nnocopy": "No single-page copies were made (pdfseparate is missing); links go to the original page, where the solution may show."},
}


def merge(files, out):
    """Concatenate the indexers' JSON arrays, check the keys, add `id`."""
    rows = []
    for f in files:
        rows += json.loads(Path(f).read_text("utf-8"))
    for i, r in enumerate(rows):
        if KEYS - r.keys():
            raise UserError(f"Row {i} ({r.get('exam')} q{r.get('q')}) lacks: {', '.join(sorted(KEYS - r.keys()))}")
        r["id"] = i
    Path(out).write_text(json.dumps(rows, ensure_ascii=False, indent=1), "utf-8")
    return len(rows)


def _pdf(course, exam):
    found = sorted(course.material.rglob(exam + ".pdf"))
    if not found:
        raise UserError(f"No PDF named {exam}.pdf in the Material folder.")
    return found[0]


def _link(pdf, page, text):
    return f"{pdf.as_uri()}#page={page}", text


def _rows(course, rows, folder, t):
    """Per row: (question links, solution links) as (url, text); makes the single-page copies."""
    copies, links = shutil.which("pdfseparate"), {}
    for r in rows:
        pdf = _pdf(course, r["exam"])
        sol = r["solpages"]
        ql = []
        for p in r["qpages"]:
            if sol and p not in sol and copies:  # the solution is elsewhere: link a copy of just this page
                one = folder / f"{r['exam']} - {p}.pdf"
                if not one.exists():
                    folder.mkdir(parents=True, exist_ok=True)
                    subprocess.run(["pdfseparate", "-f", str(p), "-l", str(p), str(pdf), str(one)], check=True)
                ql.append((one.as_uri(), f"{t['q']} ({t['page']} {p})"))
            else:
                note = f", {t['shown']}" if p in sol else ""
                ql.append(_link(pdf, p, f"{t['q']} ({t['page']} {p}{note})"))
        sl = [_link(pdf, p, f"{t['sol']} ({t['page']} {p})") for p in sol]
        links[r["id"]] = (ql, sl)
    return links, bool(copies)


def build(course, index, clusters, fmt, notes):
    rows = {r["id"]: r for r in json.loads(Path(index).read_text("utf-8"))}
    clusters = json.loads(Path(clusters).read_text("utf-8"))
    t = TEXT.get(course.settings().get("language", "he"), TEXT["en"])
    name = course.label("before_test")
    folder = course.study / f"{name} - {course.label('question_pages')}"
    course.study.mkdir(exist_ok=True)
    seen = {i for c in clusters for i in c["ids"]}
    unknown = seen - rows.keys()
    if unknown:
        raise UserError(f"Clusters name unknown row ids: {sorted(unknown)[:10]}")
    for u in sorted({r["unit"] for r in rows.values() if r["id"] not in seen}):  # nothing is dropped
        clusters.append({"unit": u, "title": t["other"], "hint": "", "ids": [i for i, r in rows.items() if r["unit"] == u and i not in seen]})
    links, copied = _rows(course, list(rows.values()), folder, t)
    nosol = sorted({r["exam"] for r in rows.values() if not r["solpages"]})
    low = sum(r["confidence"] == "low" for r in rows.values())
    notes = [t["n1"], t["n2"]] + ([t["nlow"].format(n=low)] if low else []) \
        + ([t["nnosol"].format(x=", ".join(nosol))] if nosol else []) + ([] if copied else [t["nnocopy"]]) + list(notes or [])

    def row(r):
        ql, sl = links[r["id"]]
        head = f"{r['exam']}, {t['q']} {r['q']} ({t['part']} {r['part']}, {r['points']} {t['pts']}): {r['skill']}"
        return head, ql, (sl or [(None, t["nosol"])])

    units = sorted({c["unit"] for c in clusters})
    out = []
    if fmt == "html":
        a = lambda u, x: f'<a href="{html.escape(u)}">{html.escape(x)}</a>' if u else html.escape(x)
        out = [f'<!doctype html><html lang="{course.settings().get("language", "he")}" dir="{'rtl' if course.settings().get('language', 'he') == 'he' else 'ltr'}"><meta charset="utf-8"><title>{name}</title>',
               "<style>body{font:17px/1.65 system-ui,Arial;max-width:900px;margin:24px auto;padding:0 16px}h2{background:#e8eef8;padding:6px 10px}"
               "li{margin:9px 0}details{margin:6px 0}summary{cursor:pointer;font-weight:bold}.n{background:#fff4d6;padding:8px 12px}</style>",
               f"<h1>{name}</h1><p>{html.escape(t['intro'])}</p>",
               f'<div class="n"><b>{t["notes"]}</b><ul>' + "".join(f"<li>{html.escape(n)}</li>" for n in notes) + "</ul></div>",
               "<p>" + " ".join(f'<a href="#u{u}">{t["unit"]} {u}</a>' for u in units) + "</p>"]
        for u in units:
            cs = [c for c in clusters if c["unit"] == u]
            out.append(f'<h2 id="u{u}">{t["unit"]} {u} ({sum(len(c["ids"]) for c in cs)})</h2>')
            for c in cs:
                out.append(f"<details><summary>{html.escape(c['title'])} ({len(c['ids'])})</summary><p>{html.escape(c['hint'])}</p><ol>")
                for i in c["ids"]:
                    head, ql, sl = row(rows[i])
                    out.append(f"<li>{html.escape(head)}<br>" + ", ".join(a(*x) for x in ql) + " &nbsp;|&nbsp; " + ", ".join(a(*x) for x in sl) + "</li>")
                out.append("</ol></details>")
        ext = ".html"
    else:
        md = lambda u, x: f"[{x}](<{u}>)" if u else x
        out = [f"# {name}", "", t["intro"], "", f"**{t['notes']}**", ""] + [f"- {n}" for n in notes] + [""]
        for u in units:
            cs = [c for c in clusters if c["unit"] == u]
            out += [f"## {t['unit']} {u} ({sum(len(c['ids']) for c in cs)})", ""]
            for c in cs:
                body = [c["hint"], ""] if c["hint"] else []
                for i in c["ids"]:
                    head, ql, sl = row(rows[i])
                    body.append(f"- [ ] {head} - " + ", ".join(md(*x) for x in ql) + " | " + ", ".join(md(*x) for x in sl))
                title = f"{c['title']} ({len(c['ids'])})"
                if fmt == "obsidian":
                    out += [f"> [!example]- {title}"] + [f"> {b}" if b else ">" for b in body] + [""]
                else:
                    out += [f"<details><summary>{title}</summary>", ""] + body + ["", "</details>", ""]
        ext = ".md"
    page = course.study / (name + ext)
    page.write_text("\n".join(out) + "\n", "utf-8")
    return {"page": str(page), "questions": len(rows), "clusters": len(clusters), "single_page_copies": copied, "notes": notes,
            "summary": f"Wrote {page} ({len(rows)} questions in {len(clusters)} groups)."}

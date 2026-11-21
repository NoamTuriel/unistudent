"""Open assignments: which Assignments can still be submitted, whether the Wiki can solve them, and their Trap scan.

The data is a Manifest entry's `assignment` record (`due`, `status`), written by `us ingest` from a university plugin's
listing or by `us assignments set` for a file the student added (ADR 0019). Nothing here submits anything.
"""
import datetime
import re
from pathlib import Path

from . import material, scan, wiki
from .common import UserError

STATUSES = ("open", "submitted", "graded", "unknown")
DONE = ("submitted", "graded")


def parse_date(text):
    try:
        return datetime.date.fromisoformat(text)
    except (TypeError, ValueError):
        raise UserError(f"A date is written YYYY-MM-DD, e.g. 2026-12-31 (got {text!r}).")


def _day(text):
    """The YYYY-MM-DD day of a listing's due date (a time after it is dropped), or None when it is not a date: a site's
    odd value never stops a sync or a later command."""
    day = str(text or "")[:10]
    try:
        return datetime.date.fromisoformat(day).isoformat() if re.fullmatch(r"\d{4}-\d{2}-\d{2}", day) else None
    except ValueError:
        return None


def record_of(item):
    """The `assignment` record a listing item carries, or None when it is not an assignment."""
    if item.get("kind") != "assignment":
        return None
    return {"due": _day(item.get("due")), "status": item["status"] if item.get("status") in STATUSES else "unknown"}


def refresh(course, items):
    """A sync lists every item each time: bring the date and status of assignments already in the Manifest up to date,
    also when the file itself did not change (a status moves from open to submitted with the same PDF)."""
    wanted = {}
    for item in items:
        record = record_of(item)
        if item.get("url") and record:
            wanted[item["url"]] = record
    if not wanted:
        return
    with course.edit_manifest() as manifest:
        for entry in manifest["files"].values():
            if entry.get("site_url") in wanted:
                entry["assignment"] = wanted[entry["site_url"]]


def mark(course, rel, due=None, status=None):
    if rel not in course.manifest()["files"]:
        raise UserError(f"Not in the Manifest: {rel}")
    if due is not None:
        parse_date(due)
    if status is not None and status not in STATUSES:
        raise UserError(f"The status is one of: {', '.join(STATUSES)}.")
    with course.edit_manifest() as manifest:
        record = manifest["files"][rel].setdefault("assignment", {"due": None, "status": "unknown"})
        if due is not None:
            record["due"] = due
        if status is not None:
            record["status"] = status
        return dict(record)


def _state(status, due, today):
    """open, no_date (open, date unknown), overdue, or None when it is already submitted or graded."""
    if status in DONE:
        return None
    if not due:
        return "no_date"
    return "overdue" if due < today else "open"


def _readiness(files, rel, coverage):
    """What the Wiki can say before any question is read: was the file read, and does its unit have other material."""
    status = coverage.get(rel, {}).get("status", "pending")
    unit = files[rel].get("unit")
    others = [r for r, e in files.items()
              if r != rel and "assignment" not in e and coverage.get(r, {}).get("status") == "analyzed"
              and (unit in (None, "general") or e.get("unit") in (unit, "general"))]
    if status != "analyzed":
        why = {"failed": "the Wiki could not read this file", "skipped": "the Wiki does not read this kind of file",
               "pending": "the Wiki has not read this file yet: run the Wiki build"}[status]
        return {"file_read": status, "unit_sources": len(others), "ready": "needs-material", "why": why}
    if not others:
        return {"file_read": status, "unit_sources": 0, "ready": "needs-material",
                "why": "no lecture, booklet or other source of its unit is in the Wiki: add material (inbox, course-add)"}
    return {"file_read": status, "unit_sources": len(others), "ready": "yes",
            "why": "the file and its unit's material are in the Wiki; the question-by-question check is still to do"}


def listing(course, today=None):
    today = parse_date(today) if today else datetime.date.today()
    files = course.manifest()["files"]
    open_, overdue = [], []
    if any("assignment" in e for e in files.values()):  # the Wiki's coverage is only read when there is an assignment
        coverage = {r["path"]: r for r in wiki.coverage(course)["files"]}
        for rel, entry in sorted(files.items()):
            record = entry.get("assignment")
            if not record:
                continue
            due = _day(record.get("due"))
            day = datetime.date.fromisoformat(due) if due else None
            state = _state(record.get("status"), day, today)
            if state is None:
                continue
            row = {"path": rel, "unit": entry.get("unit"), "due": due, "status": record.get("status"), "state": state,
                   "days_left": (day - today).days if day else None, **_readiness(files, rel, coverage)}
            (overdue if state == "overdue" else open_).append(row)
    open_.sort(key=lambda r: (r["due"] is None, r["due"] or ""))

    def line(r):
        when = {"no_date": "no date known", "overdue": f"overdue since {r['due']}"}.get(r["state"], f"due {r['due']}")
        return f"- {r['path']}: {when}; {'ready to solve from the Wiki' if r['ready'] == 'yes' else 'needs material: ' + r['why']}"
    lines = [f"{len(open_)} open assignments" + (f", {len(overdue)} overdue" if overdue else "") + "."]
    lines += [line(r) for r in open_ + overdue]
    return {"open": open_, "overdue": overdue, "today": today.isoformat(), "summary": "\n".join(lines)}


def trap_scan(course, names):
    """The Trap scan of the given files (paths in the Material folder or full paths), or of every assignment still open."""
    if not names:
        found = listing(course)
        names = [r["path"] for r in found["open"] + found["overdue"]]
    results = []
    for name in names:
        path = Path(name) if Path(name).is_file() else material.path_of(course, name)
        if not path.is_file():
            raise UserError(f"No such file: {name}")
        results.append({**scan.scan_file(path), "path": name})
    lines, found = [], sum(len(r["findings"]) for r in results)
    for r in results:
        lines.append(f"{r['path']}: " + (f"{len(r['findings'])} findings." if r["findings"] else "nothing found."))
        lines += [f"  - {f['summary']}" for f in r["findings"]]
        lines += [f"  - could not check: {n}" for n in r["could_not_check"]]
    return {"files": results, "found": found, "aimed_at_ai": sum(f["aimed_at_ai"] for r in results for f in r["findings"]),
            "summary": "\n".join(lines) or "No assignments to scan."}

"""The Fetch plan: what a fetch from the course site will download, approved by the student before anything downloads.

Built from a University plugin's listing (or the generated fallback's), so every university gets the same screen.
`show` writes the checklist into the Hidden folder, `apply` reads its ticks back into the approved listing, `status`
counts what the run has done from the approved listing, the Manifest and the recordings state (files from the student's
own folder or the inbox count as already in, so a course with no site still gets the box).
"""
import hashlib
import json
import re
import shutil
from pathlib import Path

from .common import UserError
from .course import parse_unit, safe_name
from .sorting import detect_unit

RECORDING_BYTES_PER_SECOND = 1_800_000 / 8  # the site's documented 1.8 Mbit/s: about 0.81 GB per hour
ROUGH_DOWNLOAD_BYTES_PER_SECOND = 2_500_000  # ponytail: a fixed rough network speed until a download is measured
ROUGH_REALTIME_FACTOR = {"mlx": 0.15, "faster": 0.5}  # hours of work per hour of audio, before a benchmark
TICK = re.compile(r"^\s*[-*]\s*\[([ xX])\]\s*(\d+)\.", re.M)
WARNING = ["KEEP THE COMPUTER ON, PLUGGED IN AND AWAKE.", "KEEP THIS APP AND CHROME OPEN."]


def _folder(course):
    return course.state / "fetch-plan"


def checklist_file(course):
    return _folder(course) / "checklist.md"


def approved_file(course):
    return _folder(course) / "approved-listing.json"


def is_recording(item):
    return item.get("kind") == "recording"


def extension(item):
    if is_recording(item):
        return ".mp4"  # a recording's name is its title, often with a dotted date ("12.10.2025")
    return Path(item.get("name") or item.get("file") or "").suffix.lower() or "(none)"


def size_of(item):
    """(bytes, estimated); bytes is None when the site gave neither a size nor a recording's length."""
    if item.get("size") is not None:
        return int(item["size"]), False
    if is_recording(item) and item.get("seconds"):
        return round(float(item["seconds"]) * RECORDING_BYTES_PER_SECOND), True
    return None, False


def human(n):
    for unit, scale in (("GB", 1e9), ("MB", 1e6), ("KB", 1e3)):
        if n >= scale:
            return f"{n / scale:.1f} {unit}" if unit == "GB" else f"{round(n / scale)} {unit}"
    return f"{n} bytes"


def plural(n, word):
    return f"{n} {word}" + ("" if n == 1 else "s")


def _ordered(items):
    """Biggest first; unknown sizes last. Stable for the same listing, so a line's number names the same file."""
    return sorted(items, key=lambda i: (-(size_of(i)[0] or -1), i.get("name") or "", i.get("url") or ""))


def _plan_id(items):
    return hashlib.sha1(json.dumps([i.get("url") for i in items]).encode("utf-8")).hexdigest()[:12]


def _read_listing(path):
    return json.loads(Path(path).read_text("utf-8"))


def _ticks(course, plan_id):
    """{number: ticked} from the checklist, when it was written for this listing; None otherwise."""
    path = checklist_file(course)
    if not path.is_file():
        return None
    text = path.read_text("utf-8")
    if f"<!-- fetch-plan {plan_id} -->" not in text:
        return None
    return {int(number): mark != " " for mark, number in TICK.findall(text)}


def realtime_factor():
    """(hours of transcription per hour of audio, measured?)."""
    from .recordings import _benchmark_file, backend_name
    try:
        return json.loads(_benchmark_file().read_text("utf-8"))["realtime_factor"], True
    except (FileNotFoundError, KeyError, ValueError):
        return ROUGH_REALTIME_FACTOR.get(backend_name(), 0.5), False


def time_left(download_bytes, transcribe_seconds):
    """(hours, rough): rough whenever a part of it comes from a fixed constant rather than a measurement."""
    factor, measured = realtime_factor()
    seconds = download_bytes / ROUGH_DOWNLOAD_BYTES_PER_SECOND + transcribe_seconds * factor
    rough = download_bytes > 0 or (transcribe_seconds > 0 and not measured)
    return round(seconds / 3600, 2), rough


def about(hours, rough, after=""):
    text = f"about {max(1, round(hours * 60))} minutes" if hours < 1 else f"about {hours:.1f} hours"
    return text + after + (" (rough estimate)" if rough else "")


def _transcribes(course):
    return course.settings().get("recording_level") == 3


def show(course, listing_path):
    items = _ordered(_read_listing(listing_path).get("items", []))
    plan_id = _plan_id(items)
    ticks = _ticks(course, plan_id)
    totals, lines, needs_unit = {}, [], []
    total = unknown = transcribe_seconds = 0
    for number, item in enumerate(items, 1):
        ticked = True if ticks is None else ticks.get(number, False)  # a new listing starts all ticked
        size, estimated = size_of(item)
        ext = extension(item)
        shown = "size unknown" if size is None else ("~" if estimated else "") + human(size)
        lines.append(f"- [{'x' if ticked else ' '}] {number}. {shown}  {ext}  {item.get('name') or item.get('url')}  "
                     f"({item.get('section') or 'no section'})")
        if not ticked:
            continue
        entry = totals.setdefault(ext, {"files": 0, "bytes": 0, "estimated": False, "unknown_size": 0})
        entry["files"] += 1
        entry["bytes"] += size or 0
        entry["estimated"] |= estimated
        entry["unknown_size"] += size is None
        total += size or 0
        unknown += size is None
        if is_recording(item) and _transcribes(course):
            transcribe_seconds += float(item.get("seconds") or 0)
        if not is_recording(item) and item.get("unit_hint") is None:
            name = safe_name(item.get("name") or "file")  # the same evidence ingest will sort by
            if detect_unit(f"{safe_name(item.get('section') or 'General')}/{name}")[0] is None:
                needs_unit.append({"number": number, "name": item.get("name"), "section": item.get("section")})
    estimated_any = any(t["estimated"] for t in totals.values())
    total_line = f"Total: {'~' if estimated_any else ''}{human(total)}" + (
        f", plus {plural(unknown, 'file')} of unknown size" if unknown else "") + "."
    path = checklist_file(course)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Fetch plan\n\n"
                    "Every file the course site has that is not downloaded yet, biggest first. Untick a line "
                    "(change [x] to [ ]) to skip that file. Sizes with ~ are estimates.\n\n"
                    f"<!-- fetch-plan {plan_id} -->\n" + "\n".join(lines) + f"\n\n{total_line}\n", "utf-8")
    free = shutil.disk_usage(course.root).free
    hours, rough = time_left(total, transcribe_seconds)
    fits = total <= free
    by_ext = ", ".join(f"{ext} " + ("size unknown" if t["files"] == t["unknown_size"]
                                    else ("~" if t["estimated"] else "") + human(t["bytes"]))
                       for ext, t in sorted(totals.items(), key=lambda kv: -kv[1]["bytes"]))
    summary = (f"{plural(sum(t['files'] for t in totals.values()), 'file')} ticked ({by_ext}). {total_line} "
               f"Free disk space: {human(free)}" + ("." if fits else ": the plan does not fit, untick some files first.")
               + f" Time: {about(hours, rough)}. Checklist: {path}")
    return {"checklist": str(path), "totals": totals, "total_bytes": total, "unknown_size": unknown,
            "free_bytes": free, "fits": fits, "hours": hours, "rough": rough, "needs_unit": needs_unit,
            "summary": summary}


def apply(course, listing_path, unit_answers):
    data = _read_listing(listing_path)
    items = _ordered(data.get("items", []))
    ticks = _ticks(course, _plan_id(items))
    if ticks is None:
        raise UserError("No Fetch plan for this listing yet: run `us fetch-plan show` first and let the student "
                        "look at it.")
    answers = {}
    for pair in unit_answers or []:
        number, _, answer = pair.partition("=")
        answers[int(number)] = None if answer.strip().lower() in ("unknown", "unsorted") else parse_unit(answer)
    chosen = []
    for number, item in enumerate(items, 1):
        if not ticks.get(number, False):
            continue  # unticked, or a line the student deleted
        item = dict(item)
        if number in answers:
            item.pop("unit_hint", None)  # "I don't know": no hint, so ingest leaves the file unsorted
            if answers[number] is not None:
                item["unit_hint"] = answers[number]
        if is_recording(item) and _transcribes(course):
            item["transcribe"] = True  # ingest approves it for transcription once it is downloaded
        chosen.append(item)
    path = approved_file(course)
    path.write_text(json.dumps({**data, "items": chosen}, ensure_ascii=False, indent=1), "utf-8")
    recordings = sum(1 for i in chosen if is_recording(i))
    return {"listing": str(path), "files": len(chosen), "recordings": recordings,
            "transcribe": sum(1 for i in chosen if i.get("transcribe")),
            "summary": f"Approved {plural(len(chosen), 'file')} ({plural(recordings, 'recording')}). "
                       f"Approved listing: {path}"}


def _bar(done, total, width=20):
    filled = width * done // total if total else width
    return "[" + "#" * filled + "-" * (width - filled) + "]"


def status(course):
    from .material import path_of
    from .recordings import approved, duration
    from .wiki import recording_pages
    path = approved_file(course)
    files = course.manifest()["files"]
    own = [rel for rel, e in files.items() if not e.get("site_url")]  # the student's folder or the inbox: already in
    if not path.is_file() and not own:
        raise UserError("No Fetch plan approved yet: run `us fetch-plan show`, then `us fetch-plan apply`.")
    items = _read_listing(path).get("items", []) if path.is_file() else []
    by_url = {e.get("site_url"): rel for rel, e in files.items() if e.get("site_url")}
    pages = recording_pages(course)
    chosen = set(approved(course))
    for rel in own:
        by_url[rel] = rel
        items.append({"url": rel, "kind": "recording", "transcribe": rel in chosen,
                      "seconds": duration(path_of(course, rel))} if rel in pages else {"url": rel})
    docs = [i for i in items if not is_recording(i)]
    recs = [i for i in items if is_recording(i)]
    docs_done = sum(1 for i in docs if i.get("url") in by_url)
    downloaded = [i for i in recs if i.get("url") in by_url]
    pages_of = {i.get("url"): pages.get(by_url[i.get("url")]) for i in downloaded}
    transcribed = [i for i in downloaded if pages_of[i.get("url")]
                   and (course.wiki / pages_of[i.get("url")]["folder"] / "transcript.md").exists()]
    summarised = [i for i in downloaded if pages_of[i.get("url")] and pages_of[i.get("url")]["processed"]]
    to_download = sum(size_of(i)[0] or 0 for i in items if i.get("url") not in by_url)
    to_transcribe = sum(float(i.get("seconds") or 0) for i in recs if i.get("transcribe") and i not in transcribed)
    hours, rough = time_left(to_download, to_transcribe)
    wanted = sum(1 for i in recs if i.get("transcribe"))
    steps = len(recs) + 2 * wanted
    rows = WARNING + [about(hours, rough, " left").upper() + ".", "",
                      f"Documents   {_bar(docs_done, len(docs))}  {docs_done} of {len(docs)} downloaded",
                      f"Recordings  {_bar(len(downloaded) + len(transcribed) + len(summarised), steps)}  "
                      f"{len(downloaded)} of {len(recs)} downloaded, {len(transcribed)} transcribed, "
                      f"{len(summarised)} summarised"]
    width = max(len(row) for row in rows) + 2
    box = "\n".join(["+" + "-" * width + "+"] + [f"| {row.ljust(width - 2)} |" for row in rows]
                    + ["+" + "-" * width + "+"])
    return {"documents": {"done": docs_done, "total": len(docs)},
            "recordings": {"downloaded": len(downloaded), "transcribed": len(transcribed),
                           "summarised": len(summarised), "total": len(recs)},
            "hours": hours, "rough": rough, "box": box, "summary": box}

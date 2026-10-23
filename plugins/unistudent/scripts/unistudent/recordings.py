"""Recordings: estimates, audio extraction and speech-to-text into the Wiki.

Heavy and slow, so nothing here runs without the skill asking the student first.
Speech-to-text backends (picked per machine, same output):
  mlx       Apple silicon (pip install mlx-whisper)
  faster    everything else (pip install faster-whisper), CPU or CUDA
  fake      tests only (UNISTUDENT_STT_BACKEND=fake)
"""
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

from . import material
from .common import UserError
from .convert import RECORDINGS
from .course import home
from .course import unit_dir
from .wiki import recording_pages, video_link

# Hebrew-tuned models by ivrit.ai; other languages use the multilingual model.
MODELS = {
    ("faster", "he"): "ivrit-ai/whisper-large-v3-turbo-ct2",
    ("faster", None): "large-v3-turbo",
    ("mlx", "he"): "mlx-community/ivrit-ai-whisper-large-v3-mlx",
    ("mlx", None): "mlx-community/whisper-large-v3-turbo",
}
# The student's choice when a run is long ("transcription": "fast"): measured on two real Hebrew lessons, 3.0 and 2.7
# times faster than the accurate model, with about 3 and 5 more misheard words per 10 minutes.
FAST_MODELS = {("mlx", "he"): "mlx-community/ivrit-ai-whisper-large-v3-turbo-mlx"}
FAST_SPEEDUP = 2.7
PARAGRAPH_SECONDS = 60

SYNCED_MARKERS = ("mobile documents", "icloud", "google drive", "googledrive", "my drive",
                  "dropbox", "onedrive", "box sync")


def is_synced_folder(path: Path) -> bool:
    """iCloud, Google Drive, Dropbox and OneDrive evict big files, so recordings stay out of them."""
    return any(marker in part.lower() for part in Path(path).parts for marker in SYNCED_MARKERS)


def recordings_root() -> Path:
    """Where recordings of synced course folders live: local, never synced."""
    return Path(os.environ.get("UNISTUDENT_RECORDINGS_ROOT") or Path.home() / "UniStudent recordings")

PACKAGES = {"mlx": "mlx-whisper", "faster": "faster-whisper"}


def hms(seconds: float) -> str:
    seconds = int(seconds)
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def duration(path: Path):
    """Seconds, or None when ffprobe is missing or the file isn't media."""
    if not shutil.which("ffprobe"):
        return None
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                             "-of", "default=nw=1:nk=1", str(path)], capture_output=True, text=True)
    try:
        return float(result.stdout.strip())
    except ValueError:
        return None


def recording_seconds(course, rel):
    """A recording's length, measured once and kept in its Manifest entry while the file's content stays the same."""
    entry = course.manifest()["files"].get(rel, {})
    if entry.get("seconds") is not None and entry.get("seconds_of") == entry.get("fingerprint"):
        return entry["seconds"]
    seconds = duration(material.path_of(course, rel))
    if seconds is not None:
        with course.edit_manifest() as manifest:
            if rel in manifest["files"]:
                manifest["files"][rel].update(seconds=seconds, seconds_of=manifest["files"][rel].get("fingerprint"))
    return seconds


def install_run(name):
    """The command that installs the engine into the Python that actually runs UniStudent (not whichever pip is first
    on PATH). An environment made by `uvx` has no pip, but `uv pip install --python` can fill it."""
    import importlib.util
    import sys
    package = PACKAGES.get(name, name)
    python = sys.executable
    if " " in python:  # quoted only if it must be; PowerShell needs the call operator before a quoted path (a POSIX shell must not get it)
        python = f'& "{python}"' if platform.system() == "Windows" else f'"{python}"'
    if importlib.util.find_spec("pip") is not None:
        return f"{python} -m pip install {package}"
    if shutil.which("uv"):
        return f'uv pip install --python "{sys.executable}" {package}' if " " in sys.executable \
            else f"uv pip install --python {sys.executable} {package}"  # a quoted argument is valid in every shell
    return "(install uv first: https://docs.astral.sh/uv/)"


def install_hint(name):
    return (f"Speech-to-text isn't installed. Run: {install_run(name)} "
            "For advanced users: or reinstall UniStudent with its 'stt' extra (uv tool install --force \"unistudent[stt] @ <repo>\").")


def _approved_file(course):
    return course.state / "approved-recordings.json"


def approved(course):
    try:
        return json.loads(_approved_file(course).read_text("utf-8"))
    except (FileNotFoundError, ValueError):
        return []


def approve(course, rels):
    """Record the recordings the student said yes to: `transcribe` runs only these."""
    known = recording_pages(course)
    unknown = [r for r in rels if r not in known]
    if unknown:
        raise UserError("Not a recording in this course: " + ", ".join(unknown))
    chosen = approved(course) + [r for r in rels if r not in approved(course)]
    _approved_file(course).parent.mkdir(parents=True, exist_ok=True)
    _approved_file(course).write_text(json.dumps(chosen, ensure_ascii=False), "utf-8")
    return chosen


def require_approved(course, rels):
    missing = [r for r in rels if r not in approved(course)]
    if missing:
        raise UserError("Not approved by the student: " + ", ".join(missing)
                        + ". Show the student the numbered list of recordings (full path, length, estimate), "
                        "then run `us recordings approve` with the ones they chose.")


def start_background(course, rels):
    """Run the transcription in a detached process; its log is in .unistudent/jobs/."""
    import sys
    jobs = course.state / "jobs"
    jobs.mkdir(parents=True, exist_ok=True)
    log = jobs / f"transcribe-{time.strftime('%Y%m%d-%H%M%S')}.log"
    package_root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, PYTHONPATH=str(package_root) + os.pathsep + os.environ.get("PYTHONPATH", ""))
    cmd = [sys.executable, "-m", "unistudent.cli", "recordings", "transcribe", "--course", str(course.root), *rels]
    kwargs = {"start_new_session": True} if os.name != "nt" else {"creationflags": 0x00000008}  # DETACHED_PROCESS
    with open(log, "w", encoding="utf-8") as handle:
        process = subprocess.Popen(cmd, stdout=handle, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                   env=env, **kwargs)
    return {"pid": process.pid, "log": str(log), "recordings": list(rels)}


def backend_name():
    forced = os.environ.get("UNISTUDENT_STT_BACKEND")
    if forced:
        return forced
    if platform.system() == "Darwin" and platform.machine() == "arm64":
        return "mlx"
    return "faster"


def backend_available(name):
    if name == "fake":
        return True
    module = {"mlx": "mlx_whisper", "faster": "faster_whisper"}[name]
    try:
        __import__(module)
        return True
    except ImportError:
        return False


def model_for(name, language, fast=False):
    if name == "fake":
        return "fake"
    return (fast and FAST_MODELS.get((name, language))) or MODELS.get((name, language)) or MODELS[(name, None)]


def _fast(course):
    return course.settings().get("transcription") == "fast"


def _require_ffmpeg():
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is needed for recordings. Install it (macOS: brew install ffmpeg; "
                           "Windows: winget install ffmpeg; Linux: your package manager).")


def extract_audio(path: Path, out: Path, start=None, seconds=None):
    _require_ffmpeg()
    cmd = ["ffmpeg", "-y", "-v", "error"]
    if start is not None:
        cmd += ["-ss", str(start)]
    cmd += ["-i", str(path)]
    if seconds is not None:
        cmd += ["-t", str(seconds)]
    cmd += ["-vn", "-ac", "1", "-ar", "16000", str(out)]
    subprocess.run(cmd, check=True)


# Quieter than speech for 30 s or more. Measured on a real 2.5 h lesson: 35 invented lines dropped (a 17-minute break
# of "Thank you." and one more), no real speech: a segment goes only when it lies wholly inside such a silence.
SILENCE = "silencedetect=noise=-40dB:d=30"


def silences(path: Path):
    """[(start, end)] in seconds of the long silences in a recording; [] when ffmpeg can't read it."""
    if not shutil.which("ffmpeg"):
        return []
    log = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-vn", "-af", SILENCE, "-f", "null", "-"],
                         capture_output=True, text=True, errors="replace").stderr
    starts = [float(t) for t in re.findall(r"silence_start: (-?[\d.]+)", log)]
    ends = [float(t) for t in re.findall(r"silence_end: ([\d.]+)", log)]
    return list(zip(starts, ends + [math.inf] * (len(starts) - len(ends))))  # a silence to the very end has no end line


def transcribe_audio(audio: Path, name: str, language: str, fast=False):
    """[(start, end, text)] from the chosen backend."""
    model = model_for(name, language, fast)
    if name == "fake":
        time.sleep(float(os.environ.get("UNISTUDENT_FAKE_STT_SECONDS", 0)))
        return [(t, t + 20, f"segment at {hms(t)}") for t in range(0, 150, 20)]
    if name == "mlx":
        import mlx_whisper
        # Not conditioning on the previous text stops Whisper's repetition loop over silence and the audio's end
        # (mlx has no VAD filter); measured on a lecture: no invented lines, three times faster.
        result = mlx_whisper.transcribe(str(audio), path_or_hf_repo=model, language=language,
                                        condition_on_previous_text=False)
        return [(s["start"], s["end"], s["text"].strip()) for s in result["segments"]]
    from faster_whisper import WhisperModel
    try:  # decoded here: faster-whisper's own reader fails with PyAV 19 (open() has no metadata_errors any more)
        import numpy  # installed with faster-whisper
        with wave.open(str(audio)) as pcm:
            sound = numpy.frombuffer(pcm.readframes(pcm.getnframes()), numpy.int16).astype(numpy.float32) / 32768
    except ImportError:
        sound = str(audio)

    def run(device):
        whisper = WhisperModel(model, device=device, compute_type="auto")
        segments, _ = whisper.transcribe(sound, language=language, vad_filter=True)
        return [(s.start, s.end, s.text.strip()) for s in segments]  # the work happens here, so its errors too
    try:
        return run("auto")
    except (RuntimeError, OSError) as error:  # an NVIDIA card without its CUDA libraries (cuBLAS, cuDNN)
        if not re.search(r"cuda|cublas|cudnn", str(error), re.I):
            raise
        print("This computer's graphics card is missing its CUDA libraries (cuBLAS, cuDNN), so transcription runs on "
              "the processor instead: slower, same result.", file=sys.stderr)
        return run("cpu")


def _benchmark_file():
    return home() / "benchmark.json"


SAMPLE_SECONDS = 60


def benchmark(course, rel):
    """Transcribe a short sample to measure this machine. Stores the real-time factor."""
    name = backend_name()
    source = material.path_of(course, rel)
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / "sample.wav"
        extract_audio(source, audio, start=0, seconds=SAMPLE_SECONDS)
        began = time.monotonic()
        transcribe_audio(audio, name, course.settings().get("language"))
        spent = time.monotonic() - began
    factor = spent / SAMPLE_SECONDS
    _save_speeds({**_speeds(), "backend": name, "realtime_factor": factor})
    return factor


ROUGH_REALTIME_FACTOR = {"mlx": 0.15, "faster": 0.5}  # hours of work per hour of audio, before anything is measured


def _speeds():
    try:
        return json.loads(_benchmark_file().read_text("utf-8"))
    except (FileNotFoundError, ValueError):
        return {}


def _save_speeds(data):
    _benchmark_file().parent.mkdir(parents=True, exist_ok=True)
    _benchmark_file().write_text(json.dumps(data), "utf-8")


def realtime_factor(course, fast=None):
    """(hours of work per hour of audio, measured?): from the transcripts this machine finished with this model, else
    the one-minute benchmark (made with the accurate model), else a rough guess. `fast`: the course's choice by default."""
    name, language = backend_name(), course.settings().get("language")
    fast = _fast(course) if fast is None else fast
    data = _speeds()
    done = data.get("transcripts", {}).get(model_for(name, language, fast))
    if done and done["audio"]:
        return done["spent"] / done["audio"], True
    speedup = FAST_SPEEDUP if model_for(name, language, fast) != model_for(name, language) else 1
    if data.get("realtime_factor") is not None:
        return data["realtime_factor"] / speedup, True
    return ROUGH_REALTIME_FACTOR.get(name, 0.5) / speedup, False


def _running_file(course):
    return course.state / "transcribing.json"


def transcribing(course):
    """The recording being transcribed right now: {path, started (HH:MM), minutes_left, elapsed}, or None."""
    try:
        job = json.loads(_running_file(course).read_text("utf-8"))
    except (FileNotFoundError, ValueError):
        return None
    elapsed = time.time() - job["started"]
    if elapsed > max(2 * job["expected"], 3600):  # ponytail: a job killed hard (a restart) leaves its file; stale by time
        return None
    return {"path": job["path"], "started": time.strftime("%H:%M", time.localtime(job["started"])),
            "minutes_left": max(0, round((job["expected"] - elapsed) / 60)), "elapsed": elapsed}


DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})|(\d{1,2})[./](\d{1,2})[./](\d{4})")


def oldest_first(course, rels):
    """Recordings in the order they were made: the last date in the name (a site title ends with it, 2026-07-16 or
    16.07.2026), else the file's time; the same day by the numbers in the name ("session 2" before "session 10")."""
    def key(rel):
        found = DATE.findall(Path(rel).name)
        if found:
            y, m, d, d2, m2, y2 = found[-1]
            day = f"{y or y2}-{int(m or m2):02d}-{int(d or d2):02d}"
        else:
            path = material.path_of(course, rel)
            day = time.strftime("%Y-%m-%d", time.localtime(path.stat().st_mtime)) if path.exists() else "9999"
        return day, [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", Path(rel).name)]
    return sorted(rels, key=key)


def listing(course, unit=None):
    rows = []
    pages = recording_pages(course)
    files, source_pages = course.manifest()["files"], course.read_state("wiki.json", {})
    now = transcribing(course)
    for rel in oldest_first(course, pages):
        info = pages[rel]
        if unit is not None and unit_dir(info["unit"]) != unit_dir(unit):
            continue
        path = material.path_of(course, rel)
        site = files[rel].get("site_url")  # files the lecturer hung on this recording on the course site
        attachments = [{"path": a, "page": source_pages.get(a, {}).get("page")}
                       for a, entry in files.items() if site and entry.get("attached_to") == site]
        rows.append({"path": rel, "unit": info["unit"], "processed": info["processed"],
                     "has_transcript": (course.wiki / info["folder"] / "transcript.md").exists(),
                     "transcribing": (now or {}).get("path") == rel,
                     "wiki_folder": info["folder"], "seconds": recording_seconds(course, rel),
                     "bytes": path.stat().st_size if path.exists() else None, "attachments": attachments})
    return rows


def estimate(course, unit=None):
    rows = [r for r in listing(course, unit) if not r["has_transcript"]]
    seconds = sum(r["seconds"] or 0 for r in rows)
    unknown = sum(1 for r in rows if r["seconds"] is None)
    size = sum(r["bytes"] or 0 for r in rows)
    factor, measured = realtime_factor(course)
    factor = factor if measured else None
    name = backend_name()
    offer = not _fast(course) and model_for(name, course.settings().get("language"), True) != \
        model_for(name, course.settings().get("language"))
    fast_factor = realtime_factor(course, fast=True)[0] if offer and factor else None
    # One vision call per ~PARAGRAPH_SECONDS segment (toc.md's row spacing): a separate,
    # explicit opt-in (ticket 04), never triggered just because a video-analysis tool is installed.
    segments = sum(math.ceil(r["seconds"] / PARAGRAPH_SECONDS) for r in rows if r["seconds"])
    return {
        "recordings": len(rows), "hours": round(seconds / 3600, 2), "unknown_duration": unknown,
        "gigabytes": round(size / 1e9, 2), "backend": name, "backend_installed": backend_available(name),
        "install_command": None if backend_available(name) else install_hint(name),
        "install_run": None if backend_available(name) else install_run(name),
        "realtime_factor": factor,
        "estimated_hours": round(seconds * factor / 3600, 2) if factor else None,
        "faster_option": {"estimated_hours": round(seconds * fast_factor / 3600, 2)} if fast_factor else None,
        "transcription": "fast" if _fast(course) else "accurate",
        "files": [r["path"] for r in rows],
        "frame_analysis_segments": segments,
        "frame_analysis": course.settings().get("frame_analysis"),
        "keep_video": course.settings().get("keep_video"),
    }


def write_transcript(course, rel, segments, name):
    info = recording_pages(course)[rel]
    folder = course.wiki / info["folder"]
    folder.mkdir(parents=True, exist_ok=True)
    source = material.path_of(course, rel)
    total = segments[-1][1] if segments else 0
    lines = ["---", f"source: {rel}", f"unit: {info['unit'] if info['unit'] is not None else 'unsorted'}",
             f"duration: {hms(total)}", f"backend: {name}", "---", "",
             f"# {Path(rel).name}: transcript", "",
             "Sources: " + video_link(course, rel, folder), ""]
    block_start, block = None, []
    for start, _, text in segments:
        if block_start is None or start - block_start >= PARAGRAPH_SECONDS:
            if block:
                lines += [f"## {hms(block_start)}", "", " ".join(block), ""]
            block_start, block = start, []
        block.append(f"[{hms(start)}] {text}")
    if block:
        lines += [f"## {hms(block_start)}", "", " ".join(block), ""]
    (folder / "transcript.md").write_text("\n".join(lines), "utf-8")
    vtt = _vtt(segments)
    (folder / "transcript.vtt").write_text(vtt, "utf-8")
    # A sidecar next to the video lets video players show this transcript as subtitles,
    # but only where the video lives in a folder the plugin owns.
    real = source.resolve()
    owned = [course.material.resolve()] + ([Path(course.settings()["recordings_dir"]).resolve()]
                                      if course.settings().get("recordings_dir") else [])
    if any(str(real).startswith(str(root) + os.sep) for root in owned):
        real.with_suffix(".vtt").write_text(vtt, "utf-8")
    return folder / "transcript.md"


def _vtt(segments):
    def stamp(seconds):
        ms = int(round((seconds - int(seconds)) * 1000))
        return f"{hms(seconds)}.{ms:03d}"
    lines = ["WEBVTT", ""]
    for start, end, text in segments:
        lines += [f"{stamp(start)} --> {stamp(end)}", text, ""]
    return "\n".join(lines)


def transcribe(course, rel):
    name = backend_name()
    if not backend_available(name):
        raise RuntimeError(install_hint(name))
    source = material.path_of(course, rel)
    seconds = recording_seconds(course, rel)
    _running_file(course).write_text(json.dumps({"path": rel, "started": time.time(),
                                                 "expected": (seconds or 0) * realtime_factor(course)[0]}), "utf-8")
    _write_progress(course)
    began = time.monotonic()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            audio = Path(tmp) / "audio.wav"
            if name == "fake":
                audio.write_bytes(b"")
            else:
                extract_audio(source, audio)
            segments = transcribe_audio(audio, name, course.settings().get("language"), _fast(course))
    finally:
        _running_file(course).unlink()
    if seconds:  # the time estimates follow this machine's real speed from now on
        data = _speeds()
        done = data.setdefault("transcripts", {}).setdefault(model_for(name, course.settings().get("language"), _fast(course)),
                                                             {"audio": 0, "spent": 0})
        done["audio"] += seconds
        done["spent"] += time.monotonic() - began
        _save_speeds(data)
    quiet = silences(source)  # Whisper invents text over a silent break ("Thank you." again and again): drop it
    segments = [s for s in segments if not any(a <= s[0] and s[1] <= b for a, b in quiet)]  # wholly inside only
    path = write_transcript(course, rel, segments, name)
    left = [r for r in approved(course) if r != rel]
    _approved_file(course).write_text(json.dumps(left, ensure_ascii=False), "utf-8")
    _write_progress(course)
    return path


def _write_progress(course):
    """Refresh the progress box file in the course folder, so the student sees it even when nobody pastes it."""
    from .fetch_plan import status
    try:
        status(course)
    except (OSError, ValueError, KeyError):
        pass  # the box is a courtesy: never let it stop a transcription


def audio_only_fetch(course):
    """Whether recordings are fetched with their sound only: nothing needs the video (no frame analysis) and the
    student chose not to keep it. Not asked yet means kept."""
    settings = course.settings()
    return not settings.get("frame_analysis") and settings.get("keep_video") is False


def keep_audio_only(course, rel):
    """Replace a recording's video, once its frame analysis is done, by an audio-only copy under the same name, so
    every time link to it still opens the right minute. Only when the student chose not to keep the video."""
    if course.settings().get("keep_video") is not False:
        raise UserError("The student keeps the video files (keep_video), so the video stays.")
    info = recording_pages(course).get(rel)
    if info is None:
        raise UserError(f"Not a recording in this course: {rel}")
    if not info["processed"]:
        raise UserError(f"{rel} has no summary yet: replace its video only once its analysis is done.")
    _require_ffmpeg()
    source = material.path_of(course, rel)
    with tempfile.TemporaryDirectory(dir=source.parent) as tmp:  # same disk, so the swap is one rename
        audio = Path(tmp) / source.name
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(source), "-vn", "-c:a", "copy", str(audio)], check=True)
        os.replace(audio, source)
    return rel


FRAME_WIDTH = 1280  # a 720p lesson's own width: its whiteboard handwriting reads well at it (checked on a real lesson)
TIME = re.compile(r"^\d{1,2}:\d{2}:\d{2}(\.\d+)?$")


def frames(course, rel, times):
    """The screen of a recording at these times (HH:MM:SS), as JPEG files at most FRAME_WIDTH wide. They wait in the
    Hidden folder until the recording's summary is written: the next Wiki build deletes them (a frame can show the
    lecturer's private screen)."""
    info = recording_pages(course).get(rel)
    if info is None:
        raise UserError(f"Not a recording in this course: {rel}")
    bad = [t for t in times if not TIME.match(t)]
    if bad or not times:
        raise UserError("Give each time as HH:MM:SS (for example 00:12:30), not: " + ", ".join(bad or ["nothing"]))
    _require_ffmpeg()
    source = material.path_of(course, rel)
    folder = course.state / "frames" / Path(info["folder"]).name
    folder.mkdir(parents=True, exist_ok=True)
    images = []
    for at in times:
        target = folder / (at.replace(":", "") + ".jpg")
        if target.exists():
            target.unlink()
        result = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", at, "-i", str(source), "-frames:v", "1",
                                 "-vf", f"scale='min({FRAME_WIDTH},iw)':-2", "-q:v", "4", str(target)],
                                capture_output=True, text=True)
        if not target.is_file():
            raise UserError(f"No picture at {at} in {rel}: " + (
                "the recording has sound only." if "does not contain any stream" in result.stderr
                else "the time may be past its end."))
        images.append(str(target.resolve()))
    return images


def fetch_streams(listing_path, folder, audio_only=False):
    """Download every recording in a university plugin's listing that has a stream URL
    (e.g. HLS) and no file yet. Stream tokens expire, so this runs right after the listing."""
    from .course import safe_name
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is needed to download recordings. Install it (macOS: brew install ffmpeg; "
                           "Windows: winget install ffmpeg; Linux: your package manager).")
    listing_path, folder = Path(listing_path), Path(folder)
    data = json.loads(listing_path.read_text("utf-8"))
    downloaded, failed, reasons = [], [], {}
    for item in data.get("items", []):
        if item.get("kind") != "recording" or not item.get("stream_url") or item.get("file"):
            continue
        stem = safe_name(item.get("name") or "recording")
        if Path(stem).suffix.lower() in RECORDINGS:  # only a real media suffix: "Lesson 3 12.10.2025" keeps its year
            stem = Path(stem).stem
        name = stem + (".m4a" if audio_only else ".mp4")
        target = folder / name
        part = folder / (name + ".part" + target.suffix)
        cmd = ["ffmpeg", "-y", "-v", "error", "-i", item["stream_url"]]
        cmd += ["-vn", "-c:a", "aac"] if audio_only else ["-c", "copy"]
        cmd += [str(part)]
        result = subprocess.run(cmd, capture_output=True)
        if result.returncode == 0 and part.exists() and part.stat().st_size > 0:
            os.replace(part, target)
            item["file"], item["name"] = name, name
            downloaded.append(name)
        else:
            if part.exists():
                part.unlink()
            failed.append(item.get("name") or item["url"])
            error = result.stderr.decode("utf-8", "replace").strip().splitlines()
            reasons[failed[-1]] = (error[-1].replace(item["stream_url"], "<link>") if error
                                   else f"ffmpeg exit code {result.returncode}")  # the link holds a token
    listing_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
    return {"downloaded": downloaded, "failed": failed, "reasons": reasons}

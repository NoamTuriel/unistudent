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
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from . import material
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
            "(or reinstall UniStudent with its 'stt' extra: uv tool install --force \"unistudent[stt] @ <repo>\").")


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


def model_for(name, language):
    return MODELS.get((name, language)) or MODELS[(name, None)] if name != "fake" else "fake"


def extract_audio(path: Path, out: Path, start=None, seconds=None):
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is needed for recordings. Install it (macOS: brew install ffmpeg; "
                           "Windows: winget install ffmpeg; Linux: your package manager).")
    cmd = ["ffmpeg", "-y", "-v", "error"]
    if start is not None:
        cmd += ["-ss", str(start)]
    cmd += ["-i", str(path)]
    if seconds is not None:
        cmd += ["-t", str(seconds)]
    cmd += ["-vn", "-ac", "1", "-ar", "16000", str(out)]
    subprocess.run(cmd, check=True)


def transcribe_audio(audio: Path, name: str, language: str):
    """[(start, end, text)] from the chosen backend."""
    model = model_for(name, language)
    if name == "fake":
        return [(t, t + 20, f"segment at {hms(t)}") for t in range(0, 150, 20)]
    if name == "mlx":
        import mlx_whisper
        result = mlx_whisper.transcribe(str(audio), path_or_hf_repo=model, language=language)
        return [(s["start"], s["end"], s["text"].strip()) for s in result["segments"]]
    from faster_whisper import WhisperModel
    whisper = WhisperModel(model, device="auto", compute_type="auto")
    segments, _ = whisper.transcribe(str(audio), language=language, vad_filter=True)
    return [(s.start, s.end, s.text.strip()) for s in segments]


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
    _benchmark_file().parent.mkdir(parents=True, exist_ok=True)
    _benchmark_file().write_text(json.dumps({"backend": name, "realtime_factor": factor}), "utf-8")
    return factor


def listing(course, unit=None):
    rows = []
    for rel, info in recording_pages(course).items():
        if unit is not None and unit_dir(info["unit"]) != unit_dir(unit):
            continue
        path = material.path_of(course, rel)
        rows.append({"path": rel, "unit": info["unit"], "processed": info["processed"],
                     "has_transcript": (course.wiki / info["folder"] / "transcript.md").exists(),
                     "wiki_folder": info["folder"], "seconds": duration(path),
                     "bytes": path.stat().st_size if path.exists() else None})
    return rows


def estimate(course, unit=None):
    rows = [r for r in listing(course, unit) if not r["has_transcript"]]
    seconds = sum(r["seconds"] or 0 for r in rows)
    unknown = sum(1 for r in rows if r["seconds"] is None)
    size = sum(r["bytes"] or 0 for r in rows)
    try:
        factor = json.loads(_benchmark_file().read_text("utf-8"))["realtime_factor"]
    except (FileNotFoundError, KeyError, ValueError):
        factor = None
    name = backend_name()
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
        "files": [r["path"] for r in rows],
        "frame_analysis_segments": segments,
        "frame_analysis": course.settings().get("frame_analysis"),
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
    # A sidecar next to the video lets video tools (e.g. mcp-video-analyzer) use this transcript,
    # but only where the video lives in a folder the plugin owns.
    real = source.resolve()
    owned = [(course.raw if course.legacy else course.material).resolve()] + ([Path(course.settings()["recordings_dir"]).resolve()]
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
    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / "audio.wav"
        if name == "fake":
            audio.write_bytes(b"")
        else:
            extract_audio(source, audio)
        segments = transcribe_audio(audio, name, course.settings().get("language"))
    return write_transcript(course, rel, segments, name)


def fetch_streams(listing_path, folder, audio_only=False):
    """Download every recording in a university plugin's listing that has a stream URL
    (e.g. HLS) and no file yet. Stream tokens expire, so this runs right after the listing."""
    from .course import safe_name
    if not shutil.which("ffmpeg"):
        raise RuntimeError("ffmpeg is needed to download recordings. Install it (macOS: brew install ffmpeg; "
                           "Windows: winget install ffmpeg; Linux: your package manager).")
    listing_path, folder = Path(listing_path), Path(folder)
    data = json.loads(listing_path.read_text("utf-8"))
    downloaded, failed = [], []
    for item in data.get("items", []):
        if item.get("kind") != "recording" or not item.get("stream_url") or item.get("file"):
            continue
        stem = Path(safe_name(item.get("name") or "recording")).stem
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
    listing_path.write_text(json.dumps(data, ensure_ascii=False, indent=1), "utf-8")
    return {"downloaded": downloaded, "failed": failed}

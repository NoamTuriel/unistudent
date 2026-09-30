"""Making links instead of copies (ADR 0003).

The only OS-specific part of the layout code. Strategy, in order:
symlink → (Windows) hard link for files / junction for folders → give up (caller writes an index page).
Set UNISTUDENT_LINK_MODE=index to force the index-page fallback.
"""
import os
import subprocess
import sys
from pathlib import Path


def link_mode():
    return os.environ.get("UNISTUDENT_LINK_MODE", "auto")


def is_linked_to(link: Path, target: Path) -> bool:
    try:
        return link.exists() and os.path.samefile(link, target)
    except OSError:
        return False


def make_link(target: Path, link: Path) -> bool:
    """Make `link` point at `target`. Returns False when no kind of link is possible."""
    target = Path(target)
    link = Path(link)
    if link_mode() == "index":
        return False
    if is_linked_to(link, target):
        return True
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.exists():
        remove_link(link)  # a stale link we own; real files are never passed here
    try:
        os.symlink(target, link, target_is_directory=target.is_dir())
        return True
    except (OSError, NotImplementedError):
        pass
    if sys.platform == "win32":
        if target.is_dir():
            result = subprocess.run(["cmd", "/c", "mklink", "/J", str(link), str(target)],
                                    capture_output=True)
            return result.returncode == 0
        try:
            os.link(target, link)  # hard link: same volume only, no admin rights needed
            return True
        except OSError:
            return False
    return False


SYNCED_MARKERS = ("mobile documents", "icloud", "google drive", "googledrive", "my drive",
                  "dropbox", "onedrive", "box sync")


def is_synced_folder(path: Path) -> bool:
    """iCloud, Google Drive, Dropbox and OneDrive don't carry links reliably and evict big files."""
    return any(marker in part.lower() for part in Path(path).parts for marker in SYNCED_MARKERS)


def recordings_root() -> Path:
    """Where recordings of synced course folders live: local, never synced."""
    return Path(os.environ.get("UNISTUDENT_RECORDINGS_ROOT") or Path.home() / "UniStudent recordings")


def remove_link(link: Path) -> None:
    """Remove a link the plugin made. Never follows it."""
    link = Path(link)
    if link.is_symlink() or link.is_file():
        link.unlink()
    elif link.is_dir():  # junction on Windows
        os.rmdir(link)

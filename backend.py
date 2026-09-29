"""
backend.py - logika konverzije MP4 -> MP3.

Koristi FFmpeg. Traži ga prvo u sistemskom PATH-u, a ako ga nema,
koristi ugrađenu binarku iz paketa `imageio-ffmpeg` (pip install imageio-ffmpeg).
"""

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

SUPPORTED_EXTENSIONS = {".mp4", ".m4v", ".mov", ".mkv", ".avi", ".webm", ".flv"}
BITRATES = [96, 128, 192, 256, 320]
DEFAULT_BITRATE = 192


class ConversionError(Exception):
    """Greška tijekom konverzije."""


class ConversionCancelled(Exception):
    """Korisnik je prekinuo konverziju."""


def find_ffmpeg() -> Optional[str]:
    """Vraća putanju do ffmpeg-a ili None ako ga nema."""
    path = shutil.which("ffmpeg")
    if path:
        return path
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


def _popen_flags() -> int:
    # Na Windowsu sprječava da se pojavi crni CMD prozor.
    if sys.platform == "win32":
        return subprocess.CREATE_NO_WINDOW
    return 0


def is_supported(path) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_EXTENSIONS


def get_duration(ffmpeg: str, input_path) -> float:
    """Trajanje u sekundama (0.0 ako se ne može pročitati)."""
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(input_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=_popen_flags(),
    )
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", result.stderr)
    if not match:
        return 0.0
    h, m, s = match.groups()
    return int(h) * 3600 + int(m) * 60 + float(s)


def unique_path(path: Path) -> Path:
    """Ako datoteka već postoji, dodaje (1), (2), ... da se ništa ne prepiše."""
    if not path.exists():
        return path
    i = 1
    while True:
        candidate = path.with_name(f"{path.stem} ({i}){path.suffix}")
        if not candidate.exists():
            return candidate
        i += 1


def build_output_path(input_path, output_dir=None) -> Path:
    input_path = Path(input_path)
    folder = Path(output_dir) if output_dir else input_path.parent
    return unique_path(folder / f"{input_path.stem}.mp3")


def convert(
    ffmpeg: str,
    input_path,
    output_path,
    bitrate: int = DEFAULT_BITRATE,
    on_progress: Optional[Callable[[int], None]] = None,
    should_cancel: Optional[Callable[[], bool]] = None,
) -> Path:
    """
    Pretvara jednu datoteku u MP3.

    on_progress(postotak 0-100) se poziva tijekom konverzije.
    should_cancel() -> True prekida konverziju (baca ConversionCancelled).
    Vraća putanju do nastale MP3 datoteke.
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.is_file():
        raise ConversionError(f"Datoteka ne postoji: {input_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    duration = get_duration(ffmpeg, input_path)

    cmd = [
        ffmpeg,
        "-hide_banner",
        "-nostdin",
        "-y",
        "-i", str(input_path),
        "-vn",                      # bez videa
        "-c:a", "libmp3lame",
        "-b:a", f"{bitrate}k",
        "-progress", "pipe:1",      # napredak na stdout
        "-nostats",
        str(output_path),
    ]

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,   # spajamo stderr da nema deadlocka
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=_popen_flags(),
    )

    last_lines = []
    last_percent = -1

    try:
        for line in process.stdout:
            line = line.strip()
            if not line:
                continue

            if should_cancel and should_cancel():
                process.terminate()
                process.wait()
                _remove_quietly(output_path)
                raise ConversionCancelled()

            last_lines.append(line)
            last_lines = last_lines[-15:]

            if duration > 0 and on_progress and line.startswith("out_time_us="):
                try:
                    seconds = int(line.split("=", 1)[1]) / 1_000_000
                except ValueError:
                    continue
                percent = max(0, min(99, int(seconds / duration * 100)))
                if percent != last_percent:
                    last_percent = percent
                    on_progress(percent)

        process.wait()
    except ConversionCancelled:
        raise
    except Exception:
        process.kill()
        _remove_quietly(output_path)
        raise

    if process.returncode != 0:
        _remove_quietly(output_path)
        details = "\n".join(
            l for l in last_lines if "=" not in l or " " in l.split("=", 1)[0]
        )
        raise ConversionError(details or f"FFmpeg je završio s kodom {process.returncode}")

    if on_progress:
        on_progress(100)
    return output_path


def _remove_quietly(path: Path) -> None:
    try:
        if path.exists():
            os.remove(path)
    except OSError:
        pass

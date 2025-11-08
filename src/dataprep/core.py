# src/dataprep/core.py
from __future__ import annotations
import csv, json, shutil, subprocess, re
from pathlib import Path
from typing import Optional, List

# ------------------------------------------------------------
# Utilities
# ------------------------------------------------------------

def _which(name: str) -> str:
    """
    Find an executable on PATH (Windows-friendly).
    Raises a helpful error if missing.
    """
    p = shutil.which(name) or shutil.which(f"{name}.exe")
    if not p:
        raise RuntimeError(f"{name} not found in PATH.")
    return p

def _ensure_dir(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p

# PySceneDetect CSV usually has these headers:
#   "Scene Number","Start Timecode","Start Frame","Start Time (seconds)",
#   "End Timecode","End Frame","End Time (seconds)","Length (frames)","Length (seconds)"
START_KEYS = ("Start Timecode", "Start", "Start Time")
END_KEYS   = ("End Timecode", "End", "End Time")

def _pick_col(row_keys: List[str], candidates: tuple[str, ...]) -> str:
    """Choose the first header present (case-insensitive) from candidates."""
    lower_map = {k.lower(): k for k in row_keys}
    for cand in candidates:
        if cand.lower() in lower_map:
            return lower_map[cand.lower()]
    raise KeyError(f"None of {candidates} present in CSV headers: {row_keys}")

_tc_re = re.compile(r"^(?P<h>\d{1,2}):(?P<m>\d{2}):(?P<s>\d{2})(?:\.(?P<ms>\d{1,3}))?$")
def _norm_tc(tc: str) -> str:
    """
    Normalize timecode to HH:MM:SS(.mmm) for ffmpeg/mkvmerge.
    Keeps milliseconds if provided; zero-pads to 3 digits.
    """
    tc = tc.strip()
    m = _tc_re.match(tc)
    if not m:
        return tc  # let ffmpeg try to parse it
    h = int(m.group("h")); mi = int(m.group("m")); s = int(m.group("s"))
    ms = m.group("ms")
    return f"{h:02d}:{mi:02d}:{s:02d}" if ms is None else f"{h:02d}:{mi:02d}:{s:02d}.{int(ms):03d}"

# ------------------------------------------------------------
# Public API (matches your cli.main imports)
# ------------------------------------------------------------

def find_latest_mkv(sources_dir: Path = Path("data/sources")) -> Path:
    """
    Return the newest .mkv under data/sources (recursively).
    """
    files = sorted(
        (p for p in sources_dir.rglob("*.mkv") if p.is_file()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not files:
        raise FileNotFoundError(f"No .mkv files found under {sources_dir}")
    return files[0]

def detect_scenes(
    inp: Path,
    outdir: Optional[Path] = None,
    mode: str = "adaptive",
    threshold: Optional[int] = None
) -> Path:
    """
    Run PySceneDetect and write one CSV.
    NOTE: PySceneDetect 0.6.7.1 uses: `list-scenes -o <file.csv>`
          (no `--csv` flag, no `--format` flag).
    """
    sd = _which("scenedetect")

    # Derive movie name & output locations
    stem = inp.stem
    movie_name = inp.parent.name if inp.parent.name != "sources" else stem
    out_root = (outdir or Path("data/scenedetect") / movie_name)
    out_root.mkdir(parents=True, exist_ok=True)

    # We choose one explicit CSV file to be stable for downstream steps
    csv_out = out_root / f"{movie_name}-Scenes.csv"

    # Build the CLI: scenedetect -i <mkv> detect-<mode> list-scenes -o <csv_out>
    cmd = [sd, "-i", str(inp)]
    if mode == "content":
        cmd += ["detect-content"]
        if threshold is not None:
            cmd += ["--threshold", str(threshold)]
    else:
        cmd += ["detect-adaptive"]

    cmd += ["list-scenes", "-o", str(csv_out)]

    # Run and return the CSV path
    subprocess.run(cmd, check=True)
    return csv_out

# --- robust CSV open with retries (Windows-friendly) -------------------------
import time

def _open_csv_read(path: Path, retries: int = 10, delay: float = 0.5):
    """
    Try opening `path` for reading with a few retries.
    Common Windows case: file is momentarily locked by another process (Excel/AV).
    """
    last_err = None
    for _ in range(retries):
        try:
            # newline='' is required for csv module; utf-8 handles PySceneDetect output.
            return path.open("r", newline="", encoding="utf-8", errors="replace")
        except PermissionError as e:
            last_err = e
            time.sleep(delay)
    # If we’re still here, surface a helpful message.
    raise PermissionError(
        f"Could not open CSV (locked?): {path}\n"
        f"Close any editors (Excel/Notepad) and retry."
    ) from last_err

def _rows_from_csv(csv_path: Path) -> list[dict]:
    with _open_csv_read(csv_path) as f:
        return list(csv.DictReader(f))

def _timestamps_from_csv(csv_path: Path, out_ts: Path) -> None:
    with _open_csv_read(csv_path) as f, out_ts.open("w", encoding="utf-8") as g:
        r = csv.DictReader(f)
        for row in r:
            g.write(f"{row['Start Time']} - {row['End Time']}\n")


def _mk_mkvmerge_parts_spec(rows: list[dict]) -> str:
    """
    Build mkvmerge `--split parts:` spec:
      "HH:MM:SS.mmm-HH:MM:SS.mmm,HH:MM:SS-HH:MM:SS,..."
    """
    return ",".join(f"{r['start']}-{r['end']}" for r in rows)

def split_with_mkvmerge(inp: Path, csv_path: Path, outdir: Path) -> None:
    """
    Split using MKVToolNix. This uses `--split parts:` (scene ranges), and
    writes files as scene-0001.mkv, scene-0002.mkv, ...
    """
    _ensure_dir(outdir)
    rows = _rows_from_csv(csv_path)
    if not rows:
        raise ValueError(f"No scenes found in {csv_path}")

    mkvmerge = _which("mkvmerge")
    # mkvmerge will name parts like output-001.mkv; we point to a base then rename.
    base = outdir / "segments.mkv"
    parts = _mk_mkvmerge_parts_spec(rows)
    cmd = [
        mkvmerge, "-o", str(base),
        "--split", f"parts:{parts}",
        str(inp),
    ]
    subprocess.run(cmd, check=True)

    # Rename produced files to scene-0001.mkv pattern
    produced = sorted(outdir.glob("segments-*.mkv")) or sorted(outdir.glob("*.mkv"))
    for i, p in enumerate(produced, start=1):
        target = outdir / f"scene-{i:04d}.mkv"
        if target.exists():
            target.unlink()
        p.rename(target)

def split_with_ffmpeg(inp: Path, csv_path: Path, outdir: Path, copy: bool = True) -> None:
    """
    Split using FFmpeg per row (range start→end):
      • copy=True  → -c copy (fast; keyframe-aligned)
      • copy=False → re-encode (frame-accurate; libx264/aac defaults)
    Names files scene-00001.mkv (5-digit padding to keep sort order stable).
    """
    _ensure_dir(outdir)
    rows = _rows_from_csv(csv_path)
    if not rows:
        raise ValueError(f"No scenes found in {csv_path}")

    ff = _which("ffmpeg")
    for i, r in enumerate(rows, start=1):
        start, end = r["start"], r["end"]
        out = outdir / f"{i:05d}.mkv"
        cmd = [ff, "-hide_banner", "-loglevel", "error", "-y",
               "-ss", start, "-to", end, "-i", str(inp)]
        cmd += (["-c", "copy"] if copy else
                ["-c:v","libx264","-preset","veryfast","-crf","18","-c:a","aac","-b:a","192k"])
        cmd.append(str(out))
        subprocess.run(cmd, check=True)

def stage_review(clips_dir: Path, review_root: Path = Path("data/review")) -> Path:
    """
    Create a review workspace:
      data/review/<clips_dir.name>/{keep,reject}/ + manifest.csv (file,duration_s)
    Includes both .mkv and .mp4 clips.
    """
    base = review_root / clips_dir.name
    _ensure_dir(base / "keep")
    _ensure_dir(base / "reject")

    manifest = base / "manifest.csv"
    ffprobe = _which("ffprobe")
    clips = sorted([*clips_dir.glob("*.mkv"), *clips_dir.glob("*.mp4")])

    with manifest.open("w", newline='', encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["file", "duration_s"])
        for clip in clips:
            out = subprocess.check_output([
                ffprobe, "-v", "error",
                "-show_entries", "format=duration",
                "-of", "json",
                "-i", str(clip)
            ])
            dur = float(json.loads(out)["format"]["duration"])
            w.writerow([clip.name, round(dur, 3)])

    return base

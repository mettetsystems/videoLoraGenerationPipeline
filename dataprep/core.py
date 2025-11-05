from __future__ import annotations
import csv, json, shutil, subprocess
from pathlib import Path

def _which(name: str) -> str:
    p = shutil.which(name) or shutil.which(f"{name}.exe")
    if not p:
        raise RuntimeError(f"{name} not found in PATH.")
    return p

def rip_makemkv(out: Path, disc: str = "0", minlength_s: int = 1200) -> None:
    out.mkdir(parents=True, exist_ok=True)
    cmd = [
        _which("makemkvcon"), "mkv", f"disc:{disc}", "all", str(out),
        f"--minlength={minlength_s}", "--progress=-stdout"
    ]
    subprocess.run(cmd, check=True)

def detect_scenes(inp: Path, outdir: Path | None = None, mode: str = "adaptive", threshold: int | None = None) -> Path:
    sd = _which("scenedetect")
    stem = inp.stem
    outdir = outdir or Path("data/scenedetect")/stem
    outdir.mkdir(parents=True, exist_ok=True)
    cmd = [sd, "-i", str(inp)]
    if mode == "content":
        cmd += ["detect-content"]
        if threshold is not None:
            cmd += ["--threshold", str(threshold)]
    else:
        cmd += ["detect-adaptive"]
    cmd += ["list-scenes","--format","csv","-o",str(outdir)]
    subprocess.run(cmd, check=True)
    return outdir

def _timestamps_from_csv(csv_path: Path, out_ts: Path) -> None:
    with csv_path.open(newline='') as f, out_ts.open("w") as g:
        r = csv.DictReader(f)
        for row in r:
            g.write(f"{row['Start Time']} - {row['End Time']}\n")

def split_with_mkvmerge(inp: Path, csv_path: Path, outdir: Path) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    tsfile = outdir / f"{inp.stem}.timestamps.txt"
    _timestamps_from_csv(csv_path, tsfile)
    cmd = [_which("mkvmerge"), "-o", str(outdir / "%d.mkv"),
           "--split", f"timestamps:{tsfile}", str(inp)]
    subprocess.run(cmd, check=True)

def split_with_ffmpeg(inp: Path, csv_path: Path, outdir: Path, copy: bool = True) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    rows = list(csv.DictReader(csv_path.open(newline='')))
    ff = _which("ffmpeg")
    for i, row in enumerate(rows, start=1):
        start, end = row["Start Time"], row["End Time"]
        out = outdir / f"{i:05d}.mkv"
        cmd = [ff, "-hide_banner", "-loglevel", "error", "-y", "-ss", start, "-to", end, "-i", str(inp)]
        cmd += (["-c","copy"] if copy else ["-c:v","libx264","-preset","veryfast","-crf","18","-c:a","aac","-b:a","192k"])
        cmd.append(str(out))
        subprocess.run(cmd, check=True)

def stage_review(clips_dir: Path, review_root: Path = Path("data/review")) -> Path:
    base = review_root / clips_dir.name
    (base/"keep").mkdir(parents=True, exist_ok=True)
    (base/"reject").mkdir(parents=True, exist_ok=True)
    manifest = base / "manifest.csv"
    ffprobe = _which("ffprobe")
    import csv as _csv
    with manifest.open("w", newline='') as f:
        w = _csv.writer(f); w.writerow(["file","duration_s"])
        for clip in sorted(clips_dir.glob("*.mkv")):
            out = subprocess.check_output([ffprobe,"-v","error","-show_entries","format=duration","-of","json","-i",str(clip)])
            dur = float(json.loads(out)["format"]["duration"])
            w.writerow([clip.name, round(dur,3)])
    return base

#!/usr/bin/env python3
"""
Idempotent bootstrap for wan21-lora-dataprep.
Creates repo skeleton, .gitkeep files, pyproject, CLI entrypoint, and script stubs.
Safe to run multiple times.
"""
from pathlib import Path
import stat

ROOT = Path(__file__).parent

DIRS = [
    "configs",
    "dataprep",
    "scripts",
    "cli",
    "data",
    "data/sources",
    "data/scenedetect",
    "data/clips",
    "data/review",
]

FILES = {
    ".env.example": "DATA_ROOT=./data\n",
    ".gitignore": "\n".join([
        "__pycache__/",
        ".venv/",
        ".env",
        "*.pyc",
        "*.pyo",
        "*.pyd",
        ".Python",
        "build/",
        "dist/",
        "*.egg-info/",
        ".DS_Store",
        # keep structure but ignore big binaries by default (you can tweak)
        "data/sources/*",
        "data/clips/*",
        "data/scenedetect/*",
        "data/review/*",
        "!data/**/.gitkeep",
    ]) + "\n",
    "README.md": "# wan21-lora-dataprep\n\nHybrid pipeline: standalone scripts + Typer CLI.\n",
    "configs/dvd_job.example.yaml": "\n".join([
        "source_disc: 0",
        "minlength_seconds: 1200",
        "input_title: title_t00.mkv",
        "scenedetect:",
        "  mode: adaptive",
        "  threshold: null",
        ""
    ]),
    "pyproject.toml": "\n".join([
        "[project]",
        'name = "wan21-lora-dataprep"',
        'version = "0.1.0"',
        'requires-python = ">=3.10"',
        "dependencies = [",
        '  "typer[all]>=0.12",',
        '  "rich>=13.7",',
        '  "pyyaml>=6.0.1",',
        '  "pandas>=2.2",',
        '  "scenedetect==0.6.*"',
        "]",
        "",
        "[project.scripts]",
        'wan21-dp = "cli.main:app"',
        "",
        "[build-system]",
        'requires = ["setuptools>=61.0"]',
        'build-backend = "setuptools.build_meta"',
        ""
    ]),
    "dataprep/__init__.py": "",
    "dataprep/core.py": r'''from __future__ import annotations
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
''',
    "cli/main.py": r'''from pathlib import Path
import typer
from dataprep.core import rip_makemkv, detect_scenes, split_with_mkvmerge, split_with_ffmpeg, stage_review

app = typer.Typer(help="WAN 2.1 LoRA data-prep CLI")

@app.command()
def rip(out: str = "data/sources", disc: str = "0", minlength: int = 1200):
    rip_makemkv(Path(out), disc, minlength)

@app.command()
def scenes(inp: str, outdir: str | None = None, mode: str = "adaptive", threshold: int | None = None):
    detect_scenes(Path(inp), Path(outdir) if outdir else None, mode, threshold)

@app.command()
def split(inp: str, csv_path: str, outdir: str, engine: str = "mkvmerge", copy: bool = True):
    if engine == "mkvmerge":
        split_with_mkvmerge(Path(inp), Path(csv_path), Path(outdir))
    else:
        split_with_ffmpeg(Path(inp), Path(csv_path), Path(outdir), copy)

@app.command()
def review(clips_dir: str, review_root: str = "data/review"):
    stage_review(Path(clips_dir), Path(review_root))

if __name__ == "__main__":
    app()
''',
    "scripts/detect_scenes.py": r'''#!/usr/bin/env python3
import argparse
from pathlib import Path
from dataprep.core import detect_scenes
p = argparse.ArgumentParser(description="Run PySceneDetect and save CSV.")
p.add_argument("--input", required=True)
p.add_argument("--outdir")
p.add_argument("--mode", choices=["adaptive","content"], default="adaptive")
p.add_argument("--threshold", type=int)
a = p.parse_args()
out = detect_scenes(Path(a.input), Path(a.outdir) if a.outdir else None, a.mode, a.threshold)
print(f"CSV in: {out}")
''',
    "scripts/split_from_csv.py": r'''#!/usr/bin/env python3
import argparse
from pathlib import Path
from dataprep.core import split_with_mkvmerge, split_with_ffmpeg
p = argparse.ArgumentParser(description="Split by PySceneDetect CSV.")
p.add_argument("--input", required=True)
p.add_argument("--csv", required=True)
p.add_argument("--outdir", required=True)
p.add_argument("--engine", choices=["mkvmerge","ffmpeg"], default="mkvmerge")
p.add_argument("--copy", action="store_true")
a = p.parse_args()
if a.engine == "mkvmerge":
    split_with_mkvmerge(Path(a.input), Path(a.csv), Path(a.outdir))
else:
    split_with_ffmpeg(Path(a.input), Path(a.csv), Path(a.outdir), copy=a.copy)
''',
    "scripts/stage_review.py": r'''#!/usr/bin/env python3
import argparse
from pathlib import Path
from dataprep.core import stage_review
p = argparse.ArgumentParser(description="Prepare keep/reject and manifest.")
p.add_argument("--clips_dir", required=True)
p.add_argument("--review_root", default="data/review")
a = p.parse_args()
base = stage_review(Path(a.clips_dir), Path(a.review_root))
print(f"Review ready: {base}")
''',
    "scripts/rip_makemkv.sh": "#!/usr/bin/env bash\nset -euo pipefail\nout=${1:-data/sources}\ndisc=${2:-0}\nminlen=${3:-1200}\nmakemkvcon mkv disc:${disc} all \"$out\" --minlength=${minlen} --progress=-stdout\n",
    "scripts/rip_makemkv.ps1": 'param([string]$Out="data/sources",[string]$Disc="0",[int]$MinLen=1200)\n& makemkvcon.exe mkv \"disc:$Disc\" all $Out --minlength=$MinLen --progress=-stdout\n',
    "Makefile": "\n".join([
        "PY=python",
        "",
        "init:",
        "\t$(PY) bootstrap_init.py",
        "",
        "install:",
        "\tpython -m venv .venv && . .venv/bin/activate || .venv\\Scripts\\activate && pip install -U pip && pip install -e .",
        "",
        "# Usage: make scenes MKV=path/to.mkv",
        "scenes:",
        "\t$(PY) scripts/detect_scenes.py --input $(MKV)",
        "",
        "# Usage: make split MKV=... CSV=... OUT=...",
        "split:",
        "\t$(PY) scripts/split_from_csv.py --input $(MKV) --csv $(CSV) --outdir $(OUT) --engine mkvmerge",
        "",
        "# Usage: make review CLIPS=path/to/dir",
        "review:",
        "\t$(PY) scripts/stage_review.py --clips_dir $(CLIPS)",
        "",
        "lint:",
        "\t@echo \"(optional) add ruff/black here\"",
        ""
    ])
}

def ensure_dirs():
    for d in DIRS:
        p = ROOT / d
        p.mkdir(parents=True, exist_ok=True)
        # add .gitkeep to data subdirs so Git tracks them empty
        if p.parts[:1] == ("data",) or "data" in p.parts:
            (p / ".gitkeep").touch(exist_ok=True)

def ensure_files():
    for rel, content in FILES.items():
        f = ROOT / rel
        if not f.exists():
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(content, encoding="utf-8")
            # mark scripts executable on POSIX
            if f.suffix in {".sh", ""} and "scripts" in f.parts:
                f.chmod(f.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

def main():
    ensure_dirs()
    ensure_files()
    print("✅ Bootstrap complete. You can now run:")
    print("   1) python -m venv .venv && source .venv/bin/activate  # or .venv\\Scripts\\activate on Windows")
    print("   2) pip install -e .")
    print("   3) wan21-dp --help  (or use scripts/* directly)")

if __name__ == "__main__":
    main()

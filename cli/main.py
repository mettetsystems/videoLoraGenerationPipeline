from pathlib import Path
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

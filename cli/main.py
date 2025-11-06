from pathlib import Path
import typer
from typing import Optional
from dataprep.core import (
    find_latest_mkv, detect_scenes,
    split_with_mkvmerge, split_with_ffmpeg,
    stage_review
)

app = typer.Typer(help="WAN 2.1 LoRA data-prep (Scenes → Split → Review)")

@app.command()
def scenes(
    inp: Optional[str] = typer.Option(None, help="Input MKV path"),
    outdir: Optional[str] = typer.Option(None, help="Output dir for scene CSV"),
    mode: str = typer.Option("adaptive", help="adaptive|content"),
    threshold: Optional[int] = typer.Option(None, help="content threshold"),
    auto_latest: bool = typer.Option(False, help="Use newest MKV under data/sources/")
):
    """Generate scene CSV using PySceneDetect."""
    mkv = Path(inp) if inp else (find_latest_mkv() if auto_latest else None)
    if mkv is None:
        raise typer.Exit("Provide --inp or use --auto-latest.")
    detect_scenes(mkv, Path(outdir) if outdir else None, mode, threshold)

@app.command()
def split(
    inp: Optional[str] = typer.Option(None, help="Input MKV path"),
    csv_path: Optional[str] = typer.Option(None, help="PySceneDetect CSV path"),
    outdir: str = typer.Option(..., help="Output directory for clips"),
    engine: str = typer.Option("mkvmerge", help="mkvmerge|ffmpeg"),
    copy: bool = typer.Option(True, help="ffmpeg: try -c copy"),
    auto_latest: bool = typer.Option(False, help="Use newest MKV under data/sources/")
):
    """Split video into scene clips using mkvmerge or ffmpeg."""
    mkv = Path(inp) if inp else (find_latest_mkv() if auto_latest else None)
    if mkv is None:
        raise typer.Exit("Provide --inp or use --auto-latest.")
    if not csv_path:
        # default CSV based on mkv stem or parent folder name
        movie_name = mkv.parent.name if mkv.parent.name != "sources" else mkv.stem
        csv_path = f"data/scenedetect/{movie_name}/{movie_name}-Scenes.csv"
    if engine == "mkvmerge":
        split_with_mkvmerge(mkv, Path(csv_path), Path(outdir))
    else:
        split_with_ffmpeg(mkv, Path(csv_path), Path(outdir), copy)

@app.command()
def review(clips_dir: str, review_root: str = "data/review"):
    """Create keep/reject folders + manifest.csv for human triage."""
    stage_review(Path(clips_dir), Path(review_root))

if __name__ == "__main__":
    app()

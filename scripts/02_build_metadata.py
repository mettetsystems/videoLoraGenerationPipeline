"""
02_build_metadata.py
Walks data\clips and writes data\clips_metadata.csv with:
video_path, parent_set, filename, duration_sec, width, height, size_bytes

Requires:
- ffmpeg/ffprobe on PATH
"""
import csv, json, subprocess
from pathlib import Path

ROOT = Path(r"D:\videoLoraGenerationPipeline")
CLIPS_DIR = ROOT / "data" / "clips"
OUT_CSV   = ROOT / "data" / "clips_metadata.csv"

def ffprobe_json(path: Path) -> dict:
    res = subprocess.run(
        ["ffprobe","-v","error","-print_format","json","-show_streams","-show_format",str(path)],
        capture_output=True, text=True
    )
    if res.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}: {res.stderr}")
    return json.loads(res.stdout)

def extract_meta(path: Path) -> dict:
    info = ffprobe_json(path)
    duration = None
    if "format" in info and "duration" in info["format"]:
        try: duration = float(info["format"]["duration"])
        except Exception: duration = None
    width = height = None
    for st in info.get("streams", []):
        if st.get("codec_type") == "video":
            width, height = st.get("width"), st.get("height")
            break
    return {
        "video_path": str(path),
        "parent_set": path.parent.name,
        "filename":   path.name,
        "duration_sec": duration,
        "width": width,
        "height": height,
        "size_bytes": path.stat().st_size,
    }

def main():
    clips = list(CLIPS_DIR.rglob("*.mp4")) + list(CLIPS_DIR.rglob("*.mkv"))
    if not clips:
        print(f"No clips found under {CLIPS_DIR}. Run 01_detect_and_cut.ps1 first."); return
    rows = []
    for clip in clips:
        try: rows.append(extract_meta(clip))
        except Exception as e: print(f"[WARN] {clip}: {e}")
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    print(f"Wrote: {OUT_CSV} ({len(rows)} rows)")

if __name__ == "__main__":
    main()

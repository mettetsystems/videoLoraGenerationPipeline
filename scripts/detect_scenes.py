#!/usr/bin/env python3
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

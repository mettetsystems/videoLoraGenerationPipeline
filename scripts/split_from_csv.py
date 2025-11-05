#!/usr/bin/env python3
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

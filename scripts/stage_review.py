#!/usr/bin/env python3
import argparse
from pathlib import Path
from dataprep.core import stage_review
p = argparse.ArgumentParser(description="Prepare keep/reject and manifest.")
p.add_argument("--clips_dir", required=True)
p.add_argument("--review_root", default="data/review")
a = p.parse_args()
base = stage_review(Path(a.clips_dir), Path(a.review_root))
print(f"Review ready: {base}")

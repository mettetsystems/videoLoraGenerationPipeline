PY=python

init:
$(PY) -c "print('nothing to init if you already ran it')"

install:
python -m venv .venv && .venv\\Scripts\\python.exe -m pip install -U pip && .venv\\Scripts\\python.exe -m pip install -e .

scenes:
$(PY) scripts/detect_scenes.py --input $(MKV)

split:
$(PY) scripts/split_from_csv.py --input $(MKV) --csv $(CSV) --outdir $(OUT) --engine mkvmerge

review:
$(PY) scripts/stage_review.py --clips_dir $(CLIPS)

#!/usr/bin/env bash
set -euo pipefail
out=${1:-data/sources}
disc=${2:-0}
minlen=${3:-1200}
makemkvcon mkv disc:${disc} all "$out" --minlength=${minlen} --progress=-stdout

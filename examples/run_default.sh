#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

PYTHONPATH=. python -m ABinterface \
  --N 12 \
  --pulse-duration 20 \
  --t-final 70 \
  --dt 0.02 \
  --carrier full \
  --omega-eV 2.0 \
  --lambda-soc-A 0.05 \
  --lambda-soc-B 0.05 \
  --soc-mix-cb-A 0.02 \
  --soc-mix-cb-B 0.02 \
  --tAB 0.08 \
  --W-downhill 0.01 \
  --W-intra 0.03 \
  --compare-time-1 22 \
  --compare-time-2 50 \
  --delta-color-scale 0.08 \
  --delta-color-norm linear

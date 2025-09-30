#!/usr/bin/env bash
set -euo pipefail

ROOT="$(pwd)"
CSV="$ROOT/results/csv"
FIG="$ROOT/plots"

# Defaults (edit if needed)
export BASE_GHZ=${BASE_GHZ:=2.40}
export MEM_MT_S=${MEM_MT_S:=4266}
export BUS_WIDTH_BITS=${BUS_WIDTH_BITS:=64}
export CHANNELS=${CHANNELS:=2}
export L1D_B=${L1D_B:=49152}
export L2_B=${L2_B:=1310720}
export LLC_B=${LLC_B:=8192000}

mkdir -p "$CSV" "$FIG" "$ROOT/results/raw/perf" "$ROOT/results/logs"

# Use current venv if active; else try system python3
PY="$(command -v python || command -v python3)"
"$PY" scripts/make_all_plots.py \
  --csvdir "$CSV" \
  --figdir "$FIG" \
  --base-ghz "$BASE_GHZ" \
  --mem-mts "$MEM_MT_S" \
  --bus-bits "$BUS_WIDTH_BITS" \
  --channels "$CHANNELS" \
  --l1d "$L1D_B" --l2 "$L2_B" --llc "$LLC_B"

echo "All figures written to $FIG/"

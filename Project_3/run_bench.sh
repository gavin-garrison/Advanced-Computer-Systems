#!/usr/bin/env bash
set -euo pipefail

# ------------------ CONFIG ------------------
# Target: file path is safest on WSL; use a big sparse/allocated file.
# You can override by: export SSD_TARGET=/path/to/your/target.img
SSD_TARGET="${SSD_TARGET:-$HOME/testfile_wsl.img}"

# Create a 16 GiB file once (skip if it exists)
if [[ ! -f "$SSD_TARGET" ]]; then
  echo "[*] Creating $SSD_TARGET (16 GiB)…"
  fallocate -l 16G "$SSD_TARGET"
fi

OUT=out
mkdir -p "$OUT"

# WSL-friendly: use buffered path and psync/libaio
B=1

echo "[*] Zero-queue baselines (QD=1)…"
fio --name=zero_4k_randread   --filename="$SSD_TARGET" --rw=randread  --bs=4k   --iodepth=1 --ioengine=psync --buffered=$B --time_based=1 --runtime=20 --group_reporting=1 --offset=4MiB --size=8GiB --output-format=json --output=$OUT/zero_4k_randread.json
fio --name=zero_4k_randwrite  --filename="$SSD_TARGET" --rw=randwrite --bs=4k   --iodepth=1 --ioengine=psync --buffered=$B --time_based=1 --runtime=20 --group_reporting=1 --offset=4MiB --size=8GiB --output-format=json --output=$OUT/zero_4k_randwrite.json
fio --name=zero_128k_seqread  --filename="$SSD_TARGET" --rw=read      --bs=128k --iodepth=1 --ioengine=psync --buffered=$B --time_based=1 --runtime=20 --group_reporting=1 --offset=4MiB --size=8GiB --output-format=json --output=$OUT/zero_128k_seqread.json
fio --name=zero_128k_seqwrite --filename="$SSD_TARGET" --rw=write     --bs=128k --iodepth=1 --ioengine=psync --buffered=$B --time_based=1 --runtime=20 --group_reporting=1 --offset=4MiB --size=8GiB --output-format=json --output=$OUT/zero_128k_seqwrite.json

echo "[*] Block-size sweeps (3 repeats each)…"
SIZES=(4k 16k 32k 64k 128k 256k)
for rep in 1 2 3; do
  for bs in "${SIZES[@]}"; do
    fio --name=bs_rand_R_${bs}_${rep} --filename="$SSD_TARGET" --rw=randread  --bs=$bs   --iodepth=32 --ioengine=libaio --buffered=$B --time_based=1 --runtime=20 --group_reporting=1 --offset=4MiB --size=8GiB --output-format=json --output=$OUT/bs_rand_R_${bs}_${rep}.json
    fio --name=bs_rand_W_${bs}_${rep} --filename="$SSD_TARGET" --rw=randwrite --bs=$bs   --iodepth=32 --ioengine=libaio --buffered=$B --time_based=1 --runtime=20 --group_reporting=1 --offset=4MiB --size=8GiB --output-format=json --output=$OUT/bs_rand_W_${bs}_${rep}.json

    fio --name=bs_seq_R_${bs}_${rep}  --filename="$SSD_TARGET" --rw=read      --bs=$bs   --iodepth=1  --ioengine=psync  --buffered=$B --time_based=1 --runtime=15 --group_reporting=1 --offset=4MiB --size=8GiB --output-format=json --output=$OUT/bs_seq_R_${bs}_${rep}.json
    fio --name=bs_seq_W_${bs}_${rep}  --filename="$SSD_TARGET" --rw=write     --bs=$bs   --iodepth=1  --ioengine=psync  --buffered=$B --time_based=1 --runtime=15 --group_reporting=1 --offset=4MiB --size=8GiB --output-format=json --output=$OUT/bs_seq_W_${bs}_${rep}.json
  done
done

echo "[*] Read/Write mixes @4k rand, QD32…"
for m in 100R 100W 70R30W 50R50W; do
  case "$m" in
    100R) RW=randread ;;
    100W) RW=randwrite ;;
    70R30W) RW=randrw; MIX="--rwmixread=70" ;;
    50R50W) RW=randrw; MIX="--rwmixread=50" ;;
  esac
  fio --name=mix_${m}_1 --filename="$SSD_TARGET" --rw=$RW $MIX --bs=4k --iodepth=32 --ioengine=libaio --buffered=$B --time_based=1 --runtime=30 --group_reporting=1 --offset=4MiB --size=4GiB --output-format=json --output=$OUT/mix_${m}_1.json
done

echo "[*] Queue-depth sweeps…"
QDS=(1 2 4 8 16 32 64)
for rep in 1 2 3; do
  for qd in "${QDS[@]}"; do
    fio --name=qd_4k_rand_${qd}_${rep}   --filename="$SSD_TARGET" --rw=randread --bs=4k   --iodepth=$qd --ioengine=libaio --buffered=$B --time_based=1 --runtime=20 --group_reporting=1 --offset=4MiB --size=4GiB  --output-format=json --output=$OUT/qd_4k_rand_${qd}_${rep}.json
  done
done
for rep in 1 2 3; do
  for qd in 1 2 4 8 16 32 64 128; do
    fio --name=qd_128k_seq_${qd}_${rep}  --filename="$SSD_TARGET" --rw=read     --bs=128k --iodepth=$qd --ioengine=libaio --buffered=$B --time_based=1 --runtime=15 --group_reporting=1 --offset=4MiB --size=4GiB  --output-format=json --output=$OUT/qd_128k_seq_${qd}_${rep}.json
  done
done

echo "[*] Tail latency (4k rand @ QD=8 and 64)…"
fio --name=tail_4k_rand_qd8_1  --filename="$SSD_TARGET" --rw=randread --bs=4k --iodepth=8  --ioengine=libaio --buffered=$B --time_based=1 --runtime=60 --group_reporting=1 --offset=4MiB --size=4GiB --output-format=json --output=$OUT/tail_4k_rand_qd8_1.json
fio --name=tail_4k_rand_qd64_1 --filename="$SSD_TARGET" --rw=randread --bs=4k --iodepth=64 --ioengine=libaio --buffered=$B --time_based=1 --runtime=60 --group_reporting=1 --offset=4MiB --size=4GiB --output-format=json --output=$OUT/tail_4k_rand_qd64_1.json

echo "[*] Working-set size (256 MiB vs 8 GiB, 4k rand, QD32)…"
fio --name=ws_small --filename="$SSD_TARGET" --rw=randread --bs=4k --iodepth=32 --ioengine=libaio --buffered=$B --time_based=1 --runtime=30 --size=256MiB --offset=4MiB --group_reporting=1 --output-format=json --output=$OUT/ws_small.json
fio --name=ws_large --filename="$SSD_TARGET" --rw=randread --bs=4k --iodepth=32 --ioengine=libaio --buffered=$B --time_based=1 --runtime=30 --size=8GiB    --offset=4MiB --group_reporting=1 --output-format=json --output=$OUT/ws_large.json

echo "[*] Burst → steady write (15 min, logs)…"
fio --name=slclike --filename="$SSD_TARGET" --rw=write --bs=128k --iodepth=32 --ioengine=libaio --buffered=$B --time_based=1 --runtime=900 --log_avg_msec=500 --write_bw_log=$OUT/slc_bw --output-format=json --output=$OUT/slc.json

echo "[*] Compressibility check (0% vs 50%)…"
fio --name=comp0  --filename="$SSD_TARGET" --rw=randread --bs=4k --iodepth=32 --ioengine=libaio --buffered=$B --refill_buffers=1 --buffer_compress_percentage=0  --time_based=1 --runtime=20 --group_reporting=1 --offset=4MiB --size=4GiB --output-format=json --output=$OUT/comp0.json
fio --name=comp50 --filename="$SSD_TARGET" --rw=randread --bs=4k --iodepth=32 --ioengine=libaio --buffered=$B --refill_buffers=1 --buffer_compress_percentage=50 --time_based=1 --runtime=20 --group_reporting=1 --offset=4MiB --size=4GiB --output-format=json --output=$OUT/comp50.json

echo "[*] Done generating raw results in $OUT/"

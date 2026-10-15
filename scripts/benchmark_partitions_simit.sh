#!/usr/bin/env bash
#
# Time one D-Flow FM case on simit-server at several partition counts, one run
# at a time on socket 0, and write the time in the time loop per count to
# <base>/../<name>_partitions.tsv. Each count runs on a fresh copy of the
# unpartitioned case.
#
# Usage, on simit-server:
#     nohup bash benchmark_partitions_simit.sh <base_case_dir> 8 12 16 24 > bench.log 2>&1 &
#
set -uo pipefail

BASE="$(realpath "$1")"
shift
HERE="$(dirname "$(realpath "$0")")"
OUT="$(dirname "$BASE")/$(basename "$BASE")_partitions.tsv"
printf "partitions\ttimeloop_h\tavg_timestep_s\tsteps\n" > "$OUT"
for N in "$@"; do
    D="${BASE}_np$(printf %02d "$N")"
    rm -rf "$D"
    cp -r "$BASE" "$D"
    bash "$HERE/run_fm_simit.sh" "$D" "$N" > "$D.log" 2>&1
    DIA=$(ls "$D"/output/*_0000.dia "$D"/output/*.dia 2>/dev/null | head -1)
    T=$(grep -h "total time in timeloop" "$DIA" | awk '{print $NF}')
    S=$(grep -h "average timestep" "$DIA" | awk '{print $NF}')
    K=$(grep -h "nr of timesteps" "$DIA" | awk '{print $NF}')
    printf "%s\t%s\t%s\t%s\n" "$N" "${T:-NA}" "${S:-NA}" "${K:-NA}" >> "$OUT"
    echo "$(date -Is) partitions $N: timeloop ${T:-NA} h"
done
cat "$OUT"

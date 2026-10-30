#!/usr/bin/env bash
#
# Partition and run one D-Flow FM case on simit-server under Intel MPI.
#
# The case directory holds the global MDU, mesh and forcing written by
# build_hindcast_v02.py. The mesh is partitioned here, on the machine that runs
# it, since METIS partitions differently on Windows and Linux and partitioned
# files are not portable. The ranks are pinned to free physical cores chosen
# by simit_pick_cores.sh, on socket 0 by preference, the socket of MaltaDT by
# the convention shared with StagnoneDT, so that runs of the two projects do
# not share cores. The claim on the cores lasts while this launcher runs.
# I_MPI_WAIT_MODE=1 lets a waiting rank yield its core, which matters once
# DIMR alternates FM with SWAN.
#
# Usage, on simit-server:
#     bash run_fm_simit.sh <case_dir> <n_partitions> [<mdu>]
#
set -euo pipefail

CASE="$(realpath "$1")"
N="$2"
# ~/MaltaDT/model/hindcast links to the data disk, mounted with nofail, so a
# disk absent at boot leaves /storage an empty directory rather than an error.
if [[ "$CASE" == /storage/* ]] && ! mountpoint -q /storage; then
    echo "ERROR: /storage is not mounted"; exit 3
fi
# build_hindcast_v02.py names the MDU after the case directory. A pattern on
# the partition suffix _NNNN.mdu would also match a case named after its dates.
MDU="${3:-$(basename "$CASE").mdu}"
[[ -f "$CASE/$MDU" ]] || { echo "ERROR: $CASE/$MDU not found, pass the MDU name"; exit 3; }
FM="$HOME/Scaricati/delft3dfm/lnx64"
PICK="$HOME/simit_tools/simit_pick_cores.sh"
SOCKET="${SIMIT_SOCKET:-0}"

set +u
source /opt/intel/oneapi/setvars.sh > /dev/null 2>&1 || true
set -u
export PATH="$FM/bin:$PATH"
export LD_LIBRARY_PATH="$FM/lib:${LD_LIBRARY_PATH:-}"
command -v mpiexec > /dev/null || { echo "ERROR: no mpiexec after sourcing oneAPI"; exit 4; }

export OMP_NUM_THREADS=1
export I_MPI_WAIT_MODE=1
export I_MPI_PIN=1
CPUS="$(bash "$PICK" "$N" "$SOCKET" $$)" || { echo "ERROR: no $N free cores"; exit 2; }
trap 'rm -f "$HOME/.simit_cores/$$.claim"' EXIT
export I_MPI_PIN_PROCESSOR_LIST="$CPUS"

# Processes of this user whose working directory is the case, a removed copy
# of it included (readlink then appends " (deleted)")
case_pids() {
    for p in $(pgrep -u "$USER" -f dimr); do
        [[ "$(readlink "/proc/$p/cwd" 2>/dev/null)" == "$CASE"* ]] && echo "$p"
    done
    return 0
}
if [[ -n "$(case_pids)" ]]; then
    echo "ERROR: dimr already running in $CASE: $(case_pids | tr '\n' ' ')"
    exit 5
fi

cd "$CASE"
rm -rf output "${MDU%.mdu}"_0*.mdu *_0[0-9][0-9][0-9]_net.nc *.cache
if [[ "$N" -gt 1 ]]; then
    run_dflowfm.sh --partition:ndomains="$N":icgsolver=6 "$MDU" > partition.log 2>&1
    # The partitioner returns success after an error in the MDU, so the
    # partitioned files are checked before any rank is started
    if [[ ! -f "${MDU%.mdu}_$(printf %04d $((N - 1))).mdu" ]] || grep -q "\*\* ERROR" partition.log; then
        echo "ERROR: partitioning failed:"; grep "\*\* ERROR" partition.log | head -5
        exit 6
    fi
    PROCS="$(seq -s' ' 0 $((N - 1)))"
else
    PROCS="0"
fi
cat > dimr_config.xml << EOF
<?xml version="1.0" encoding="utf-8"?>
<dimrConfig xmlns="http://schemas.deltares.nl/dimr">
  <documentation><fileVersion>1.3</fileVersion><createdBy>run_fm_simit.sh</createdBy></documentation>
  <control><start name="DFlowFM"/></control>
  <component name="DFlowFM">
    <library>dflowfm</library>
    <process>$PROCS</process>
    <workingDir>.</workingDir>
    <inputFile>$MDU</inputFile>
    <mpiCommunicator>DFM_COMM_DFMWORLD</mpiCommunicator>
  </component>
</dimrConfig>
EOF
echo "case $CASE, $N partitions, pinned to CPUs $I_MPI_PIN_PROCESSOR_LIST, start $(date -Is)"
run_dimr.sh -c "$N" -m dimr_config.xml > run.log 2>&1 || echo "run_dimr exit $?"
# When some ranks abort, mpiexec may return while the others keep waiting for
# them, pinned to the same cores as the next launch. They are ended here.
LEFT="$(case_pids)"
if [[ -n "$LEFT" ]]; then
    echo "ending ranks left behind: $(echo $LEFT)"
    kill $LEFT 2> /dev/null; sleep 5; kill -9 $(case_pids) 2> /dev/null || true
fi
echo "end $(date -Is)"
DIA="output/${MDU%.mdu}_0000.dia"
[[ "$N" -eq 1 ]] && DIA="output/${MDU%.mdu}.dia"
grep -hE "total time in timeloop|average timestep|nr of timesteps|\*\* ERROR" "$DIA" || true

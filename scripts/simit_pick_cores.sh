#!/usr/bin/env bash
#
# Choose N free physical cores on simit-server and claim them for a launch.
#
# Shared by the MaltaDT and StagnoneDT launchers, installed on the server at
# ~/simit_tools/simit_pick_cores.sh. A physical core counts as busy when
#   - a running dimr, dflowfm, swan or wave process is pinned to a set that
#     includes either of its two hardware threads (a pinned rank may move
#     anywhere within its set, so the whole set is busy),
#   - an unpinned such process is currently placed on it, or
#   - a live claim written by an earlier call holds it.
# Free cores are taken from the preferred socket first, MaltaDT on socket 0
# and StagnoneDT on socket 1 by convention. The claim is written under flock,
# so two launches started together do not receive the same cores, and lasts
# as long as the process that made it, normally the launcher, is alive.
#
# Usage:
#     CPUS=$(simit_pick_cores.sh <n> <socket 0|1> [<claimant pid>])
# prints a comma-separated list of the first hardware thread of each core,
# for I_MPI_PIN_PROCESSOR_LIST, or exits 1 when too few cores are free.
#     simit_pick_cores.sh --status
# prints the busy cores and the claims.
#
set -euo pipefail

DIR="$HOME/.simit_cores"
mkdir -p "$DIR"
exec 9> "$DIR/lock"
flock 9

# Physical cores: first hardware thread of each core and its socket
declare -A SOCKET SIBLINGS
CORES=()
for t in /sys/devices/system/cpu/cpu[0-9]*; do
    c=${t##*cpu}
    sib=$(cat "$t/topology/thread_siblings_list")
    first=${sib%%[,-]*}
    if [[ "$c" == "$first" ]]; then
        CORES+=("$c")
        SOCKET[$c]=$(cat "$t/topology/physical_package_id")
        SIBLINGS[$c]=$sib
    fi
done
NCPU=$(nproc --all)

declare -A THREAD2CORE
for c in "${CORES[@]}"; do
    for s in ${SIBLINGS[$c]//,/ }; do THREAD2CORE[$s]=$c; done
done

expand() {  # "0,2-4,8" -> "0 2 3 4 8"
    local out=() part a b
    for part in ${1//,/ }; do
        if [[ "$part" == *-* ]]; then a=${part%-*}; b=${part#*-}; out+=($(seq "$a" "$b"))
        else out+=("$part"); fi
    done
    echo "${out[@]}"
}

declare -A BUSY
for p in $(pgrep -f 'dimr|dflowfm|swan|wave\.exe|/wave ' 2>/dev/null || true); do
    # mpiexec, the hydra proxies and waiting launchers hold no core
    cpu=$(ps -o pcpu= -p "$p" 2>/dev/null | tr -d ' ') || continue
    [[ -z "$cpu" || ${cpu%.*} -lt 10 ]] && continue
    aff=$(taskset -cp "$p" 2>/dev/null | sed 's/.*: //') || continue
    [[ -z "$aff" ]] && continue
    threads=($(expand "$aff"))
    declare -A own=()
    for t in "${threads[@]}"; do own[${THREAD2CORE[$t]}]=1; done
    if [[ ${#own[@]} -eq 1 ]]; then
        # pinned to one core
        for c in "${!own[@]}"; do BUSY[$c]=1; done
    else
        # unpinned, or pinned to a domain of several cores as by the default
        # I_MPI_PIN_DOMAIN: the process occupies the core it runs on, and the
        # scheduler keeps a single process of a domain on a free core of it
        psr=$(ps -o psr= -p "$p" 2>/dev/null | tr -d ' ') || continue
        [[ -n "$psr" ]] && BUSY[${THREAD2CORE[$psr]}]=1
    fi
    unset own
done
for f in "$DIR"/*.claim; do
    [[ -e "$f" ]] || continue
    owner=$(basename "$f" .claim)
    if kill -0 "$owner" 2> /dev/null; then
        for c in $(cat "$f" | tr ',' ' '); do BUSY[$c]=1; done
    else
        rm -f "$f"
    fi
done

if [[ "${1:-}" == "--status" ]]; then
    for s in 0 1; do
        b=(); for c in "${CORES[@]}"; do [[ ${SOCKET[$c]} == "$s" && -n "${BUSY[$c]:-}" ]] && b+=("$c"); done
        echo "socket $s busy cores: ${#b[@]} (${b[*]:-none})"
    done
    for f in "$DIR"/*.claim; do [[ -e "$f" ]] && echo "claim by pid $(basename "$f" .claim): $(cat "$f")"; done
    exit 0
fi

N="$1"
PREF="$2"
OWNER="${3:-$PPID}"
PICK=()
for pass in pref other; do
    for c in "${CORES[@]}"; do
        [[ ${#PICK[@]} -ge $N ]] && break
        [[ -n "${BUSY[$c]:-}" ]] && continue
        if [[ $pass == pref && ${SOCKET[$c]} != "$PREF" ]] || [[ $pass == other && ${SOCKET[$c]} == "$PREF" ]]; then
            continue
        fi
        PICK+=("$c")
    done
done
if [[ ${#PICK[@]} -lt $N ]]; then
    echo "only ${#PICK[@]} free physical cores, $N requested" >&2
    exit 1
fi
for c in "${PICK[@]}"; do
    if [[ ${SOCKET[$c]} != "$PREF" ]]; then
        echo "warning: socket $PREF lacks free cores, the run spans both sockets" >&2
        break
    fi
done
LIST=$(IFS=,; echo "${PICK[*]}")
echo "$LIST" > "$DIR/$OWNER.claim"
echo "$LIST"

"""Build the interactive maps of eight long-wave scenarios and their index page.

One scenario is taken for each direction of arrival, at the speed that gives
the largest peak at Senglea in the sweep, for the disturbance 15 km long. Each
is run again with map output, since the sweep kept the station records alone,
and turned into a page by build_longwave_portal.py. The map output and the
regridded caches are removed once the payload of the page is written. Each page
carries a bar that leads to the other seven and a description of the set, from
longwave_portal_page.py, and the entry page opens the scenario of largest response.

Usage:
    python build_longwave_portal_set.py [--workers 4] [--pages-only]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "model" / "tests" / "longwave_portal_runs"
OUT = ROOT / "outputs" / "longwave_portal"
TABLE = ROOT / "data" / "processed" / "longwave_sweep_response.csv"
MESH = "outer03"                 # with the breakwater thin dams, declared by default
SIGMA_KM = 15
T_TOTAL = 6 * 3600.0
MAP_INTERVAL = 240.0
FROM = {0: "south", 45: "southwest", 90: "west", 135: "northwest", 180: "north",
        225: "northeast", 270: "east", 315: "southeast"}
ORDER = (180, 225, 270, 315, 0, 45, 90, 135)        # by direction of arrival, from the north
RHO_G = 1025.0 * 9.81


def selection():
    """The scenario of largest peak at Senglea for each direction, from the sweep."""
    import pandas as pd

    df = pd.read_csv(TABLE)
    d = df[df.sigma_km == SIGMA_KM]
    p = d.pivot_table(index=["heading", "speed"], columns="station", values="peak").reset_index()
    best = p.loc[p.groupby("heading").senglea.idxmax()].set_index("heading")
    rows = []
    for h in ORDER:
        r = best.loc[h]
        speed = int(r.speed)
        rows.append(dict(heading=h, speed=speed, case=f"{MESH}_h{h:03d}_u{speed:02d}_s{SIGMA_KM:02d}",
                         offshore=float(r.offshore_4km), senglea=float(r.senglea),
                         marsa=float(r.marsa_head), msida=float(r.msida_head)))
    return rows


def build_one(sc: dict) -> tuple[str, int, float]:
    t0 = time.time()
    case = sc["case"]
    page = OUT / case / "index.html"
    log = RUNS / f"{case}.log"
    with open(log, "w") as f:
        rc = subprocess.call(
            [sys.executable, str(Path(__file__).with_name("build_longwave_scenario.py")),
             "--mesh", MESH, "--heading", str(sc["heading"]), "--speed", str(sc["speed"]),
             "--sigma-along", str(SIGMA_KM * 1e3), "--tag", f"_s{SIGMA_KM:02d}",
             "--t-total", str(T_TOTAL), "--map-interval", str(MAP_INTERVAL), "--out", str(RUNS)],
            stdout=f, stderr=subprocess.STDOUT)
        if rc == 0:
            rc = subprocess.call(
                [sys.executable, str(Path(__file__).with_name("build_longwave_portal.py")),
                 case, "--root", str(RUNS), "--discard-caches"],
                stdout=f, stderr=subprocess.STDOUT)
    for big in (RUNS / case / "output").glob("*_map.nc"):
        big.unlink()
    for big in list((RUNS / case).glob("pressure.nc")) + list((RUNS / case).glob("*.cache")):
        big.unlink()
    return case, rc if page.exists() else (rc or 1), time.time() - t0


REDIRECT = """<!doctype html>
<meta charset="utf-8">
<title>Valletta long-wave scenarios</title>
<meta http-equiv="refresh" content="0; url=__CASE__/index.html">
<a href="__CASE__/index.html">Valletta long-wave scenarios</a>
"""


def write_set(rows) -> None:
    """The description of the set, read by build_longwave_portal.py for every page."""
    (OUT / "_set.json").write_text(json.dumps(rows), encoding="utf-8")


def write_pages(rows) -> int:
    """Rewrite the page of every scenario already built, without its payload."""
    failed = 0
    for r in rows:
        if not (OUT / r["case"] / "data" / "meta.json").exists():
            continue
        failed += subprocess.call(
            [sys.executable, str(Path(__file__).with_name("build_longwave_portal.py")),
             r["case"], "--root", str(RUNS), "--html-only"], stdout=subprocess.DEVNULL) != 0
    return failed


def write_index(rows) -> Path:
    """The entry page, which opens the scenario of largest response."""
    first = max(rows, key=lambda r: r["senglea"])["case"]
    path = OUT / "index.html"
    path.write_text(REDIRECT.replace("__CASE__", first), encoding="utf-8")
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--pages-only", action="store_true",
                    help="rewrite the pages and the entry page, keeping the payloads")
    args = ap.parse_args(argv)
    rows = selection()
    OUT.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)
    failed = 0
    write_set(rows)
    if args.pages_only:
        failed = write_pages(rows)
    else:
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            for case, rc, wall in pool.map(build_one, rows):
                failed += rc != 0
                print(f"{case} exit {rc} {wall:5.0f} s (elapsed {(time.time() - t0) / 60:.0f} min)",
                      flush=True)
    path = write_index(rows)
    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file()) / 1e6
    print(f"index written to {path}; {size:.0f} MB under {OUT}; {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

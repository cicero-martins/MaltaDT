"""Build the interactive maps of eight long-wave scenarios and their index page.

One scenario is taken for each direction of arrival, at the speed that gives
the largest peak at Senglea in the sweep, for the disturbance 15 km long. Each
is run again with map output, since the sweep kept the station records alone,
and turned into a page by build_longwave_portal.py. The map output and the
regridded caches are removed once the payload of the page is written. The index
page states what the scenarios are within the study and links to the eight maps.

Usage:
    python build_longwave_portal_set.py [--workers 4] [--index-only]
"""

from __future__ import annotations

import argparse
import html
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "model" / "tests" / "longwave_portal_runs"
OUT = ROOT / "outputs" / "longwave_portal"
TABLE = ROOT / "data" / "processed" / "longwave_sweep_response.csv"
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
        rows.append(dict(heading=h, speed=speed, case=f"outer01_h{h:03d}_u{speed:02d}_s{SIGMA_KM:02d}",
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
             "--mesh", "outer01", "--heading", str(sc["heading"]), "--speed", str(sc["speed"]),
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


INDEX = """<!doctype html>
<meta charset="utf-8">
<title>Valletta long-wave scenarios</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{--bg:#0d1117;--panel:#161b22;--line:#30363d;--ink:#e6edf3;--ink2:#9aa7b4;--acc:#58c8d9}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,Segoe UI,Roboto,sans-serif}
main{max-width:980px;margin:0 auto;padding:36px 22px 60px}
h1{font-size:25px;margin:0 0 4px}
h2{font-size:16px;margin:30px 0 8px;color:var(--acc);font-weight:600}
.sub{color:var(--ink2);margin-bottom:22px}
p{margin:0 0 12px;max-width:74ch}
table{border-collapse:collapse;width:100%;margin-top:6px;font-size:14px}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:right}
th:first-child,td:first-child{text-align:left}
th{color:var(--ink2);font-weight:500}
a{color:var(--acc);text-decoration:none}
a:hover{text-decoration:underline}
td a{font-weight:600}
.note{color:var(--ink2);font-size:13.5px}
ul{margin:0 0 12px 18px;padding:0;max-width:74ch}
</style>
<main>
<h1>Response of the Valletta harbours to moving pressure disturbances</h1>
<div class="sub">Eight scenarios of a numerical sweep, one for each direction of arrival.
Oceanography Malta Research Group, University of Malta, with the Universit&agrave; degli Studi di Palermo.
Interreg VI-A Italia-Malta WETWISE.</div>

<h2>Place of the scenarios in the study</h2>
<p>The study addresses the circulation and the renewal of the water of the Grand Harbour and
Marsamxett with a coupled wave and hydrodynamic model in Delft3D FM. One of its components concerns
the <em>mil&#289;&#295;uba</em>, the long wave raised by an atmospheric pressure disturbance travelling
over the sea, a meteotsunami, which floods the low ground at the head of Msida Creek.</p>
<p>The scenarios shown here belong to that component. Each is an idealised experiment and reproduces
no particular event. A pressure rise of 2 hPa, 15 km long and 50 km wide, crosses the Sicily Channel
on a straight track of 400 km through the harbours at constant speed, and the model computes the
response of the sea in two dimensions over a domain of 419 by 361 km, with cells of 15 m inside the
harbours. A sweep of 96 such scenarios, over six speeds, eight directions and two lengths, gives the
response of the harbours as a function of the disturbance. The eight maps below are the scenarios of
largest response for each direction.</p>

<h2>Reading the maps</h2>
<ul>
<li>The water level is in centimetres and the currents in metres per second, both for the rise of 2 hPa.
The response is proportional to the rise within 2 per cent up to 10 hPa.</li>
<li>The amplification in the table is the largest departure of the level from rest divided by the
1.99 cm that the same rise would produce if it stood still, the static response.</li>
<li>Zooming into the harbours brings in a finer grid. The time shown is the time elapsed from the
start of the scenario, the disturbance passing over the harbours near the middle of its track.</li>
</ul>

<h2>Scenarios</h2>
<table>
<tr><th>Arrives from</th><th>Speed, km/h</th><th>4 km off the harbours</th><th>Senglea</th>
<th>Marsa, head of the Grand Harbour</th><th>Msida Creek, head</th><th>Peak at Marsa for 2 hPa</th></tr>
__ROWS__
</table>
<p class="note" style="margin-top:10px">Columns three to six give the amplification over the static
response.</p>

<h2>Standing of the results</h2>
<p>The results are preliminary. The disturbances are of one shape and one width, wind is not applied,
and the response has not yet been tested against the pressure and sea level records of dated events.
The bed level at the heads of the inlets, where flooding is reported, rests on a survey with gaps.</p>
<p class="note">Source code and documents at
<a href="https://github.com/cicero-martins/MaltaDT">github.com/cicero-martins/MaltaDT</a>.
The interactive page is that of the Stagnone di Marsala digital twin, applied here without change
to its code.</p>
</main>
"""


def write_index(rows) -> Path:
    cells = []
    for r in rows:
        if not (OUT / r["case"] / "index.html").exists():
            continue
        cm = r["marsa"] * 200.0 / RHO_G * 100.0
        cells.append(
            f"<tr><td><a href=\"{html.escape(r['case'])}/index.html\">the "
            f"{FROM[r['heading']]}</a></td><td>{r['speed'] * 3.6:.0f}</td>"
            f"<td>{r['offshore']:.1f}</td><td>{r['senglea']:.1f}</td><td>{r['marsa']:.1f}</td>"
            f"<td>{r['msida']:.1f}</td><td>{cm:.0f} cm</td></tr>")
    path = OUT / "index.html"
    path.write_text(INDEX.replace("__ROWS__", "\n".join(cells)), encoding="utf-8")
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--index-only", action="store_true")
    args = ap.parse_args(argv)
    rows = selection()
    OUT.mkdir(parents=True, exist_ok=True)
    RUNS.mkdir(parents=True, exist_ok=True)
    failed = 0
    if not args.index_only:
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

"""Download the hourly surface currents of the CALYPSO HF radar network.

The CALYPSO network of the group, CODAR SeaSonde radars on the Maltese Islands
and on the southern coast of Sicily, is distributed by the European HFR Node
through its ERDDAP server (erddap.hfrnode.eu, to which the EMODnet Physics
server redirects). Two products are taken.

- Totals, dataset EUHFR_NRTcurrent_HFR-CALYPSO-Total_v3, a regular grid of
  about 3 km (0.0334 by 0.0270 degrees, 51 by 43 points over 13.69 to
  15.37 E and 35.74 to 36.88 N), hourly from November 2022, with the
  eastward and northward components (EWCT, NSCT), their standard deviations
  (EWCS, NSCS), the geometric dilution of precision (GDOP) and the quality
  flags of the node.
- Radials of the stations on the Maltese Islands, datasets
  EUHFR_NRTcurrent_HFR-CALYPSO-<site>_v3, on a polar grid of 3.02 km in range
  (67 cells) and 5 degrees in bearing (72 cells) about the antenna, with the
  radial velocity (RDVA), the direction of the radial vector (DRVA), the
  spatial and temporal quality estimates (ESPC, ETMP) and the flags. The sites
  are Ta' Barkat (BARK, 14.5561 E, 35.8825 N, some 2 km east of the mouth of
  the Grand Harbour), Ta' Cenc (CENC, Gozo), Ghar Lapsi (LAPS, south-west
  Malta) and Ta' Sopu (SOPU, Gozo, whose record ends in February 2026).

Each window is written to data/raw/hfr_calypso/ as one netCDF file per
product. The data are acknowledged as the CALYPSO data policy requires.

Usage:
    python download_hfr_calypso.py [--window may26 jul26 jul25] [--force]
"""

from __future__ import annotations

import argparse
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "raw" / "hfr_calypso"
SERVER = "https://erddap.hfrnode.eu/erddap/griddap"
TOTAL = "EUHFR_NRTcurrent_HFR-CALYPSO-Total_v3"
RADIAL = "EUHFR_NRTcurrent_HFR-CALYPSO-{}_v3"
SITES = ("BARK", "CENC", "LAPS", "SOPU")
TOTAL_VARS = ("EWCT", "NSCT", "EWCS", "NSCS", "GDOP", "QCflag", "VART_QC", "GDOP_QC",
              "CSPD_QC", "DDNS_QC", "POSITION_QC")
RADIAL_VARS = ("RDVA", "DRVA", "EWCT", "NSCT", "ESPC", "ETMP", "QCflag", "OWTR_QC",
               "CSPD_QC", "VART_QC", "MDFL_QC", "AVRB_QC", "RDCT_QC", "POSITION_QC")
LAT = (35.74, 36.88)
LON = (13.69, 15.37)

# windows of the runs in hand, one day either side
WINDOWS = {
    "may26": ("2026-05-16T00:00:00Z", "2026-05-23T23:00:00Z"),
    "jul26": ("2026-07-02T00:00:00Z", "2026-07-10T23:00:00Z"),
    "jul25": ("2025-07-21T00:00:00Z", "2025-08-02T23:00:00Z"),
}


def request(dataset: str, variables, sel: str) -> str:
    query = ",".join(v + sel for v in variables)
    return f"{SERVER}/{dataset}.nc?" + urllib.parse.quote(query, safe=",():")


def fetch(link: str, path: Path) -> bool:
    try:
        with urllib.request.urlopen(link, timeout=900) as r:
            data = r.read()
    except urllib.error.HTTPError as err:
        print(f"  {path.name}: HTTP {err.code}, {err.read()[:300].decode(errors='replace')}",
              file=sys.stderr)
        return False
    if not data.startswith((b"CDF", b"\x89HDF")):
        print(f"  {path.name}: not netCDF, {data[:300].decode(errors='replace')}", file=sys.stderr)
        return False
    path.write_bytes(data)
    print(f"  {path.name}, {len(data) / 1e6:.1f} MB")
    return True


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--window", nargs="+", default=list(WINDOWS), choices=list(WINDOWS))
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    for name in args.window:
        start, end = WINDOWS[name]
        print(f"{name}: {start} to {end}")
        jobs = [(request(TOTAL, TOTAL_VARS,
                         f"[({start}):1:({end})][(0.0)][({LAT[0]}):1:({LAT[1]})][({LON[0]}):1:({LON[1]})]"),
                 OUT / f"calypso_total_{name}.nc")]
        for site in SITES:
            jobs.append((request(RADIAL.format(site), RADIAL_VARS, f"[({start}):1:({end})][(0.0)][][]"),
                         OUT / f"calypso_radial_{site}_{name}.nc"))
        for link, path in jobs:
            if path.exists() and not args.force:
                print(f"  {path.name} present")
                continue
            fetch(link, path)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Download records of the PORTO coastal stations from the portal of the group.

The portal stations.ocean.mt of the Oceanography Malta Research Group serves
the record of each station through the request it issues itself,
api/?action=downloadStationAscDataForDateRange, with the station reference and
a range of dates. The meteorological stations report wind speed, gust, wind
direction, air temperature, air pressure and humidity at one minute, and the
Portomaso sea level station reports the level at 10 s. Days are requested one
at a time and written as one CSV per station and day,
<out>/<ref>/<ref>_<YYYY-MM-DD>.csv, with the units in a sidecar JSON. Days
without a record are listed and skipped, and days already present are not
requested again.

Station references (getStationList): MetElmo, MetKord and MetMsida on the
harbours, MetCirk, MetDelim, MetMgarG, MetMXlokk and MetQamm elsewhere on the
islands, SLevPMaso for Portomaso and SLevMXlokk for Marsaxlokk.

Usage:
    python download_porto_stations.py --stations MetElmo MetKord MetMsida \\
        --start 2026-07-02 --end 2026-07-10
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
API = "https://stations.ocean.mt/api/"
USER_AGENT = "MaltaDT research download (University of Palermo)"
PAUSE = 0.5                           # s between requests


def request(params: dict) -> dict:
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))


def day(ref: str, date: pd.Timestamp, out: Path) -> str:
    path = out / ref / f"{ref}_{date:%Y-%m-%d}.csv"
    if path.exists():
        return "present"
    d = request(dict(action="downloadStationAscDataForDateRange", ref=ref,
                     startDate=f"{date:%Y-%m-%d}", endDate=f"{date:%Y-%m-%d}", showAttrs=1))
    if not d.get("success") or not d.get("data"):
        return "none"
    names = [h["name"] for h in d["dataHeaders"]]
    # the time stamp leads every row whether or not it is listed among the headers
    cols = ["time"] + [n for n in names if n != "timestamp"]
    rows = d["data"]
    if len(rows[0]) != len(cols):
        cols = ["time"] + names[: len(rows[0]) - 1]
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows, columns=cols).to_csv(path, index=False)
    meta = path.parent / f"{ref}_headers.json"
    if not meta.exists():
        meta.write_text(json.dumps(d["dataHeaders"], indent=1))
    return f"{len(rows)} rows"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stations", nargs="+", required=True)
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True, help="last day, inclusive")
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "raw" / "porto")
    args = ap.parse_args(argv)
    out = args.out if args.out.is_absolute() else ROOT / args.out
    for ref in args.stations:
        missing = []
        for date in pd.date_range(args.start, args.end, freq="D"):
            status = day(ref, date, out)
            if status == "none":
                missing.append(f"{date:%Y-%m-%d}")
            time.sleep(PAUSE)
        n = len(pd.date_range(args.start, args.end, freq="D"))
        print(f"{ref}: {n - len(missing)} of {n} days"
              + (f", none on {' '.join(missing)}" if missing else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Download a sea level record from the JRC Tide Analysis Database (TAD) server.

Adapted from StagnoneDT/scripts/download_marettimo_wl_long.py, which uses the
same API for device 658. The IDSL radar gauges sample at 5 s, so a month holds
some half a million rows, and the request is made one day at a time to stay
below the row cap of the API.

Only the level column is kept. The 5 s level is written per month as a
compressed CSV, and a one-minute mean series is written for the whole record.
One minute resolves frequencies up to 30 cph, against a milghuba band of 0.2 to
2 cph and basin modes of 3 to 6 cph.

Devices identified on the server for the Maltese Islands, group IDSL:

    555  IDSL-42  La Valletta   14.5141 E, 35.8893 N   Senglea, inside the Grand Harbour
    556  IDSL-43  Marsaxlokk    14.5548 E, 35.8316 N
    533  IDSL-34  Malta         14.3319 E, 35.9858 N   at the position of Cirkewwa

Usage:
    python download_jrc_tad_wl.py --device 555 --name senglea \\
        --t-min 2021-06-01 --t-max 2024-12-14 [--workers 4]
"""

from __future__ import annotations

import argparse
import gzip
import io
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "insitu"
API = "https://webcritech.jrc.ec.europa.eu/TAD_server/api/Data/Get/{device}"
N_REC = 100000                  # a day at 5 s is 17 280 rows


def fetch(url: str, timeout: int = 180, retries: int = 5) -> str | None:
    """Response text, or None when every attempt failed.

    The server closes connections without a response under load, which
    http.client raises as RemoteDisconnected rather than as a URLError, so
    every exception is retried with a growing pause.
    """
    req = urllib.request.Request(url, headers={"User-Agent": "MaltaDT/1.0"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:  # noqa: BLE001
            if attempt == retries - 1:
                print(f"  failed {url}: {e!r}", file=sys.stderr)
            else:
                time.sleep(5 * (attempt + 1))
    return None


def parse_day(text: str) -> pd.Series:
    """Level column of a TAD CSV, indexed by UTC time."""
    if not text or not text.lower().startswith("time"):
        return pd.Series(dtype=float)
    df = pd.read_csv(io.StringIO(text), usecols=[0, 1])
    df.columns = ["t", "level"]
    df["t"] = pd.to_datetime(df["t"], format="%d %b %Y %H:%M:%S", errors="coerce")
    df["level"] = pd.to_numeric(df["level"], errors="coerce")
    s = df.dropna().drop_duplicates("t").set_index("t")["level"].sort_index()
    return s


def day_file(cache: Path, day: pd.Timestamp) -> Path:
    return cache / f"{day:%Y-%m}" / f"{day:%Y-%m-%d}.csv.gz"


def get_day(device: int, cache: Path, day: pd.Timestamp) -> tuple[pd.Timestamp, int]:
    path = day_file(cache, day)
    if path.exists():
        return day, -1
    t0 = day.strftime("%Y-%m-%d %H:%M:%S")
    t1 = (day + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)).strftime("%Y-%m-%d %H:%M:%S")
    url = (API.format(device=device) + f"?tMin={quote_plus(t0)}&tMax={quote_plus(t1)}"
           f"&nRec={N_REC}&mode=CSV")
    text = fetch(url)
    if text is None:
        # Not cached, so that a later run retries the day.
        return day, -2
    s = parse_day(text)
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt") as f:
        s.to_csv(f, header=["level_m"], date_format="%Y-%m-%d %H:%M:%S")
    return day, len(s)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--device", type=int, required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--t-min", required=True)
    ap.add_argument("--t-max", required=True)
    ap.add_argument("--workers", type=int, default=2)
    args = ap.parse_args(argv)

    cache = RAW / f"{args.name}_5s"
    days = pd.date_range(args.t_min, args.t_max, freq="D", inclusive="left")
    print(f"device {args.device}, {args.name}, {len(days)} days to {cache}")

    done, failed = 0, []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for day, n in pool.map(lambda d: get_day(args.device, cache, d), days):
            done += 1
            if n == -2:
                failed.append(day)
            elif n >= 0 and (n < 10000 or day.day == 1):
                print(f"  {day:%Y-%m-%d}  {n:6d} rows   ({done}/{len(days)})", flush=True)
    if failed:
        print(f"\n{len(failed)} days failed and were not cached; rerun to retry them:")
        print("  " + " ".join(f"{d:%Y-%m-%d}" for d in failed))

    parts = []
    for day in days:
        path = day_file(cache, day)
        if path.exists() and path.stat().st_size > 40:
            s = pd.read_csv(path, index_col=0, parse_dates=True)["level_m"]
            if len(s):
                parts.append(s.resample("1min").mean())
    if not parts:
        print("no data", file=sys.stderr)
        return 1
    series = pd.concat(parts).dropna()
    out = RAW / f"{args.name}_wl_1min.csv"
    series.to_csv(out, header=["level_m"], date_format="%Y-%m-%d %H:%M")
    full = pd.date_range(series.index[0], series.index[-1], freq="1min")
    print(f"\n1-min series {series.index[0]} to {series.index[-1]}, {len(series)} values, "
          f"{len(series) / len(full):.1%} of the span")
    print(f"written {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

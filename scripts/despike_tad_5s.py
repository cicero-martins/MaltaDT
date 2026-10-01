"""Remove radar echoes from the 5 s record of a JRC TAD radar gauge.

The IDSL gauges are downward-looking radars. Anything entering the beam above
the water, the hull or superstructure of a vessel, heavy rain or spray, shortens
the measured range and appears as a rise of the level. At Senglea, a gauge
between two creeks with moorings and traffic, these echoes arrive in bursts of
several minutes, are always upward and saturate near a ceiling. In dense bursts
they dominate a running median, so a median filter does not remove them.

Since the contamination is one-sided, the water surface is the lower envelope
of the 5 s samples. It is estimated by the LOW_QUANTILE over a window of
WINDOW_SAMPLES (one minute), short enough that a 23 minute oscillation of 0.1 m
amplitude changes by under 3 cm within it. Samples more than THRESHOLD_M above
the envelope are discarded. A minute in which more than MAX_FLAGGED of the
samples are discarded is set missing, since the envelope itself is no longer
reliable there, and every other minute is the mean of its retained samples.

Usage:
    python despike_tad_5s.py --name senglea
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "insitu"

WINDOW_SAMPLES = 13             # one minute at 5 s
LOW_QUANTILE = 0.2
THRESHOLD_M = 0.08
MAX_FLAGGED = 0.25


def despike_day(s: pd.Series) -> tuple[pd.Series, int, int]:
    env = s.rolling(WINDOW_SAMPLES, center=True, min_periods=5).quantile(LOW_QUANTILE)
    flagged = (s - env) > THRESHOLD_M
    kept = s.mask(flagged)
    minute = kept.resample("1min")
    frac = flagged.resample("1min").mean()
    out = minute.mean().where(frac <= MAX_FLAGGED)
    return out, int(flagged.sum()), int((frac > MAX_FLAGGED).sum())


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--name", required=True)
    args = ap.parse_args(argv)

    cache = RAW / f"{args.name}_5s"
    files = sorted(cache.glob("*/*.csv.gz"))
    if not files:
        print(f"no 5 s files under {cache}", file=sys.stderr)
        return 1
    parts, n_samples, n_flagged, n_burst = [], 0, 0, 0
    for path in files:
        if path.stat().st_size <= 40:
            continue
        s = pd.read_csv(path, index_col=0, parse_dates=True)["level_m"]
        if s.empty:
            continue
        out, nf, nb = despike_day(s)
        parts.append(out)
        n_samples += len(s)
        n_flagged += nf
        n_burst += nb
    series = pd.concat(parts).dropna()
    path = RAW / f"{args.name}_wl_1min_despiked.csv"
    series.to_csv(path, header=["level_m"], date_format="%Y-%m-%d %H:%M")
    print(f"{args.name}: {n_samples} samples, {n_flagged} discarded "
          f"({n_flagged / n_samples:.2%}), {n_burst} minutes set missing in dense bursts")
    print(f"written {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

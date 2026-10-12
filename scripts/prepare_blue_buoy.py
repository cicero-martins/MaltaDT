"""Write the BLUE buoy record with the filled and spurious values removed.

The record supplied has its gaps filled and carries no flags. The filled
stretches correspond to failures of the buoy and are disregarded, as are the
sea temperature and salinity after the failure of their sensor on 8 November
2025, as stated by the group. The rows flagged by assess_blue_buoy.py are set
missing variable by variable, together with three further classes it reports.
For air pressure and air temperature, which are reported to 0.1 and so repeat
and align in measured data, the filled stretches are taken from the wind:

- wave heights and periods standing above their 70-minute running median by
  more than SPIKE_ABS and by more than the median itself;
- current speeds above CURRENT_SPIKE that exceed three times the 70-minute
  running median, the isolated values of November 2025 to May 2026;
- pressures on either side of a change above PRESSURE_STEP in ten minutes.

Rows recorded before the buoy reached its mooring are dropped. The result is
written to data/processed/blue_buoy_10min.csv with missing values left empty.

Usage:
    python prepare_blue_buoy.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assess_blue_buoy as ab  # noqa: E402

OUT = ab.ROOT / "data" / "processed" / "blue_buoy_10min.csv"
SENSOR_FAILURE = "2025-11-08 00:00"     # sea temperature and salinity
SPIKE_ABS = 1.0                         # m, and s for the period
CURRENT_SPIKE = 60.0                    # cm/s
PRESSURE_STEP = 2.0                     # hPa in ten minutes
GROUPS = {
    "current_abs_speed": ("current_abs_speed", "current_direction", "current_u", "current_v"),
    "sea_temperature": ("sea_temperature",),
    "salinity": ("salinity", "conductivity"),
    "sig_wave_height": ("sig_wave_height", "max_wave_height", "peak_wave_direction",
                        "peak_wave_period"),
    "air_pressure": ("air_pressure",),
    "air_temperature": ("air_temperature", "abs_humidity"),
    "wind_speed": ("wind_speed", "wind_direction", "gust_speed", "gust_direction"),
}


def main() -> int:
    if not ab.SOURCE.exists():
        print(f"missing {ab.SOURCE}", file=sys.stderr)
        return 1
    df = ab.load()
    off = (np.hypot(df.longitude - ab.MOORING[0], df.latitude - ab.MOORING[1])
           > ab.MOORING_TOLERANCE_DEG).to_numpy()
    moored = df.index >= df.index[np.flatnonzero(~off)[0]]

    bad = {}
    for lead in GROUPS:
        invalid, held, line = ab.flags(df, lead)
        bad[lead] = invalid | held | line | off
    # Air pressure and air temperature are reported to 0.1, so an hour without
    # change or four values on a line occur in measured data. Their filled
    # stretches are taken from the wind, which belongs to the same station.
    _, held, line = ab.flags(df, "wind_speed")
    for lead in ("air_pressure", "air_temperature"):
        invalid, _, _ = ab.flags(df, lead)
        bad[lead] = invalid | held | line | off

    for col in ("sea_temperature", "salinity"):
        bad[col] |= df.index >= SENSOR_FAILURE

    hs = df.sig_wave_height.where(~bad["sig_wave_height"])
    med = hs.rolling(7, center=True, min_periods=3).median()
    wave_spike = ((hs - med) > np.maximum(SPIKE_ABS, med)).to_numpy()
    for extra in ("max_wave_height", "peak_wave_period"):
        lo, hi = ab.RANGES[extra]
        wave_spike |= ~df[extra].between(lo, hi).to_numpy()
    bad["sig_wave_height"] |= wave_spike

    cs = df.current_abs_speed.where(~bad["current_abs_speed"])
    med = cs.rolling(7, center=True, min_periods=3).median()
    current_spike = ((cs > CURRENT_SPIKE) & (cs > 3 * med)).to_numpy()
    bad["current_abs_speed"] |= current_spike

    step = df.air_pressure.diff().abs().gt(PRESSURE_STEP).to_numpy()
    pressure_step = step | np.r_[step[1:], False]
    bad["air_pressure"] |= pressure_step

    out = df.copy()
    for lead, cols in GROUPS.items():
        for c in cols:
            out.loc[bad[lead], c] = np.nan
    out = out[moored].drop(columns=["latitude", "longitude", "dop"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, float_format="%.4f", date_format="%Y-%m-%d %H:%M:%S")

    n = len(out)
    print(f"{n} rows from {out.index[0]} to {out.index[-1]}, written to {OUT}\n")
    print(f"removed beyond the flags of the assessment: {int(wave_spike[moored].sum())} wave rows, "
          f"{int(current_spike[moored].sum())} current rows, "
          f"{int(pressure_step[moored].sum())} pressure rows\n")
    print("Rows retained, per cent, and days")
    for lead in GROUPS:
        k = int(out[lead].notna().sum())
        print(f"  {lead:20s} {100 * k / n:6.1f} {k / 144:8.1f}")
    print("\nRows retained by month, per cent")
    leads = ("current_abs_speed", "sig_wave_height", "wind_speed", "air_pressure",
             "sea_temperature")
    print(f"  {'month':8s} " + " ".join(f"{c[:14]:>15s}" for c in leads))
    months = out.index.to_period("M")
    for m in months.unique():
        sel = months == m
        print(f"  {m}  " + " ".join(f"{100 * out[c][sel].notna().mean():15.0f}" for c in leads))
    print("\nLongest stretches with current, waves, wind and pressure all present")
    full = out[["current_abs_speed", "sig_wave_height", "wind_speed", "air_pressure"]] \
        .notna().all(axis=1).to_numpy()
    r = ab.runs(full)
    starts = np.flatnonzero((r > 0) & (np.r_[0, r[:-1]] == 0))
    for s in sorted(starts, key=lambda s: -r[s])[:6]:
        print(f"  {out.index[s]} to {out.index[s + int(r[s]) - 1]}  {r[s] / 144:.1f} days")
    return 0


if __name__ == "__main__":
    sys.exit(main())

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
    python prepare_blue_buoy.py [--figure]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import assess_blue_buoy as ab  # noqa: E402

OUT = ab.ROOT / "data" / "processed" / "blue_buoy_10min.csv"
FIGURE = ab.ROOT / "figures" / "blue_buoy_treatment.png"
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--figure", action="store_true")
    args = ap.parse_args(argv)
    if not ab.SOURCE.exists():
        print(f"missing {ab.SOURCE}", file=sys.stderr)
        return 1
    df = ab.load()
    off = (np.hypot(df.longitude - ab.MOORING[0], df.latitude - ab.MOORING[1])
           > ab.MOORING_TOLERANCE_DEG).to_numpy()
    moored = df.index >= df.index[np.flatnonzero(~off)[0]]

    bad, filled, spurious = {}, {}, {}
    for lead in GROUPS:
        invalid, held, line = ab.flags(df, lead)
        bad[lead] = invalid | held | line | off
        filled[lead], spurious[lead] = held | line, invalid.copy()
    # Air pressure and air temperature are reported to 0.1, so an hour without
    # change or four values on a line occur in measured data. Their filled
    # stretches are taken from the wind, which belongs to the same station.
    _, held, line = ab.flags(df, "wind_speed")
    for lead in ("air_pressure", "air_temperature"):
        invalid, _, _ = ab.flags(df, lead)
        bad[lead] = invalid | held | line | off
        filled[lead], spurious[lead] = held | line, invalid.copy()

    sensor_out = np.asarray(df.index >= SENSOR_FAILURE)
    for col in ("sea_temperature", "salinity"):
        bad[col] |= sensor_out

    hs = df.sig_wave_height.where(~bad["sig_wave_height"])
    med = hs.rolling(7, center=True, min_periods=3).median()
    wave_spike = ((hs - med) > np.maximum(SPIKE_ABS, med)).to_numpy()
    for extra in ("max_wave_height", "peak_wave_period"):
        lo, hi = ab.RANGES[extra]
        wave_spike |= ~df[extra].between(lo, hi).to_numpy()
    bad["sig_wave_height"] |= wave_spike
    spurious["sig_wave_height"] |= wave_spike

    cs = df.current_abs_speed.where(~bad["current_abs_speed"])
    med = cs.rolling(7, center=True, min_periods=3).median()
    current_spike = ((cs > CURRENT_SPIKE) & (cs > 3 * med)).to_numpy()
    bad["current_abs_speed"] |= current_spike
    spurious["current_abs_speed"] |= current_spike

    step = df.air_pressure.diff().abs().gt(PRESSURE_STEP).to_numpy()
    pressure_step = step | np.r_[step[1:], False]
    bad["air_pressure"] |= pressure_step
    spurious["air_pressure"] |= pressure_step

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
    if args.figure:
        plot(df, bad, filled, spurious, sensor_out, ~np.asarray(moored))
    return 0


PLOTTED = (("current_abs_speed", "current speed, cm/s"),
           ("sig_wave_height", "significant wave height, m"),
           ("wind_speed", "wind speed, m/s"), ("air_pressure", "air pressure, hPa"),
           ("sea_temperature", "sea temperature, °C"), ("salinity", "salinity"))
C_KEPT = "#2a78d6"
C_FILLED = "#eb6834"
C_SPURIOUS = "#c2185b"
C_SENSOR = "#8a8984"
C_BEFORE = "#7b5ea7"


def plot(df, bad, filled, spurious, sensor_out, before) -> None:
    """The record as supplied, coloured by the reason each value is removed."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#8a8984",
                         "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e",
                         "ytick.color": "#52514e"})
    fig, axes = plt.subplots(len(PLOTTED), 1, figsize=(12.5, 12), sharex=True)
    n = len(df)
    for ax, (col, label) in zip(axes, PLOTTED):
        lo, hi = ab.RANGES[col]
        s = df[col].where(df[col].between(lo, hi))
        is_sensor = sensor_out if col in ("sea_temperature", "salinity") else np.zeros(n, bool)
        is_before = before
        is_spur = spurious[col] & ~is_before & ~is_sensor
        is_fill = filled[col] & ~is_before & ~is_sensor & ~is_spur
        kept = ~bad[col] & ~is_before
        ax.plot(df.index, s.where(kept), color=C_KEPT, lw=0.5)
        ax.plot(df.index, s.where(is_fill), color=C_FILLED, lw=1.1)
        ax.plot(df.index, s.where(is_sensor), color=C_SENSOR, lw=1.1)
        ax.plot(df.index, s.where(is_before), color=C_BEFORE, lw=0.8)
        ax.plot(df.index[is_spur], s[is_spur], ".", color=C_SPURIOUS, ms=4)
        share = lambda m: f"{100 * m.mean():.1f}"
        ax.set_title(f"{label}: kept {share(kept)} %, filled {share(is_fill)} %, "
                     f"spurious {share(is_spur)} %"
                     + (f", sensor out of operation {share(is_sensor)} %" if is_sensor.any() else "")
                     + f", before the mooring {share(is_before)} %", fontsize=8.5, loc="left")
        ax.set_ylabel(label)
        ax.grid(color="#e8e7e3", lw=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    handles = [plt.Line2D([], [], color=C_KEPT, lw=2, label="kept"),
               plt.Line2D([], [], color=C_FILLED, lw=2,
                          label="filled stretch, a failure of the buoy: held for an hour "
                                "or more, or four values or more on a straight line"),
               plt.Line2D([], [], color=C_SPURIOUS, marker=".", ls="", ms=9,
                          label="spurious value: outside the physical range, isolated spike, "
                                "or pressure step above 2 hPa in ten minutes"),
               plt.Line2D([], [], color=C_SENSOR, lw=2,
                          label="sensor out of operation, from 8 November 2025"),
               plt.Line2D([], [], color=C_BEFORE, lw=2,
                          label="before the mooring, inside the Grand Harbour")]
    fig.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.06, 0.0), frameon=False,
               fontsize=8.5, ncol=1)
    fig.suptitle("BLUE buoy record as supplied, coloured by the treatment of each value",
                 fontsize=10, x=0.06, ha="left")
    fig.tight_layout(rect=(0, 0.09, 1, 0.98))
    fig.savefig(FIGURE, dpi=140, facecolor="#fcfcfb")
    print(f"\nfigure written to {FIGURE}")


if __name__ == "__main__":
    sys.exit(main())

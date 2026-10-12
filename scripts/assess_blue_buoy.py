"""Assessment of the BLUE buoy record supplied by the group.

The file BlueInterpFull.csv holds the buoy record at ten-minute intervals with
no missing time stamp, the gaps of the original record having been filled
before it was supplied. A filled value cannot be told from a measured one by a
flag, since the file carries none, so the assessment looks for the traces a
filling leaves: a value held unchanged, and consecutive values lying on a
straight line. It also reports values that cannot be physical, the position of
the buoy through time, and the span over which each variable changes at all.

Flags applied, per variable:

- held: unchanged from the preceding row for at least HOLD_ROWS rows;
- line: at least LINE_ROWS consecutive rows with a constant, non-zero step;
- invalid: outside the physical range listed in RANGES, or with a position
  away from the mooring.

Usage:
    python assess_blue_buoy.py [--figure]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "raw" / "blue_buoy" / "BlueInterpFull.csv"
FIGURE = ROOT / "figures" / "blue_buoy_overview.png"

MOORING = (14.5388, 35.9294)        # lon, lat, median position after deployment
MOORING_TOLERANCE_DEG = 0.01        # about 1 km
HOLD_ROWS = 6                       # one hour
LINE_ROWS = 4
RANGES = {
    "current_abs_speed": (0.0, 300.0),      # cm/s
    "salinity": (30.0, 41.0),
    "sea_temperature": (10.0, 32.0),        # degrees Celsius
    "sig_wave_height": (0.0, 15.0),         # m
    "max_wave_height": (0.0, 30.0),
    "peak_wave_period": (0.0, 30.0),        # s
    "peak_wave_direction": (0.0, 360.0),
    "air_pressure": (950.0, 1050.0),        # hPa
    "air_temperature": (-5.0, 45.0),
    "wind_speed": (0.0, 60.0),              # m/s
}
PLOTTED = (("current_abs_speed", "current speed, cm/s"),
           ("sea_temperature", "sea temperature, °C"), ("salinity", "salinity"),
           ("sig_wave_height", "significant wave height, m"),
           ("air_pressure", "air pressure, hPa"), ("wind_speed", "wind speed, m/s"))

C_VALID = "#2a78d6"
C_FLAGGED = "#eb6834"


def load():
    import pandas as pd

    df = pd.read_csv(SOURCE)
    df["timestamp"] = pd.to_datetime(df["timestamp"], format="%d/%m/%Y %H:%M:%S")
    return df.set_index("timestamp")


def runs(mask):
    """Length of the run of True values each row belongs to, zero where False."""
    import pandas as pd

    m = pd.Series(np.asarray(mask, dtype=bool))
    group = (m != m.shift()).cumsum()
    return (m.groupby(group).transform("size") * m).to_numpy()


def flags(df, column):
    s = df[column]
    lo, hi = RANGES[column]
    invalid = ~s.between(lo, hi)
    step = s.diff()
    held = runs(step.eq(0)) >= HOLD_ROWS
    line = runs((step.diff().abs() < 1e-9) & step.ne(0)) >= LINE_ROWS
    return invalid.to_numpy(), held, line


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--figure", action="store_true")
    args = ap.parse_args(argv)
    if not SOURCE.exists():
        print(f"missing {SOURCE}", file=sys.stderr)
        return 1
    df = load()
    step = df.index.to_series().diff().dropna()
    print(f"{len(df)} rows, {df.index[0]} to {df.index[-1]}, "
          f"every step {step.min()} to {step.max()}, {df.isna().sum().sum()} empty cells\n")

    off = (np.hypot(df.longitude - MOORING[0], df.latitude - MOORING[1])
           > MOORING_TOLERANCE_DEG).to_numpy()
    zero = ((df.latitude == 0) | (df.longitude == 0)).to_numpy()
    moved = np.flatnonzero(~off)
    print(f"position: {zero.sum()} rows at zero, {off.sum() - zero.sum()} rows more than "
          f"{MOORING_TOLERANCE_DEG} degree from the mooring at {MOORING[0]} E, {MOORING[1]} N")
    first = df.index[moved[0]]
    print(f"  first row at the mooring {first}; before it the median position is "
          f"{df.longitude[:first].median():.4f} E, {df.latitude[:first].median():.4f} N")
    after = off & (df.index > first) & ~zero
    print(f"  rows away from the mooring after that date: {after.sum()}\n")

    print(f"Share of rows flagged, per variable (held for {HOLD_ROWS * 10} min or more, "
          f"on a straight line over {LINE_ROWS} rows or more, outside the physical range)")
    print(f"  {'variable':20s} {'invalid':>8s} {'held':>8s} {'line':>8s} {'clear':>8s}  "
          f"last change of value")
    flagged = {}
    for col in RANGES:
        invalid, held, line = flags(df, col)
        bad = invalid | held | line
        flagged[col] = bad
        changes = df.index[df[col].diff().ne(0).to_numpy()]
        print(f"  {col:20s} {invalid.mean():8.1%} {held.mean():8.1%} {line.mean():8.1%} "
              f"{1 - bad.mean():8.1%}  {changes[-1]}")
    print()

    for col in ("sea_temperature", "salinity"):
        s = df[col]
        last = df.index[s.diff().ne(0).to_numpy()][-1]
        print(f"{col}: constant at {s.iloc[-1]:.4f} from {last} to the end, "
              f"{(df.index[-1] - last).days} days")
    print()

    print("Clear rows by month, per cent, at the mooring")
    cols = ("current_abs_speed", "sea_temperature", "sig_wave_height", "air_pressure",
            "wind_speed")
    print(f"  {'month':8s} " + " ".join(f"{c[:14]:>15s}" for c in cols))
    months = df.index.to_period("M")
    for m in months.unique():
        sel = (months == m) & ~off
        if not sel.any():
            print(f"  {m}  not at the mooring")
            continue
        print(f"  {m}  " + " ".join(f"{100 * (1 - flagged[c][sel].mean()):15.0f}" for c in cols))
    print()

    ok = ~off
    for col, unit in (("current_abs_speed", "cm/s"), ("sig_wave_height", "m"),
                      ("wind_speed", "m/s"), ("air_pressure", "hPa")):
        v = df[col][ok & ~flagged[col]]
        print(f"{col}: clear values, median {v.median():.2f}, 99th percentile "
              f"{v.quantile(0.99):.2f}, maximum {v.max():.2f} {unit} on {v.idxmax()}")
    tsel = ok & ~flagged["sea_temperature"]
    print(f"sea_temperature: clear values {df.sea_temperature[tsel].min():.1f} to "
          f"{df.sea_temperature[tsel].max():.1f}, salinity "
          f"{df.salinity[ok & ~flagged['salinity']].min():.2f} to "
          f"{df.salinity[ok & ~flagged['salinity']].max():.2f}")
    dp = df.air_pressure.diff().abs()
    print(f"air_pressure: reported to {np.sort(dp[dp > 1e-6].round(2).unique())[0]:.1f} hPa, "
          f"largest change in ten minutes {dp[~flagged['air_pressure']].max():.1f} hPa")

    if args.figure:
        plot(df, flagged, off)
    return 0


def plot(df, flagged, off) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#8a8984",
                         "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e",
                         "ytick.color": "#52514e"})
    fig, axes = plt.subplots(len(PLOTTED), 1, figsize=(12, 11), sharex=True)
    for ax, (col, label) in zip(axes, PLOTTED):
        lo, hi = RANGES[col]
        s = df[col].where(df[col].between(lo, hi))
        bad = flagged[col] | off
        ax.plot(df.index, s.where(~bad), color=C_VALID, lw=0.5)
        ax.plot(df.index, s.where(bad), color=C_FLAGGED, lw=0.9)
        ax.set_ylabel(label)
        ax.grid(color="#e8e7e3", lw=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    axes[0].plot([], [], color=C_VALID, label="clear")
    axes[0].plot([], [], color=C_FLAGGED,
                 label="held, on a straight line, or away from the mooring")
    axes[0].legend(frameon=False, fontsize=8, ncol=2, loc="upper right")
    axes[0].set_title("BLUE buoy, ten-minute record as supplied, with the rows flagged by the "
                      "assessment", fontsize=9, loc="left")
    fig.tight_layout()
    fig.savefig(FIGURE, dpi=140, facecolor="#fcfcfb")
    print(f"\nfigure written to {FIGURE}")


if __name__ == "__main__":
    sys.exit(main())

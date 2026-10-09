"""A pressure band crossing a bounded basin, against the response on an unbounded sea.

Reads the runs written by `build_proudman_basin_test.py`. The band is uniform
across its path, so on an unbounded sea the response is the closed form of
`analyse_proudman_channel_test.py` with the distance measured from the starting
position of the band. Reported at each station, in units of the static
response, are the peak of that closed form and the peak of the modelled record
with Riemann boundaries on the west and east sides alone and on all four sides.

Usage:
    python analyse_proudman_basin_test.py [--figure]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyse_proudman_channel_test as ac  # noqa: E402
import build_proudman_basin_test as bb  # noqa: E402

RUNS = bb.OUT
FIGURE = bb.bp.ROOT / "figures" / "proudman_basin_test.png"
ETA_STATIC = ac.ETA_STATIC

C_THEORY = "#52514e"
C_WE = "#2a78d6"
C_FOUR = "#eb6834"


def load_his(case: str):
    import xarray as xr

    ds = xr.open_dataset(RUNS / case / "output" / f"{case}_his.nc")
    names = [s.strip() for s in ds["station_name"].values.astype(str)]
    t = (ds["time"].values - ds["time"].values[0]) / np.timedelta64(1, "s")
    wl = ds["waterlevel"].values
    return t, {n: wl[:, i] for i, n in enumerate(names)}


def unbounded(station: str, t, froude: float):
    """Closed form at the centre of the cell holding the station."""
    x = bb.STATIONS[station][0]
    xc = (np.floor((x + bb.HALF) / bb.DX) + 0.5) * bb.DX - bb.HALF
    return ac.closed_form(xc - bb.X_START, t, froude)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--figure", action="store_true")
    args = ap.parse_args(argv)

    rec = {}
    for fr in bb.FROUDE:
        for variant in bb.VARIANTS:
            case = bb.case_name(fr, variant)
            if not (RUNS / case / "output" / f"{case}_his.nc").exists():
                print(f"missing run: {case}", file=sys.stderr)
                return 1
            rec[(fr, variant)] = load_his(case)

    print(f"basin {2 * bb.HALF / 1e3:.0f} km across, band starting "
          f"{abs(bb.X_START) / 1e3:.0f} km west of the centre, peaks in units of the "
          f"static response\n")
    print(f"  {'Fr':>5s} {'station':8s} {'unbounded':>10s} {'west, east':>11s} "
          f"{'four sides':>11s} {'retained':>9s}")
    for fr in bb.FROUDE:
        for st in bb.STATIONS:
            t, two = rec[(fr, "west_east")]
            _, four = rec[(fr, "four_sides")]
            pk_u = np.max(np.abs(unbounded(st, t, fr)))
            pk_two, pk_4 = np.max(np.abs(two[st])), np.max(np.abs(four[st]))
            print(f"  {fr:5.2f} {st:8s} {pk_u / ETA_STATIC:10.3f} {pk_two / ETA_STATIC:11.3f} "
                  f"{pk_4 / ETA_STATIC:11.3f} {pk_4 / pk_u:9.2f}")

    if args.figure:
        plot(rec)
    return 0


def plot(rec) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#8a8984",
                         "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e",
                         "ytick.color": "#52514e"})
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex="col")
    for col, fr in enumerate(bb.FROUDE):
        for row, st in enumerate(("centre", "north")):
            ax = axes[row, col]
            t, two = rec[(fr, "west_east")]
            _, four = rec[(fr, "four_sides")]
            ax.plot(t / 60, unbounded(st, t, fr) * 100, color=C_THEORY, ls="--", lw=1.5,
                    label="unbounded sea, closed form")
            ax.plot(t / 60, two[st] * 100, color=C_WE, lw=1.7,
                    label="Riemann west and east, walls north and south")
            ax.plot(t / 60, four[st] * 100, color=C_FOUR, lw=1.7, label="Riemann on four sides")
            where = "centre of the basin" if st == "centre" else "15 km from the north side"
            ax.set_title(f"Fr = {fr:.1f}, {where}", fontsize=9, loc="left")
            ax.set_ylabel("water level, cm")
            ax.grid(color="#e8e7e3", lw=0.6)
            ax.set_axisbelow(True)
            ax.axhline(0, color="#d6d5d0", lw=0.8, zorder=0)
            for side in ("top", "right"):
                ax.spines[side].set_visible(False)
        axes[1, col].set_xlabel("time, min")
    axes[0, 0].legend(frameon=False, fontsize=8)
    axes[0, 0].set_xlim(30, 210)
    axes[0, 1].set_xlim(30, 120)
    fig.tight_layout()
    fig.savefig(FIGURE, dpi=150, facecolor="#fcfcfb")
    print(f"\nfigure written to {FIGURE}")


if __name__ == "__main__":
    sys.exit(main())

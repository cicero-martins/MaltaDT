"""Response at the stations for scenarios of a moving pressure disturbance.

Reads runs written by `build_longwave_scenario.py`. For each case and station
it reports the largest departure of the water level from rest, in units of the
static response to the pressure rise, the range, and the period of the largest
spectral peak between 5 and 120 minutes. With several cases the first is taken
as the reference, and the figure overlays the records.

Usage:
    python analyse_longwave_scenario.py outer01_h180_u31 v02_h180_u31 [--figure NAME]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_longwave_scenario as bl  # noqa: E402

COLOURS = ("#2a78d6", "#eb6834", "#1baf7a", "#52514e")
PANELS = ("shelf_60km_up", "shelf_30km_up", "offshore_4km", "senglea", "marsa_head",
          "msida_head")


def load_his(case: str):
    import xarray as xr

    ds = xr.open_dataset(bl.OUT / case / "output" / f"{case}_his.nc")
    names = [s.strip() for s in ds["station_name"].values.astype(str)]
    t = (ds["time"].values - ds["time"].values[0]) / np.timedelta64(1, "s")
    wl = ds["waterlevel"].values
    return t, {n: wl[:, i] for i, n in enumerate(names)}


def eta_static(case: str) -> float:
    """Static response to the pressure rise of the case, from its scenario file."""
    f = bl.OUT / case / "scenario.json"
    rise = json.loads(f.read_text())["rise"] if f.exists() else bl.P_RISE
    return rise / (bl.RHO * bl.G)


def dominant_period(t, eta) -> float:
    """Period in minutes of the largest spectral peak between 5 and 120 minutes."""
    dt = float(t[1] - t[0])
    n = 8 * eta.size
    f = np.fft.rfftfreq(n, dt)
    a = np.abs(np.fft.rfft((eta - eta.mean()) * np.hanning(eta.size), n))
    sel = (f >= 1 / (120 * 60)) & (f <= 1 / (5 * 60))
    return 1 / f[sel][np.argmax(a[sel])] / 60


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cases", nargs="+")
    ap.add_argument("--figure", default="", help="name of the figure under figures/")
    ap.add_argument("--labels", nargs="*", default=None)
    args = ap.parse_args(argv)

    rec = {}
    for case in args.cases:
        if not (bl.OUT / case / "output" / f"{case}_his.nc").exists():
            print(f"missing run: {case}", file=sys.stderr)
            return 1
        t, wl = load_his(case)
        es = eta_static(case)
        rec[case] = (t, {k: v / es for k, v in wl.items()})
        print(f"{case}: static response {es * 100:.2f} cm")

    print("\npeak and range in units of the static response, period in minutes\n")
    print(f"  {'station':15s} " + " ".join(f"{c[:24]:>26s}" for c in args.cases))
    print(f"  {'':15s} " + " ".join(f"{'peak':>8s} {'range':>8s} {'period':>8s}"
                                    for _ in args.cases))
    stations = list(rec[args.cases[0]][1])
    for st in stations:
        row = []
        for case in args.cases:
            t, wl = rec[case]
            eta = wl[st]
            row.append(f"{np.max(np.abs(eta)):8.2f} "
                       f"{(eta.max() - eta.min()):8.2f} "
                       f"{dominant_period(t, eta):8.1f}")
        print(f"  {st:15s} " + " ".join(row))

    if len(args.cases) > 1:
        ref = args.cases[0]
        print(f"\nPeak relative to {ref}")
        for case in args.cases[1:]:
            ratios = [np.max(np.abs(rec[case][1][st])) / np.max(np.abs(rec[ref][1][st]))
                      for st in stations]
            print(f"  {case:26s} " + " ".join(f"{r:5.2f}" for r in ratios))

    if args.figure:
        plot(rec, args.cases, args.labels or args.cases, args.figure)
    return 0


def plot(rec, cases, labels, name: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#8a8984",
                         "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e",
                         "ytick.color": "#52514e"})
    fig, axes = plt.subplots(3, 2, figsize=(11, 8.5), sharex=True)
    for ax, st in zip(axes.ravel(), PANELS):
        for case, label, colour in zip(cases, labels, COLOURS):
            t, wl = rec[case]
            ax.plot(t / 3600, wl[st], color=colour, lw=1.3, label=label)
        ax.set_title(st.replace("_", " "), fontsize=9, loc="left")
        ax.set_ylabel("level / static response")
        ax.grid(color="#e8e7e3", lw=0.6)
        ax.set_axisbelow(True)
        ax.axhline(0, color="#d6d5d0", lw=0.8, zorder=0)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    for ax in axes[-1]:
        ax.set_xlabel("time, h")
    axes[0, 0].legend(frameon=False, fontsize=8)
    fig.tight_layout()
    out = bl.ROOT / "figures" / name
    fig.savefig(out, dpi=150, facecolor="#fcfcfb")
    print(f"\nfigure written to {out}")


if __name__ == "__main__":
    sys.exit(main())

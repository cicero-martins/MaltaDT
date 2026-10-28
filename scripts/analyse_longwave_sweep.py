"""Response surface of the long-wave sweep.

Reads the history files of the scenarios run by `run_longwave_sweep.py` and
reduces each record to its largest departure from rest and its range, in units
of the static response to the pressure rise, and to the period of its largest
spectral peak between 5 and 120 minutes. The table of all scenarios and
stations is written to data/processed/longwave_sweep_response.csv, and the
figure shows the peak against the speed of the disturbance and the direction
it arrives from, for each length of the disturbance.

Usage:
    python analyse_longwave_sweep.py [--figure]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyse_longwave_scenario as an  # noqa: E402
import build_longwave_scenario as bl  # noqa: E402
import run_longwave_sweep as sw  # noqa: E402

TABLE = sw.ROOT / "data" / "processed" / "longwave_sweep_response.csv"
FIGURE = sw.ROOT / "figures" / "longwave_sweep_response.png"
FIXED = ("plateau_north", "sicily_coast", "plateau_east", "offshore_4km", "gh_mouth",
         "senglea", "french_creek", "dockyard_creek", "marsa_head", "mx_mouth",
         "sliema_creek", "msida_head", "pieta_head")
PANELS = (("offshore_4km", "4 km off the harbours"), ("senglea", "Senglea"),
          ("marsa_head", "Marsa, head of the Grand Harbour"),
          ("msida_head", "Msida Creek, head"))
FROM = {0: "S", 45: "SW", 90: "W", 135: "NW", 180: "N", 225: "NE", 270: "E", 315: "SE"}


def collect():
    import pandas as pd

    bl.OUT = sw.OUT
    rows = []
    for sc in sw.scenarios():
        case = sc["case"]
        if not (sw.OUT / case / "output" / f"{case}_his.nc").exists():
            continue
        t, wl = an.load_his(case)
        es = an.eta_static(case)
        for st in FIXED:
            eta = wl[st] / es
            rows.append(dict(case=case, sigma_km=sc["sigma"], heading=sc["heading"],
                             arrives_from=FROM[sc["heading"]], speed=sc["speed"], station=st,
                             peak=float(np.max(np.abs(eta))),
                             range=float(eta.max() - eta.min()),
                             period_min=float(an.dominant_period(t, eta))))
    return pd.DataFrame(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--figure", action="store_true")
    ap.add_argument("--mesh", default=sw.MESH, help="outer mesh of the sweep")
    ap.add_argument("--suffix", default="", help="suffix of the directory of cases, e.g. _thd")
    args = ap.parse_args(argv)
    sw.set_mesh(args.mesh, args.suffix)

    df = collect()
    if df.empty:
        print("no scenario has been run", file=sys.stderr)
        return 1
    n = df["case"].nunique()
    TABLE.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(TABLE, index=False, float_format="%.3f")
    print(f"{n} scenarios of {len(list(sw.scenarios()))}, table written to {TABLE}\n")

    print("Peak in units of the static response, over all scenarios")
    print(f"  {'station':15s} {'least':>7s} {'median':>7s} {'largest':>8s}  largest at")
    for st in FIXED:
        d = df[df.station == st]
        k = d.loc[d.peak.idxmax()]
        print(f"  {st:15s} {d.peak.min():7.2f} {d.peak.median():7.2f} {d.peak.max():8.2f}  "
              f"from {k.arrives_from}, {k.speed:.0f} m/s, {k.sigma_km:.0f} km")

    print("\nPeak at Senglea and at the head of Msida Creek, by direction of arrival, "
          "largest over the speeds")
    for sigma in sw.SIGMAS_KM:
        print(f"  length {sigma} km")
        for st in ("senglea", "msida_head"):
            d = df[(df.station == st) & (df.sigma_km == sigma)]
            by = d.groupby("heading").peak.max()
            print(f"    {st:11s} " + " ".join(f"{FROM[h]}:{by[h]:5.2f}" for h in by.index))

    print("\nPeak by speed, median over the directions")
    for sigma in sw.SIGMAS_KM:
        for st in ("offshore_4km", "senglea", "msida_head"):
            d = df[(df.station == st) & (df.sigma_km == sigma)]
            by = d.groupby("speed").peak.median()
            print(f"  {sigma} km {st:13s} " + " ".join(f"{s:.0f}:{by[s]:5.2f}" for s in by.index))

    if args.figure:
        plot(df)
    return 0


def plot(df) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#8a8984"})
    headings = sorted(FROM, key=lambda h: (h + 180) % 360)     # ordered by arrival, from N
    fig, axes = plt.subplots(len(sw.SIGMAS_KM), len(PANELS), figsize=(15, 6.2),
                             sharex=True, sharey=True)
    for j, (st, title) in enumerate(PANELS):
        d = df[df.station == st]
        vmax = d.peak.max()
        for i, sigma in enumerate(sw.SIGMAS_KM):
            ax = axes[i, j]
            grid = np.full((len(sw.SPEEDS), len(headings)), np.nan)
            for _, r in d[d.sigma_km == sigma].iterrows():
                grid[sw.SPEEDS.index(int(r.speed)), headings.index(int(r.heading))] = r.peak
            im = ax.imshow(grid, origin="lower", aspect="auto", cmap="viridis", vmin=0, vmax=vmax)
            for (a, b), v in np.ndenumerate(grid):
                if np.isfinite(v):
                    ax.text(b, a, f"{v:.1f}", ha="center", va="center", fontsize=7,
                            color="#fcfcfb" if v < 0.6 * vmax else "#0b0b0b")
            ax.set_xticks(range(len(headings)), [FROM[h] for h in headings])
            ax.set_yticks(range(len(sw.SPEEDS)), [f"{s * 3.6:.0f}" for s in sw.SPEEDS])
            if i == 0:
                ax.set_title(title, fontsize=9, loc="left")
            if j == 0:
                ax.set_ylabel(f"length {sigma} km\nspeed, km/h")
            if i == len(sw.SIGMAS_KM) - 1:
                ax.set_xlabel("direction the disturbance arrives from")
        fig.colorbar(im, ax=axes[:, j], label="peak / static response", shrink=0.85,
                     location="bottom", pad=0.14)
    fig.savefig(FIGURE, dpi=150, facecolor="#fcfcfb", bbox_inches="tight")
    print(f"\nfigure written to {FIGURE}")


if __name__ == "__main__":
    sys.exit(main())

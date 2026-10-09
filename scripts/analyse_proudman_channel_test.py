"""Response to a moving pressure disturbance against the linear closed form.

Reads the runs written by `build_proudman_channel_test.py`.

Reported for each Froude number:

- for the reference channel, the peak of the modelled record at each station
  beside the peak of the closed form, in units of the static response, and the
  root mean square departure of the record from the closed form relative to
  the peak of the latter;
- for the channels closed by a Riemann boundary, the signal returned by the
  boundary, taken as the difference from the reference record, relative to the
  peak of the reference at the same station, with and without the inverse
  barometer correction of pavBnd.

Usage:
    python analyse_proudman_channel_test.py [--figure]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_proudman_channel_test as bp  # noqa: E402

RUNS = bp.OUT
FIGURE = bp.ROOT / "figures" / "proudman_channel_test.png"
ETA_STATIC = bp.P_RISE / (bp.RHO * bp.G)       # m, magnitude of the static response

C_THEORY = "#52514e"
C_MODEL = "#2a78d6"
C_RIEMANN = "#eb6834"
C_RIEMANN_PAV = "#1baf7a"


def eta_s(xi):
    """Static response, a depression under the pressure rise."""
    return -ETA_STATIC * np.exp(-xi ** 2 / (2 * bp.SIGMA_X ** 2))


def d_eta_s(xi):
    return -xi / bp.SIGMA_X ** 2 * eta_s(xi)


def closed_form(x: float, t, froude: float):
    """Linear frictionless response to a disturbance switched on over a fluid at rest."""
    c = bp.CELERITY
    if abs(froude - 1.0) < 1e-9:
        return (c * t / 2 * d_eta_s(x - c * t)
                + eta_s(x - c * t) / 4 - eta_s(x + c * t) / 4)
    return (eta_s(x - froude * c * t) / (1 - froude ** 2)
            - eta_s(x - c * t) / (2 * (1 - froude))
            - eta_s(x + c * t) / (2 * (1 + froude)))


def load_his(case: str):
    import xarray as xr

    ds = xr.open_dataset(RUNS / case / "output" / f"{case}_his.nc")
    names = [s.strip() for s in ds["station_name"].values.astype(str)]
    t = (ds["time"].values - ds["time"].values[0]) / np.timedelta64(1, "s")
    wl = ds["waterlevel"].values
    x = ds["station_x_coordinate"].values
    return t, {n: wl[:, i] for i, n in enumerate(names)}, dict(zip(names, x))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--figure", action="store_true")
    args = ap.parse_args(argv)

    rec = {}
    for fr in bp.FROUDE:
        for variant in bp.VARIANTS:
            case = bp.case_name(fr, variant)
            if not (RUNS / case / "output" / f"{case}_his.nc").exists():
                print(f"missing run: {case}", file=sys.stderr)
                return 1
            rec[(fr, variant)] = load_his(case)

    print(f"static response {ETA_STATIC * 100:.2f} cm, sigma {bp.SIGMA_X / 1e3:.1f} km\n")
    print("Reference channel against the closed form, peaks in units of the static response")
    print(f"  {'Fr':>5s} {'station':8s} {'peak, closed form':>18s} {'peak, model':>12s} "
          f"{'ratio':>7s} {'rms / peak':>11s}")
    for fr in bp.FROUDE:
        t, wl, xs = rec[(fr, "reference")]
        for st in ("x100km", "x200km", "x300km"):
            # The record is taken at the centre of the cell holding the station.
            xc = (np.floor((xs[st] - bp.X_WEST) / bp.DX) + 0.5) * bp.DX + bp.X_WEST
            th = closed_form(xc, t, fr)
            pk_t, pk_m = np.max(np.abs(th)), np.max(np.abs(wl[st]))
            rms = np.sqrt(np.mean((wl[st] - th) ** 2))
            print(f"  {fr:5.2f} {st:8s} {pk_t / ETA_STATIC:18.3f} {pk_m / ETA_STATIC:12.3f} "
                  f"{pk_m / pk_t:7.3f} {rms / pk_t:11.4f}")
    print()

    # A boundary that admits no incoming characteristic cannot pass the forced
    # wave, whose velocity is U eta / h and not c eta / h. It returns a free
    # wave of amplitude (Fr - 1) / 2 times the forced wave, which is the static
    # response divided by 2 (1 + Fr) whatever the amplification.
    print("Signal returned by the Riemann boundary 50 km inside it, max|test - reference|,")
    print("in units of the static response and of the peak of the reference record")
    print(f"  {'Fr':>5s} {'first order':>12s} {'pavBnd = 0':>12s} {'pavBnd set':>12s} "
          f"{'/ peak':>8s}")
    for fr in bp.FROUDE:
        t, ref, _ = rec[(fr, "reference")]
        st = "x300km"
        row = []
        for variant in ("riemann", "riemann_pav"):
            _, test, _ = rec[(fr, variant)]
            row.append(np.max(np.abs(test[st] - ref[st])))
        print(f"  {fr:5.2f} {1 / (2 * (1 + fr)):12.3f} {row[0] / ETA_STATIC:12.3f} "
              f"{row[1] / ETA_STATIC:12.3f} {row[0] / np.max(np.abs(ref[st])):8.3f}")

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
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))

    for ax, fr in zip(axes[0], (0.6, 1.0)):
        t, wl, xs = rec[(fr, "reference")]
        st = "x300km"
        xc = (np.floor((xs[st] - bp.X_WEST) / bp.DX) + 0.5) * bp.DX + bp.X_WEST
        ax.plot(t / 60, closed_form(xc, t, fr) * 100, color=C_THEORY, ls="--", lw=1.5,
                label="closed form")
        ax.plot(t / 60, wl[st] * 100, color=C_MODEL, lw=1.8, label="D-Flow FM")
        ax.set_title(f"Fr = {fr:.1f}, 300 km from the start", fontsize=9, loc="left")
        ax.set_xlabel("time, min")
        ax.set_ylabel("water level, cm")
        ax.legend(frameon=False, fontsize=8)

    ax = axes[1, 0]
    t_end = bp.T_STOP
    frs = np.linspace(0.4, 1.3, 181)
    tt = np.arange(0.0, t_end + 1, 30.0)
    for x_km, ls in ((100, ":"), (300, "--")):
        peak = [np.max(np.abs(closed_form(x_km * 1e3, tt, f))) / ETA_STATIC for f in frs]
        ax.plot(frs, peak, color=C_THEORY, ls=ls, lw=1.5, label=f"closed form, {x_km} km")
    for st, marker in (("x100km", "s"), ("x300km", "o")):
        pts = [np.max(np.abs(rec[(fr, "reference")][1][st])) / ETA_STATIC for fr in bp.FROUDE]
        ax.plot(bp.FROUDE, pts, marker, color=C_MODEL, ms=6, mec="#fcfcfb", mew=1.5,
                label=f"D-Flow FM, {st[1:4]} km")
    ax.set_xlabel("Froude number of the disturbance")
    ax.set_ylabel("peak level / static response")
    ax.set_title("Amplification against speed and distance", fontsize=9, loc="left")
    ax.legend(frameon=False, fontsize=8)

    ax = axes[1, 1]
    fr = 1.0
    t, ref, _ = rec[(fr, "reference")]
    ax.plot(t / 60, ref["x300km"] * 100, color=C_THEORY, ls="--", lw=1.5,
            label="reference, no boundary")
    for variant, color, label in (("riemann", C_RIEMANN, "Riemann, pavBnd = 0"),
                                  ("riemann_pav", C_RIEMANN_PAV, "Riemann, pavBnd set")):
        tt, test, _ = rec[(fr, variant)]
        ax.plot(tt / 60, test["x300km"] * 100, color=color, lw=1.6, label=label)
    ax.set_xlim(100, 240)
    ax.set_xlabel("time, min")
    ax.set_ylabel("water level, cm")
    ax.set_title("Fr = 1.0, 50 km inside the Riemann boundary", fontsize=9, loc="left")
    ax.legend(frameon=False, fontsize=8)

    for ax in axes.ravel():
        ax.grid(color="#e8e7e3", lw=0.6)
        ax.set_axisbelow(True)
        ax.axhline(0, color="#d6d5d0", lw=0.8, zorder=0)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURE, dpi=150, facecolor="#fcfcfb")
    print(f"\nfigure written to {FIGURE}")


if __name__ == "__main__":
    sys.exit(main())

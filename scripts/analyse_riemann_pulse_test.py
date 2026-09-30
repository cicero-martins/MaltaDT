"""Reflection coefficients of the open boundary from the synthetic pulse test.

Reads the runs written by `build_riemann_pulse_test.py`. At every station the
reference record contains the incident wave alone and the test record the
incident and the reflected wave, so their difference is the reflected wave.

Reported for each boundary type, Riemann and prescribed water level:

- the peak reflection coefficient, max|test - reference| / max|reference|,
  signed by the reflected wave at its extremum relative to the incident peak;
- the spectral reflection coefficient |F(test - reference)| / |F(reference)| at
  frequencies where the incident spectrum holds at least a hundredth of its
  peak energy and the record spans at least one cycle;
- for the square basins, the peak coefficient against incidence angle beside
  the first-order value (1 - cos t)/(1 + cos t), and the mean level remaining
  over the basin once the pulse has left, as a fraction of the initial mean.

Usage:
    python analyse_riemann_pulse_test.py [--figure]
"""

from __future__ import annotations

import argparse
import math
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "model" / "tests" / "riemann_pulse"
FIGURE = ROOT / "figures" / "riemann_pulse_test.png"

CONFIGS = ("ch_s05", "ch_s20", "sq060_s05", "sq120_s05")
BASIN_HALF = {"sq060": 60e3, "sq120": 120e3}
OPEN_CELLS = {"ch": 3, "sq060": 4 * 80, "sq120": 4 * 160}
FREQS_CPH = (0.2, 0.5, 1.0, 2.0, 4.0)
ENERGY_FLOOR = 1e-2

# Reference palette of the dataviz skill, light surface.
C_REFERENCE = "#52514e"
C_RIEMANN = "#2a78d6"
C_WATERLEVEL = "#eb6834"
C_RIEMANN_LARGE = "#1baf7a"


def check_open_cells(case: str, expected: int) -> None:
    """The boundary must open every cell along it, as reported in the .dia.

    FM ignores all but the first polyline of a .pli file with only a warning,
    and a partly matched boundary leaves closed walls that reflect fully.
    """
    text = (RUNS / case / "output" / f"{case}.dia").read_text(errors="replace")
    found = [int(n) for n in re.findall(r"opened\s+(\d+)\s+cells", text)]
    if sum(found) != expected:
        raise RuntimeError(f"{case}: boundary opened {sum(found)} cells, expected {expected}")


def load_his(case: str):
    import xarray as xr

    ds = xr.open_dataset(RUNS / case / "output" / f"{case}_his.nc")
    names = [s.strip() for s in ds["station_name"].values.astype(str)]
    t = (ds["time"].values - ds["time"].values[0]) / np.timedelta64(1, "s")
    wl = ds["waterlevel"].values
    return t, {n: wl[:, i] for i, n in enumerate(names)}


def peak_coefficient(test, ref) -> float:
    refl = test - ref
    k = int(np.argmax(np.abs(refl)))
    return float(refl[k] / np.max(np.abs(ref)))


def spectral_coefficient(test, ref, dt: float):
    n = 8 * ref.size                    # zero padding for a smooth estimate
    f = np.fft.rfftfreq(n, dt) * 3600.0
    R = np.abs(np.fft.rfft(test - ref, n))
    I = np.abs(np.fft.rfft(ref, n))
    ok = I ** 2 >= ENERGY_FLOOR * np.max(I ** 2)
    f_min = 3600.0 / (ref.size * dt)     # one cycle over the record
    out = {}
    for fc in FREQS_CPH:
        k = int(np.argmin(np.abs(f - fc)))
        out[fc] = float(R[k] / I[k]) if ok[k] and fc >= f_min else None
    return out


def theory(angle_deg: float) -> float:
    c = math.cos(math.radians(angle_deg))
    return (1 - c) / (1 + c)


def basin_mean_level(case: str, half: float):
    """Mean level over the test square, per map time."""
    import xarray as xr

    ds = xr.open_dataset(RUNS / case / "output" / f"{case}_map.nc")
    x = ds["mesh2d_face_x"].values
    y = ds["mesh2d_face_y"].values
    inside = (np.abs(x) < half) & (np.abs(y) < half)
    s1 = ds["mesh2d_s1"].values[:, inside]
    t = (ds["time"].values - ds["time"].values[0]) / np.timedelta64(1, "s")
    return t, s1.mean(axis=1)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--figure", action="store_true")
    args = ap.parse_args(argv)

    records = {}
    for cfg in CONFIGS:
        geometry = cfg.split("_")[0]
        for variant in ("riemann", "waterlevel", "reference"):
            case = f"{cfg}_{variant}"
            if not (RUNS / case / "output").exists():
                print(f"missing run: {case}", file=sys.stderr)
                return 1
            if variant != "reference":
                check_open_cells(case, OPEN_CELLS[geometry])
            records[(cfg, variant)] = load_his(case)

    print("Peak reflection coefficient, signed, and spectral coefficient |R(f)|")
    print("(dash where the incident spectrum holds under 1 per cent of its peak")
    print("energy, or the record spans less than one cycle)\n")
    head = " ".join(f"{f'{f:g} cph':>8s}" for f in FREQS_CPH)
    print(f"  {'case':10s} {'station':14s} {'boundary':10s} {'peak':>8s} {head}")
    angles = {}
    for cfg in CONFIGS:
        t, ref = records[(cfg, "reference")]
        dt = float(t[1] - t[0])
        for variant in ("riemann", "waterlevel"):
            _, test = records[(cfg, variant)]
            for st in ref:
                rp = peak_coefficient(test[st], ref[st])
                rs = spectral_coefficient(test[st], ref[st], dt)
                cells = " ".join(f"{v:8.3f}" if v is not None else f"{'-':>8s}"
                                 for v in rs.values())
                print(f"  {cfg:10s} {st:14s} {variant:10s} {rp:+8.3f} {cells}")
                if cfg.startswith("sq") and "mid" not in st:
                    angles[(cfg, variant, float(st[3:7]))] = rp
        print()

    print("Square basins, peak coefficient against incidence angle")
    sq = [c for c in CONFIGS if c.startswith("sq")]
    print(f"  {'angle':>6s} {'theory':>8s} " +
          " ".join(f"{f'{c[:5]} Riemann':>14s}" for c in sq) +
          " " + " ".join(f"{f'{c[:5]} level':>12s}" for c in sq))
    for a in sorted({k[2] for k in angles}):
        print(f"  {a:6.1f} {theory(a):8.3f} " +
              " ".join(f"{angles[(c, 'riemann', a)]:+14.3f}" for c in sq) + " " +
              " ".join(f"{angles[(c, 'waterlevel', a)]:+12.3f}" for c in sq))
    print()

    print("Mean level over the test square, as a fraction of its initial value")
    means = {}
    for cfg in sq:
        half = BASIN_HALF[cfg.split("_")[0]]
        for variant in ("riemann", "waterlevel", "reference"):
            tm, m = basin_mean_level(f"{cfg}_{variant}", half)
            means[(cfg, variant)] = (tm, m)
            picks = [k for k, tv in enumerate(tm) if tv in (3600.0, 5400.0, 7200.0, tm[-1])]
            print(f"  {cfg:10s} {variant:11s} " + "  ".join(
                f"{tm[k] / 3600:.1f} h {m[k] / m[0]:+.4f}" for k in picks))

    if args.figure:
        plot(records, angles, means)
    return 0


def plot(records, angles, means) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#8a8984",
                         "axes.labelcolor": "#0b0b0b", "xtick.color": "#52514e",
                         "ytick.color": "#52514e"})
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    style = {"reference": dict(color=C_REFERENCE, ls="--", lw=1.5),
             "riemann": dict(color=C_RIEMANN, lw=2),
             "waterlevel": dict(color=C_WATERLEVEL, lw=2)}
    labels = {"reference": "reference, no boundary", "riemann": "Riemann",
              "waterlevel": "prescribed water level"}

    for ax, (cfg, st, title, xmax) in zip(
            (axes[0, 0], axes[0, 1]),
            (("ch_s05", "ch_180km", "Channel, 5 min pulse, 20 km inside the boundary", 240),
             ("sq060_s05", "sq_22.5deg", "120 km basin, boundary cell at 22.5°", 90))):
        for variant in ("reference", "waterlevel", "riemann"):
            t, rec = records[(cfg, variant)]
            ax.plot(t / 60, rec[st], label=labels[variant], **style[variant])
        ax.set_title(title, fontsize=9, loc="left")
        ax.set_xlabel("time, min")
        ax.set_ylabel("water level, m")
        ax.set_xlim(0, xmax)
        ax.axhline(0, color="#d6d5d0", lw=0.8, zorder=0)
    axes[0, 0].legend(frameon=False, fontsize=8)

    ax = axes[1, 0]
    a = np.linspace(0, 50, 101)
    ax.plot(a, [theory(v) for v in a], color=C_REFERENCE, ls="--", lw=1.5,
            label="first order, (1 − cos θ)/(1 + cos θ)")
    for cfg, color, label in (("sq060_s05", C_RIEMANN, "Riemann, 120 km basin"),
                              ("sq120_s05", C_RIEMANN_LARGE, "Riemann, 240 km basin")):
        pts = sorted(k[2] for k in angles if k[0] == cfg and k[1] == "riemann")
        ax.plot(pts, [abs(angles[(cfg, "riemann", p)]) for p in pts], "o-", color=color,
                ms=6, lw=2, mec="#fcfcfb", mew=2, label=label)
    ax.set_xlabel("incidence angle θ, degrees")
    ax.set_ylabel("|peak reflection coefficient|")
    ax.set_title("Reflection against incidence angle, 5 min pulse", fontsize=9, loc="left")
    ax.legend(frameon=False, fontsize=8)

    ax = axes[1, 1]
    for variant in ("reference", "waterlevel", "riemann"):
        tm, m = means[("sq060_s05", variant)]
        ax.plot(tm / 3600, m / m[0], label=labels[variant], **style[variant])
    ax.axhline(0, color="#d6d5d0", lw=0.8, zorder=0)
    ax.set_xlabel("time, h")
    ax.set_ylabel("mean level / initial mean level")
    ax.set_title("Volume retained in the 120 km basin", fontsize=9, loc="left")

    for ax in axes.ravel():
        ax.grid(color="#e8e7e3", lw=0.6)
        ax.set_axisbelow(True)
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    fig.tight_layout()
    fig.savefig(FIGURE, dpi=150, facecolor="#fcfcfb")
    print(f"\nfigure written to {FIGURE}")


if __name__ == "__main__":
    sys.exit(main())

"""Spatial pattern of the oscillations left by a long-wave scenario.

Reads the map output of runs written by `build_longwave_scenario.py` and
answers two questions the station records leave open.

1. Whether the oscillation that persists on the shelf after the disturbance
   has been lowered is a property of the shelf or a return from the open
   boundary. The records of the same scenario on two domains of different
   extent are compared over the window after the lowering, and the root mean
   square level over that window is mapped.
2. Whether the oscillation of the Grand Harbour near 22 minutes has the
   structure of a fundamental mode. The level at each face is fitted with a
   sinusoid of the period found at Senglea, over the window after the passage,
   and the amplitude and phase of the fit are mapped over the harbours.

Usage:
    python figure_longwave_modes.py outer01_h270_u31_t400 --larger outer02_h270_u31_t400
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyse_longwave_scenario as an  # noqa: E402
import build_longwave_scenario as bl  # noqa: E402

HARBOUR_BOX = (14.488, 35.872, 14.535, 35.912)
SHELF_BOX = (13.6, 35.4, 15.6, 37.2)


def scenario(case: str) -> dict:
    return json.loads((bl.OUT / case / "scenario.json").read_text())


def late_difference(case: str, larger: str) -> None:
    """Records of two domains over the window after the disturbance is lowered."""
    sc = scenario(case)
    t, a = an.load_his(case)
    _, b = an.load_his(larger)
    es = an.eta_static(case)
    late = t > sc["t_track"]
    print(f"Window after the lowering, {sc['t_track'] / 3600:.2f} to {t[-1] / 3600:.2f} h, "
          f"in units of the static response")
    print(f"  {'station':15s} {'rms, ' + case[:8]:>14s} {'rms, ' + larger[:8]:>14s} "
          f"{'rms of difference':>18s}")
    for st in a:
        n = min(a[st].size, b[st].size)
        x, y = a[st][:n][late[:n]] / es, b[st][:n][late[:n]] / es
        print(f"  {st:15s} {np.sqrt(np.mean(x ** 2)):14.3f} {np.sqrt(np.mean(y ** 2)):14.3f} "
              f"{np.sqrt(np.mean((x - y) ** 2)):18.3f}")


def harmonic_fit(t, s1, period_s: float):
    """Amplitude and phase of the sinusoid of given period fitted at every face."""
    w = 2 * math.pi / period_s
    design = np.c_[np.cos(w * t), np.sin(w * t), np.ones_like(t)]
    coef, *_ = np.linalg.lstsq(design, s1, rcond=None)
    amp = np.hypot(coef[0], coef[1])
    phase = np.degrees(np.arctan2(coef[1], coef[0]))
    return amp, phase


def main(argv=None) -> int:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import xugrid as xu
    from matplotlib.collections import PolyCollection

    ap = argparse.ArgumentParser()
    ap.add_argument("case")
    ap.add_argument("--larger", default="", help="the same scenario on a larger domain")
    ap.add_argument("--figure", default="longwave_modes.png")
    args = ap.parse_args(argv)

    if args.larger:
        late_difference(args.case, args.larger)

    sc = scenario(args.case)
    es = an.eta_static(args.case)
    ds = xu.open_dataset(bl.OUT / args.case / "output" / f"{args.case}_map.nc")
    grid = ds.grid
    t = (ds["time"].values - ds["time"].values[0]) / np.timedelta64(1, "s")
    s1 = ds["mesh2d_s1"].values / es
    xy = np.c_[grid.node_x, grid.node_y]
    fn = grid.face_node_connectivity
    fx, fy = grid.face_x, grid.face_y

    # Period of the basin from the station record at Senglea.
    th, wl = an.load_his(args.case)
    t_pass = sc["track_half"] / sc["speed"]
    after = th > t_pass + 1200.0
    period = an.dominant_period(th[after], wl["senglea"][after]) * 60.0
    print(f"\nperiod at Senglea after the passage {period / 60:.1f} min")

    late = t > sc["t_track"]
    rms = np.sqrt(np.nanmean(s1[late] ** 2, axis=0))
    sel_s = ((fx > SHELF_BOX[0]) & (fx < SHELF_BOX[2]) & (fy > SHELF_BOX[1]) & (fy < SHELF_BOX[3]))
    sel_h = ((fx > HARBOUR_BOX[0]) & (fx < HARBOUR_BOX[2]) & (fy > HARBOUR_BOX[1])
             & (fy < HARBOUR_BOX[3]))
    win = t > t_pass + 1200.0
    amp, phase = harmonic_fit(t[win], np.nan_to_num(s1[win][:, sel_h]), period)
    dry = np.nanstd(s1[:, sel_h], axis=0) < 1e-6
    amp[dry] = np.nan
    # Phase relative to the face of largest amplitude.
    k = int(np.nanargmax(amp))
    rel = (phase - phase[k] + 180.0) % 360.0 - 180.0
    print(f"harmonic fit at {period / 60:.1f} min over the harbours: amplitude "
          f"{np.nanmin(amp):.2f} to {np.nanmax(amp):.2f} of the static response")
    strong = amp > 0.5 * np.nanmax(amp)
    print(f"faces above half the largest amplitude: phase within "
          f"{np.nanpercentile(np.abs(rel[strong]), 95):.0f} degrees of the largest for 95 per cent")

    def polys(sel):
        return [xy[row[row >= 0]] for row in fn[sel]]

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#8a8984"})
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    aspect = 1 / math.cos(math.radians(36.0))

    ax = axes[0]
    pc = PolyCollection(polys(sel_s), array=rms[sel_s], cmap="viridis", linewidths=0)
    pc.set_clim(0, float(np.nanpercentile(rms[sel_s], 99)))
    ax.add_collection(pc)
    ax.set_xlim(SHELF_BOX[0], SHELF_BOX[2])
    ax.set_ylim(SHELF_BOX[1], SHELF_BOX[3])
    ax.set_title("Root mean square level after the disturbance is lowered", fontsize=9,
                 loc="left")
    fig.colorbar(pc, ax=ax, label="level / static response", shrink=0.8)

    ax = axes[1]
    pc = PolyCollection(polys(sel_h), array=amp, cmap="viridis", linewidths=0)
    ax.add_collection(pc)
    ax.set_title(f"Amplitude of the oscillation at {period / 60:.1f} min", fontsize=9, loc="left")
    fig.colorbar(pc, ax=ax, label="amplitude / static response", shrink=0.8)

    ax = axes[2]
    shown = np.where(amp > 0.1 * np.nanmax(amp), rel, np.nan)
    pc = PolyCollection(polys(sel_h), array=shown, cmap="twilight_shifted", linewidths=0)
    pc.set_clim(-180, 180)
    ax.add_collection(pc)
    ax.set_title("Phase relative to the face of largest amplitude", fontsize=9, loc="left")
    fig.colorbar(pc, ax=ax, label="degrees", shrink=0.8, ticks=(-180, -90, 0, 90, 180))

    for ax in axes[1:]:
        ax.set_xlim(HARBOUR_BOX[0], HARBOUR_BOX[2])
        ax.set_ylim(HARBOUR_BOX[1], HARBOUR_BOX[3])
    for ax in axes:
        ax.set_aspect(aspect)
        ax.set_facecolor("#e8e7e3")
    fig.tight_layout()
    out = bl.ROOT / "figures" / args.figure
    fig.savefig(out, dpi=150, facecolor="#fcfcfb")
    print(f"figure written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

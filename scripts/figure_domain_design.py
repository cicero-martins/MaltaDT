"""Figure: the design exercise for domain extent, resolution and layering.

Panel (a) places the candidate domains on the plateau bathymetry. Panel (b)
sets the resonant period of each element of the system against the observed
milghuba band, which is the argument for the domain extent. Panel (c) gives the
measured distribution of channel width inside the harbours against candidate
cell sizes, which is the argument for the interior resolution.

Usage:
    python figure_domain_design.py --dpi 300
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SHELF = ROOT / "data" / "external" / "emodnet_shelf.tif"
OUT = ROOT / "figures" / "domain_design.png"

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
HAIRLINE = "#c3c2b7"
GRID = "#e1e0d9"
LAND = "#e7e6e1"
BLUE = "#2a78d6"
ORANGE = "#eb6834"
BAND = "#f0efec"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]

MILGHUBA = (0.2, 2.0)

DOMAINS = [
    ("A", (14.44, 35.83, 14.62, 35.97), "#898781"),
    ("B", (14.05, 35.70, 15.00, 36.30), ORANGE),
    ("C", (13.90, 35.60, 15.30, 36.75), INK),
]

# Resonators, as label, period in minutes, frequency in cph, category. The
# shelf and the inlets are quarter-wave estimates. The harbours carry the range
# of the fundamental mode computed on the measured profile by
# estimate_basin_modes.py, plotted at the geometric mean of its limits.
RESONATORS = [
    ("Plateau to Sicily\nquarter wave", 156.4, 0.38, "shelf"),
    ("Plateau to Sicily\nhalf wave", 78.2, 0.77, "shelf"),
    ("Near plateau, 25 km", 48.6, 1.24, "shelf"),
    ("Grand Harbour", "14.5 to 18.4", 3.67, "harbour"),
    ("Marsamxett", "10.4 to 12.8", 5.20, "harbour"),
    ("Inlet, 1 km", 6.1, 9.76, "inlet"),
    ("Inlet, 600 m", 4.0, 14.86, "inlet"),
]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import rasterio
    from matplotlib.colors import LinearSegmentedColormap
    from matplotlib.patches import Rectangle

    sys.path.insert(0, str(ROOT / "scripts"))
    from domain_design_estimate import load_harbour_grids

    if not SHELF.exists():
        print(f"missing {SHELF}", file=sys.stderr)
        return 1

    fig = plt.figure(figsize=(13.4, 6.0), facecolor=SURFACE)
    gs = fig.add_gridspec(1, 3, width_ratios=[1.02, 1.20, 1.02], wspace=0.30,
                          left=0.042, right=0.988, top=0.775, bottom=0.215)

    fig.text(0.045, 0.945, "Domain extent, interior resolution and vertical layering",
             color=INK, fontsize=15, fontweight="semibold", ha="left")
    fig.text(0.045, 0.895,
             "The arguments are drawn from the measured bathymetry rather than "
             "from nominal figures.", color=INK_2, fontsize=9.6, ha="left")

    headings = []

    def panel(ax, title, subtitle):
        headings.append((ax, title, subtitle))
        for sp in ax.spines.values():
            sp.set_color(HAIRLINE)
            sp.set_linewidth(0.8)
        ax.tick_params(colors=MUTED, labelsize=7.8, length=3, width=0.7)

    # ---------- (a) candidate domains ----------
    ax1 = fig.add_subplot(gs[0, 0])
    src = rasterio.open(SHELF)
    z = src.read(1).astype(float)
    if src.nodata is not None:
        z[z == src.nodata] = np.nan
    ext = (src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top)
    cmap = LinearSegmentedColormap.from_list("depth", SEQ[::-1], N=256)
    cmap.set_bad(LAND)
    d = np.where(z < 0, -z, np.nan)
    ax1.set_facecolor(LAND)
    ax1.imshow(d, extent=ext, origin="upper", cmap=cmap, vmin=0, vmax=250,
               interpolation="nearest")
    for name, (a, b, c_, d_), col in DOMAINS:
        ax1.add_patch(Rectangle((a, b), c_ - a, d_ - b, fill=False,
                                edgecolor=col, linewidth=1.8, zorder=5))
        lx, ly = (a + 0.03, d_ - 0.04) if name != "A" else (c_ + 0.05, d_ + 0.02)
        ax1.text(lx, ly, name, color=col, fontsize=11,
                 fontweight="semibold", va="top", zorder=6)
    ax1.plot(14.51, 35.90, marker="o", ms=4, color=INK, zorder=7)
    import matplotlib.patheffects as pe
    ax1.annotate("Valletta", xy=(14.51, 35.90), xytext=(14.68, 35.86),
                 color=INK, fontsize=8.2, va="center", ha="left", zorder=7,
                 arrowprops=dict(arrowstyle="-", color=INK, linewidth=0.7),
                 path_effects=[pe.withStroke(linewidth=2.4, foreground=SURFACE)])
    ax1.set_aspect(1 / math.cos(math.radians(36.2)))
    ax1.set_xlim(13.88, 15.32)
    ax1.set_ylim(35.58, 36.78)
    panel(ax1, "(a)  Candidate domains",
          "Plateau depth, 0 to 250 m. Land and no data in grey.")

    # ---------- (b) resonance against the band ----------
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.axvspan(MILGHUBA[0], MILGHUBA[1], color=BAND, zorder=0)
    ax2.text(math.sqrt(MILGHUBA[0] * MILGHUBA[1]), 7.35,
             "observed milgħuba band\n0.2 to 2 cph", color=INK_2, fontsize=8.6,
             ha="center", va="top")
    colours = {"shelf": ORANGE, "harbour": BLUE, "inlet": MUTED}
    for i, (lab, T, f, kind) in enumerate(RESONATORS):
        y = len(RESONATORS) - 1 - i
        ax2.plot([f], [y], marker="o", ms=9, color=colours[kind], zorder=4,
                 markeredgecolor=SURFACE, markeredgewidth=2)
        ax2.text(f * 1.22, y, f"{lab.replace(chr(10), ' ')}  "
                 f"({T if isinstance(T, str) else format(T, '.0f')} min)",
                 color=INK, fontsize=8.4, va="center", ha="left", zorder=5)
    ax2.set_xscale("log")
    ax2.set_xlim(0.12, 60)
    ax2.set_ylim(-0.8, 7.6)
    ax2.set_yticks([])
    ax2.set_xticks([0.2, 0.5, 1, 2, 5, 10, 20])
    ax2.set_xticklabels(["0.2", "0.5", "1", "2", "5", "10", "20"])
    ax2.set_xlabel("Resonant frequency, cycles per hour", color=INK_2, fontsize=9)
    ax2.xaxis.grid(True, color=GRID, linewidth=0.7)
    ax2.set_axisbelow(True)
    panel(ax2, "(b)  Where each element resonates",
          "Shelf in orange, harbours in blue, inlets in grey.")

    # ---------- (c) channel width ----------
    ax3 = fig.add_subplot(gs[0, 2])
    _, t, wet, width, ridge, cx, cy = load_harbour_grids()
    anchors = {}
    HARB = {"Grand Harbour": ((14.502, 35.880, 14.528, 35.900), BLUE),
            "Marsamxett": ((14.490, 35.892, 14.518, 35.909), ORANGE)}
    for name, ((a, b, c_, d_), col) in HARB.items():
        r0, c0 = ~t * (a, d_)
        r1, c1 = ~t * (c_, b)
        c0, r0, c1, r1 = int(c0), int(r0), int(c1), int(r1)
        ww = np.sort(width[r0:r1, c0:c1][ridge[r0:r1, c0:c1]])
        frac = 100 * np.arange(1, ww.size + 1) / ww.size
        ax3.plot(ww, frac, color=col, linewidth=2.0, label=name, zorder=4)
        anchors[name] = ww
    # Direct labels are omitted deliberately. The two curves cross and run
    # close together over much of the range, so a label placed beside one sits
    # on the other. The legend carries identity without that ambiguity.
    # Guides for the proposed interior cell size only. Four cells carry the
    # conveyance of a channel, eight resolve the flow across it.
    for k, lab in ((4, "4 cells"), (8, "8 cells")):
        x = 15 * k
        ax3.axvline(x, color=MUTED, linewidth=0.9, zorder=1)
        ax3.text(x, 101.5, lab, color=MUTED, fontsize=7.6,
                 ha="center", va="bottom", zorder=5)
    ax3.set_xscale("log")
    ax3.set_xlim(18, 600)
    ax3.set_ylim(0, 100)
    ax3.set_xticks([20, 50, 100, 200, 500])
    ax3.set_xticklabels(["20", "50", "100", "200", "500"])
    ax3.set_xlabel("Channel width, m", color=INK_2, fontsize=9)
    ax3.set_ylabel("Percentage of channel length below", color=INK_2, fontsize=9)
    ax3.yaxis.grid(True, color=GRID, linewidth=0.7)
    ax3.set_axisbelow(True)
    leg = ax3.legend(loc="lower right", frameon=False, fontsize=8.2)
    for txt in leg.get_texts():
        txt.set_color(INK_2)
    panel(ax3, "(c)  Measured channel width",
          "On the ridge of the distance transform, against 15 m cells.")

    fig.text(0.042, 0.085,
             "Panel (b) carries the argument for the extent. The harbours and their "
             "inlets resonate above the observed band while the plateau resonates "
             "within it, so the harbours\nrespond to a shelf-scale oscillation rather "
             "than generating one. Domain A holds no resonator in the band and cannot "
             "produce the signal under study, while\ndomain B was sized at 28,500 cells "
             "against 25,900 for domain A, an increase of a tenth for the whole "
             "plateau.",
             color=MUTED, fontsize=8.2, ha="left", va="top")

    # Headings are placed after the draw, in figure coordinates, so that they
    # align across panels despite the fixed aspect ratio of panel (a).
    fig.canvas.draw()
    for ax, title, subtitle in headings:
        x = ax.get_position().x0
        fig.text(x, 0.845, title, color=INK, fontsize=10.5,
                 fontweight="semibold", ha="left", va="bottom")
        fig.text(x, 0.800, subtitle, color=INK_2, fontsize=8.5,
                 ha="left", va="bottom")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=args.dpi, facecolor=SURFACE)
    print(f"Written {args.out} at {args.dpi} dpi")
    return 0


if __name__ == "__main__":
    sys.exit(main())

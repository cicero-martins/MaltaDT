"""Figure: the merged bathymetry and the coastline, at island and harbour scale.

Three panels. The first shows the extent and coverage of the merged product
over the Maltese Islands with the coastline overlaid. The second and third
show the Valletta harbours at the two resolutions available, 10 m from the
dataset supplied by the host group and 115 m from the public EMODnet product,
on a shared colour scale so that the comparison is direct.

Encoding follows the diverging rule: the data spans a meaningful zero, namely
sea level, so the scale is two hues about a neutral gray midpoint rather than
a single ramp or a rainbow. Cool below zero and warm above, with the neutral
placed exactly at the shoreline. Panel (a) carries its own scale because the
open shelf reaches 262 m and would otherwise compress the harbours to a single
tone; panels (b) and (c) share one scale, which is what makes them comparable.

Hues are taken from the reference palette: the blue sequential ramp for the
submerged arm, the categorical red for the emerged arm, and the documented
diverging midpoint. Chrome and ink follow the same reference.

Usage:
    python figure_bathymetry_overview.py
    python figure_bathymetry_overview.py --dpi 300
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
BATHY = ROOT / "data" / "processed" / "mepa_4036_merged_10m_wgs84.tif"
COAST = ROOT / "data" / "processed" / "malta_coastline_wgs84.gpkg"
EMOD = ROOT / "data" / "external" / "emodnet_valletta.tif"
OUT = ROOT / "figures" / "bathymetry_overview.png"

# Reference palette, light mode.
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
MUTED = "#898781"
HAIRLINE = "#c3c2b7"
NEUTRAL = "#f0efec"        # documented diverging midpoint
NODATA = "#e7e6e1"

# Submerged arm, blue sequential ramp, deep to shallow.
COOL = ["#0d366b", "#184f95", "#256abf", "#3987e5", "#6da7ec", "#9ec5f4", "#cde2fb"]
# Emerged arm, warm, terminating at the categorical red.
WARM = ["#f6c9b4", "#f0a184", "#e87257", "#e34948", "#a8302f"]

VALLETTA = (14.478, 35.878, 14.545, 35.912)   # lon0, lat0, lon1, lat1


def diverging_cmap():
    from matplotlib.colors import LinearSegmentedColormap
    return LinearSegmentedColormap.from_list(
        "topobathy", COOL + [NEUTRAL] + WARM, N=512)


def read(path, window=None):
    import rasterio
    from rasterio.windows import from_bounds
    src = rasterio.open(path)
    if window is None:
        z = src.read(1).astype(float)
        bounds = src.bounds
    else:
        w = from_bounds(*window, transform=src.transform)
        z = src.read(1, window=w).astype(float)
        bounds = rasterio.windows.bounds(w, src.transform)
    if src.nodata is not None and not np.isnan(src.nodata):
        z[z == src.nodata] = np.nan
    return z, (bounds[0], bounds[2], bounds[1], bounds[3])


def draw_panel(ax, z, extent, norm, cmap, title, subtitle=None):
    ax.set_facecolor(NODATA)
    im = ax.imshow(z, extent=extent, origin="upper", cmap=cmap, norm=norm,
                   interpolation="nearest")
    # Title and subtitle are drawn as text rather than through set_title, so
    # that the two sit on separate lines instead of colliding above the axes.
    ax.text(0, 1.055, title, transform=ax.transAxes, color=INK,
            fontsize=10.5, fontweight="semibold", va="bottom", ha="left")
    if subtitle:
        ax.text(0, 1.012, subtitle, transform=ax.transAxes, color=INK_2,
                fontsize=8.6, va="bottom", ha="left")
    for s in ax.spines.values():
        s.set_color(HAIRLINE)
        s.set_linewidth(0.8)
    ax.tick_params(colors=MUTED, labelsize=7.5, length=3, width=0.7)
    return im


def scale_bar(ax, extent, km, label):
    """A scale bar, since a geographic axis in degrees does not convey distance."""
    import math
    lat = (extent[2] + extent[3]) / 2
    deg = km / (111.320 * math.cos(math.radians(lat)))
    x0 = extent[0] + (extent[1] - extent[0]) * 0.06
    y0 = extent[2] + (extent[3] - extent[2]) * 0.07
    ax.plot([x0, x0 + deg], [y0, y0], color=INK, lw=2.0, solid_capstyle="butt",
            zorder=6)
    ax.text(x0 + deg / 2, y0 + (extent[3] - extent[2]) * 0.018, label,
            color=INK, fontsize=7.5, ha="center", va="bottom", zorder=6)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dpi", type=int, default=220)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import geopandas as gpd
    from matplotlib.colors import TwoSlopeNorm
    from matplotlib.patches import Rectangle

    for p in (BATHY, COAST, EMOD):
        if not p.exists():
            print(f"missing input: {p}", file=sys.stderr)
            return 1

    cmap = diverging_cmap()
    cmap.set_bad(NODATA)
    coast = gpd.read_file(COAST)

    z_all, ext_all = read(BATHY)
    z_val, ext_val = read(BATHY, VALLETTA)
    z_emo, ext_emo = read(EMOD)

    fig = plt.figure(figsize=(11.0, 9.4), facecolor=SURFACE)
    gs = fig.add_gridspec(2, 2, height_ratios=[1.34, 1.0],
                          hspace=0.22, wspace=0.11,
                          left=0.055, right=0.90, top=0.885, bottom=0.075)

    fig.text(0.055, 0.966, "Maltese Islands bathymetry and coastline",
             color=INK, fontsize=15, fontweight="semibold", ha="left")
    fig.text(0.055, 0.941,
             "CDI 4036_MEPA, LiDAR and sonar merged at 10 m, with the coastline "
             "supplied separately. Both in EPSG:4326.",
             color=INK_2, fontsize=9.6, ha="left")

    # (a) islands
    ax1 = fig.add_subplot(gs[0, :])
    n1 = TwoSlopeNorm(vmin=-150, vcenter=0.0, vmax=150)
    im1 = draw_panel(ax1, z_all, ext_all, n1, cmap,
                     "(a)  Extent and coverage",
                     "Grey carries no data. The LiDAR reaches only a coastal strip, "
                     "so island interiors are blank.")
    coast.boundary.plot(ax=ax1, color=INK, linewidth=0.45, zorder=4)
    ax1.add_patch(Rectangle((VALLETTA[0], VALLETTA[1]),
                            VALLETTA[2] - VALLETTA[0], VALLETTA[3] - VALLETTA[1],
                            fill=False, edgecolor=INK, linewidth=1.5, zorder=5))
    ax1.text(VALLETTA[2] + 0.006, VALLETTA[3], "Valletta, panels (b) and (c)",
             color=INK, fontsize=8.6, va="top", ha="left", zorder=6)
    # Trim to the extent that actually carries data, with a small margin.
    cols = np.where(np.isfinite(z_all).any(axis=0))[0]
    rows = np.where(np.isfinite(z_all).any(axis=1))[0]
    dx = (ext_all[1] - ext_all[0]) / z_all.shape[1]
    dy = (ext_all[3] - ext_all[2]) / z_all.shape[0]
    ax1.set_xlim(ext_all[0] + dx * (cols[0] - 4), ext_all[0] + dx * (cols[-1] + 4))
    ax1.set_ylim(ext_all[3] - dy * (rows[-1] + 4), ext_all[3] - dy * (rows[0] - 4))
    ax1.set_aspect(1 / np.cos(np.radians(35.9)))
    scale_bar(ax1, ext_all, 10, "10 km")

    cax1 = fig.add_axes([0.915, 0.535, 0.016, 0.30])
    cb1 = fig.colorbar(im1, cax=cax1, extend="both")
    cb1.set_label("Elevation, m relative to the coastline zero", color=INK_2,
                  fontsize=8.6)
    cb1.ax.tick_params(colors=MUTED, labelsize=7.5, length=3, width=0.7)
    cb1.outline.set_edgecolor(HAIRLINE)

    # (b) and (c) share a scale
    n2 = TwoSlopeNorm(vmin=-45, vcenter=0.0, vmax=60)

    ax2 = fig.add_subplot(gs[1, 0])
    draw_panel(ax2, z_val, ext_val, n2, cmap,
               "(b)  Valletta at 10 m, CDI 4036_MEPA",
               "The inlets are resolved by 10 to 30 cells across.")
    coast.boundary.plot(ax=ax2, color=INK, linewidth=0.7, zorder=4)

    ax3 = fig.add_subplot(gs[1, 1])
    im3 = draw_panel(ax3, z_emo, ext_emo, n2, cmap,
                     "(c)  The same extent at 115 m, EMODnet DTM 2024",
                     "The inlets occupy one to three cells and are lost.")
    coast.boundary.plot(ax=ax3, color=INK, linewidth=0.7, zorder=4)

    for ax, ext in ((ax2, ext_val), (ax3, ext_emo)):
        ax.set_xlim(VALLETTA[0], VALLETTA[2])
        ax.set_ylim(VALLETTA[1], VALLETTA[3])
        ax.set_aspect(1 / np.cos(np.radians(35.9)))
        scale_bar(ax, (VALLETTA[0], VALLETTA[2], VALLETTA[1], VALLETTA[3]),
                  1, "1 km")
    ax3.tick_params(labelleft=False)

    for ax, lab, xy in (
        (ax2, "Grand Harbour", (14.5215, 35.8905)),
        (ax2, "Marsamxett", (14.4985, 35.9022)),
        (ax2, "Valletta", (14.5135, 35.8975)),
    ):
        ax.text(*xy, lab, color=INK, fontsize=8.0, ha="center", va="center",
                zorder=7,
                path_effects=[__import__("matplotlib.patheffects", fromlist=["x"])
                              .withStroke(linewidth=2.2, foreground=SURFACE)])

    cax2 = fig.add_axes([0.915, 0.105, 0.016, 0.24])
    cb2 = fig.colorbar(im3, cax=cax2, extend="both")
    cb2.set_label("Elevation, m", color=INK_2, fontsize=8.6)
    cb2.ax.tick_params(colors=MUTED, labelsize=7.5, length=3, width=0.7)
    cb2.outline.set_edgecolor(HAIRLINE)

    fig.text(0.055, 0.022,
             "Panels (b) and (c) share a colour scale. Panel (a) carries its own, the "
             "open shelf reaching 262 m, and values beyond the bar ends are clipped.\n"
             "The neutral tone marks sea level, where the two datasets agree to a "
             "median of zero.",
             color=MUTED, fontsize=8.0, ha="left")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(args.out, dpi=args.dpi, facecolor=SURFACE)
    print(f"Written {args.out} at {args.dpi} dpi")
    return 0


if __name__ == "__main__":
    sys.exit(main())

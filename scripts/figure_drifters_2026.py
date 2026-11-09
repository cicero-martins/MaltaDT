"""One figure for each deployment of the drifters of 2026, over its time inside domain B.

Each figure maps the drifting fixes of both units over the bed levels of mesh
v03, with the elapsed time marked every six hours, and gives the speed of each
unit from fix to fix with the wind at the BLUE buoy, and the temperature of
the sensors. The record is that written by prepare_drifters_2026.py.

Usage:
    python figure_drifters_2026.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.tri as mtri  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import xarray as xr  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "data" / "processed" / "drifters_2026.csv"
MESH = ROOT / "data" / "processed" / "mesh_v03" / "malta_v03_net.nc"
COAST = ROOT / "data" / "processed" / "malta_coastline_wgs84.gpkg"
BLUE = ROOT / "data" / "processed" / "blue_buoy_10min.csv"
BLUE_POS = (14.5388, 35.9294)
COLOURS = {9: "#2a78d6", 11: "#eb6834"}
DEPLOYMENTS = {
    "may": dict(title="20 to 21 May 2026", extent=(14.355, 14.485, 35.925, 36.015),
                levels=[-80, -60, -40, -30, -20, -10, -5, 0], blue=False),
    "jul": dict(title="6 to 8 July 2026", extent=(14.30, 14.90, 35.68, 36.20),
                levels=[-1000, -500, -300, -200, -175, -150, -125, -100, -75, -50, -25, 0],
                blue=True),
}
MARK_HOURS = 6


def mesh_bed():
    n = xr.open_dataset(MESH)
    x, y, z = n.mesh2d_node_x.values, n.mesh2d_node_y.values, n.mesh2d_node_z.values
    faces = n.mesh2d_face_nodes.values
    tris = []
    for f in faces:
        f = f[np.isfinite(f)].astype(int) - int(n.mesh2d_face_nodes.attrs.get("start_index", 0))
        tris += [[f[0], f[k], f[k + 1]] for k in range(1, f.size - 1)]
    return mtri.Triangulation(x, y, np.array(tris)), z


def figure(key, spec, d, tri, z, coast, blue):
    tracks = {b: d[(d.deployment == f"{b}_{key}") & d.in_domain_b] for b in COLOURS}
    t0 = min(g.time.iloc[0] for g in tracks.values())
    t1 = max(g.time.iloc[-1] for g in tracks.values())

    fig = plt.figure(figsize=(11, 6.2))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.35, 1], hspace=0.3, wspace=0.22)
    ax = fig.add_subplot(gs[:, 0])
    x0, x1, y0, y1 = spec["extent"]
    tc = ax.tricontourf(tri, z, levels=spec["levels"], cmap="Blues_r", extend="min", zorder=0)
    gpd.GeoSeries([coast]).plot(ax=ax, color="#d9d6cf", edgecolor="#9a978f", lw=0.5, zorder=1)
    for b, g in tracks.items():
        ax.plot(g.lon, g.lat, color=COLOURS[b], lw=1.6, zorder=3, label=f"unit {b}")
        ax.plot(g.lon.iloc[0], g.lat.iloc[0], "o", color=COLOURS[b], ms=6, mec="k", mew=0.6,
                zorder=4)
        ax.plot(g.lon.iloc[-1], g.lat.iloc[-1], "s", color=COLOURS[b], ms=6, mec="k", mew=0.6,
                zorder=4)
        # elapsed time from the first drifting fix of either unit
        h = (g.time - t0).dt.total_seconds() / 3600
        for mark in np.arange(MARK_HOURS, h.max() + 1e-6, MARK_HOURS):
            i = int(np.argmin(np.abs(h.values - mark)))
            if abs(h.values[i] - mark) > 0.6:
                continue
            ax.plot(g.lon.iloc[i], g.lat.iloc[i], "o", color="white", mec=COLOURS[b], ms=4,
                    mew=1.2, zorder=4)
            # labels on opposite sides, since the tracks of May overlap
            side = (-24, -2) if key == "may" and b == 11 else (5, -2)
            ax.annotate(f"{mark:.0f} h", (g.lon.iloc[i], g.lat.iloc[i]), fontsize=6.5,
                        xytext=side, textcoords="offset points", color="#0b0b0b", zorder=5)
    if spec["blue"]:
        ax.plot(*BLUE_POS, "^", color="#0b0b0b", ms=7, zorder=5)
        ax.annotate("BLUE", BLUE_POS, fontsize=7, xytext=(5, 3), textcoords="offset points")
    ax.plot([], [], "o", color="w", mec="k", label="first drifting fix")
    ax.plot([], [], "s", color="w", mec="k", label="last fix in domain B")
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect(1 / np.cos(np.radians(35.95)))
    ax.legend(fontsize=7, loc="lower left", framealpha=0.85)
    ax.tick_params(labelsize=7)
    cb = fig.colorbar(tc, ax=ax, shrink=0.6, pad=0.02)
    cb.set_label("bed level of mesh v03 (m)", fontsize=7)
    cb.ax.tick_params(labelsize=6)
    ax.set_title(f"(a) drifting tracks, {spec['title']}, marks every {MARK_HOURS} h "
                 f"from {t0:%d %b %H:%M} UTC", fontsize=8.5, loc="left")

    bx = fig.add_subplot(gs[0, 1])
    for b, g in tracks.items():
        bx.plot(g.time.iloc[1:], g.speed.iloc[1:], color=COLOURS[b], lw=1)
    w = blue.loc[t0:t1, "wind_speed"]
    bw = bx.twinx()
    bw.plot(w.index, w.values, color="#52514e", lw=0.8, ls=":")
    bw.set_ylabel("wind at BLUE (m/s), dotted", fontsize=7)
    bw.tick_params(labelsize=7)
    bx.set_ylabel("drift speed (m/s)", fontsize=7)
    bx.set_title("(b) speed from fix to fix", fontsize=8.5, loc="left")

    cx = fig.add_subplot(gs[1, 1], sharex=bx)
    for b, g in tracks.items():
        cx.plot(g.time, g.sst, color=COLOURS[b], lw=1)
    cx.set_ylabel("temperature of the sensor (°C)", fontsize=7)
    cx.set_title("(c) temperature", fontsize=8.5, loc="left")
    for a in (bx, cx):
        a.grid(color="#e8e7e3", lw=0.6)
        a.tick_params(labelsize=7)
        a.xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 12]))
        a.xaxis.set_major_formatter(mdates.DateFormatter("%d %b\n%H:%M"))
    path = ROOT / "figures" / f"drifters_2026_{key}.png"
    fig.savefig(path, dpi=170, facecolor="#fcfcfb", bbox_inches="tight")
    plt.close(fig)
    for b, g in tracks.items():
        hrs = (g.time.iloc[-1] - g.time.iloc[0]).total_seconds() / 3600
        print(f"{key} unit {b}: {g.time.iloc[0]:%d %b %H:%M} to {g.time.iloc[-1]:%d %b %H:%M}, "
              f"{hrs:.1f} h in domain B")
    print(f"wrote {path}")


def main() -> int:
    d = pd.read_csv(RECORD, parse_dates=["time"])
    d = d[d.status == "drifting"]
    tri, z = mesh_bed()
    coast = gpd.read_file(COAST).union_all()
    blue = pd.read_csv(BLUE, index_col=0, parse_dates=True)
    for key, spec in DEPLOYMENTS.items():
        figure(key, spec, d, tri, z, coast, blue)
    return 0


if __name__ == "__main__":
    sys.exit(main())

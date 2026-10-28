"""Figures of the first hindcast week on mesh v03 against CMEMS, ERA5 and BLUE.

Four figures are written to figures/:

- hindcast_week_map.png: mesh and bed depth of domain B, the open boundary,
  the stations and the area of the spurious surface currents, with the
  harbours and the BLUE buoy in a second panel;
- hindcast_week_level_forcing.png: water level at the BLUE station against the
  CMEMS sea surface height, less the offset removed at the boundary, and ERA5
  wind speed and pressure against the buoy;
- hindcast_week_blue.png: eastward and northward current and sea temperature at
  the buoy against the top layer of the model, the layer nearest 20 m and the
  daily CMEMS fields;
- hindcast_week_coastal_cooling.png: temperature of the top layer at stations
  from the open plateau to the mouth of the Grand Harbour.

Usage:
    python figure_hindcast_first_week.py [model/hindcast/v03_3d20_0722_0801] [--map-only]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import analyse_hindcast_v02 as ah  # noqa: E402

ROOT = ah.ROOT
CASE = ROOT / "model" / "hindcast" / "v03_3d20_0722_0801"
VALIDATION_START = pd.Timestamp("2025-07-25")
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e8e7e3"
C_TOP, C_DEEP, C_CMEMS = "#2a78d6", "#1baf7a", "#eb6834"
SURFACE = "#fcfcfb"


def style(ax, ylabel):
    ax.set_ylabel(ylabel)
    ax.grid(color=GRID, lw=0.6)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    import matplotlib.dates as mdates
    # spin-up shaded, the validation window clear
    lo, hi = ax.get_xlim()
    ax.axvspan(lo, mdates.date2num(VALIDATION_START), color="#efeeea", lw=0, zorder=0)
    ax.set_xlim(lo, hi)


def layer_series(st, name, depth):
    """A variable at the sigma layer nearest a depth below the surface."""
    wl = st["waterlevel"].values
    bed = float(st["bedlevel"])
    kmx = st.sizes["laydim"]
    frac = (np.arange(kmx) + 0.5) / kmx
    zc = bed + (wl[:, None] - bed) * frac[None, :]
    k = np.nanargmin(np.abs(zc - (wl[:, None] - depth)), axis=1)
    return pd.Series(st[name].values[np.arange(len(k)), k], index=st["time"].values)


def plot_map(case, meta, plt):
    """Mesh, bed level and the points of reference of the document."""
    import math

    import geopandas as gpd
    import xugrid as xu
    from matplotlib.collections import LineCollection, PolyCollection
    from matplotlib.patches import Rectangle

    uds = xu.open_dataset(next(case.glob("*_net.nc")))
    g = uds.grid
    zn = uds["mesh2d_node_z"].values
    fn = g.face_node_connectivity
    polys = [np.c_[g.node_x[r[r >= 0]], g.node_y[r[r >= 0]]] for r in fn]
    zf = np.array([zn[r[r >= 0]].mean() for r in fn])
    segs = np.c_[g.node_x, g.node_y][g.edge_node_connectivity]
    coast = gpd.read_file(ROOT / "data" / "processed" / "malta_coastline_wgs84_open.gpkg")
    bnd = np.loadtxt(next(case.glob("*_bnd.pli")), skiprows=2)
    st = meta["stations"]
    offshore = {"blue_buoy": "BLUE buoy", "plateau_north": "plateau, north edge",
                "plateau_east": "plateau, east", "offshore_4km": "offshore, 4 km"}
    harbour = {"blue_buoy": "BLUE buoy", "offshore_4km": "offshore, 4 km",
               "gh_mouth": "Grand Harbour mouth", "mx_mouth": "Marsamxett mouth",
               "senglea": "Senglea", "french_creek": "French Creek",
               "dockyard_creek": "Dockyard Creek", "marsa_head": "Marsa",
               "sliema_creek": "Sliema Creek", "msida_head": "Msida Creek",
               "pieta_head": "Pietà Creek"}
    slope_box = (14.25, 35.76, 14.34, 35.83)        # spurious currents of Section 7
    harbour_box = (14.480, 35.872, 14.560, 35.936)

    fig, axes = plt.subplots(1, 2, figsize=(13, 6.2), gridspec_kw=dict(width_ratios=[1.45, 1]))
    for ax, box, lw in ((axes[0], None, 0.12), (axes[1], harbour_box, 0.15)):
        pc = ax.add_collection(PolyCollection(polys, array=-zf, cmap="Blues", clim=(0, 1200),
                                              linewidths=0))
        ax.add_collection(LineCollection(segs, colors="#52514e", linewidths=lw, alpha=0.6))
        coast.plot(ax=ax, color="#e7e6e1", edgecolor="#8a8984", linewidth=0.5)
        ax.set_aspect(1 / math.cos(math.radians(36.0)))
        for side in ("top", "right"):
            ax.spines[side].set_visible(False)
    ax = axes[0]
    ax.plot(bnd[:, 0], bnd[:, 1], color=C_CMEMS, lw=2.0, label="open boundary, Riemann")
    ax.add_patch(Rectangle(slope_box[:2], slope_box[2] - slope_box[0], slope_box[3] - slope_box[1],
                           fill=False, ec="#c0392b", lw=1.4, ls="--"))
    ax.annotate("spurious surface\ncurrents, Section 7", (slope_box[2], slope_box[1]),
                xytext=(4, 0), textcoords="offset points", ha="left", va="bottom",
                fontsize=8, color="#c0392b")
    ax.add_patch(Rectangle(harbour_box[:2], harbour_box[2] - harbour_box[0],
                           harbour_box[3] - harbour_box[1], fill=False, ec=INK, lw=1.0))
    for name, label in offshore.items():
        if name == "offshore_4km":
            continue
        x, y = st[name]
        ax.plot(x, y, "o", ms=6, mfc="#f2c14e" if name == "blue_buoy" else "white", mec=INK, mew=1.0)
        ax.annotate(label, (x, y), xytext=(6, 4), textcoords="offset points", fontsize=8.5,
                    color=INK)
    ax.set_xlim(14.00, 15.06)
    ax.set_ylim(35.66, 36.34)
    ax.set_title("Domain B, mesh v03 and bed depth", fontsize=10, loc="left")
    ax.legend(frameon=False, fontsize=8.5, loc="lower right")
    ax = axes[1]
    # label offsets chosen by hand to keep the names clear of one another
    offsets = {"blue_buoy": (6, 6), "offshore_4km": (6, -10), "gh_mouth": (6, -2),
               "mx_mouth": (6, 8), "senglea": (-6, 0), "french_creek": (6, -8),
               "dockyard_creek": (6, 2), "marsa_head": (-6, -8), "sliema_creek": (-6, -7),
               "msida_head": (-6, 0), "pieta_head": (-6, -6)}
    for name, label in harbour.items():
        x, y = st[name]
        dx, dy = offsets[name]
        ax.plot(x, y, "o", ms=5.5, mfc="#f2c14e" if name == "blue_buoy" else "white",
                mec=INK, mew=1.0)
        ax.annotate(label, (x, y), xytext=(dx, dy), textcoords="offset points", fontsize=8,
                    ha="left" if dx > 0 else "right", va="center", color=INK)
    ax.set_xlim(harbour_box[0], harbour_box[2])
    ax.set_ylim(harbour_box[1], harbour_box[3])
    ax.set_title("Valletta harbours and the BLUE buoy", fontsize=10, loc="left")
    fig.colorbar(pc, ax=axes, label="bed depth, m", shrink=0.75)
    fig.savefig(ROOT / "figures" / "hindcast_week_map.png", dpi=150, facecolor=SURFACE,
                bbox_inches="tight")
    plt.close(fig)


def main(argv=None) -> int:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    argv = list(argv or [])
    map_only = "--map-only" in argv
    argv = [a for a in argv if a != "--map-only"]
    case = Path(argv[0]) if argv else CASE
    case = case if case.is_absolute() else ROOT / case
    meta = json.loads((case / "case.json").read_text())
    plot_map(case, meta, plt)
    if map_only:
        print("figure written to", ROOT / "figures" / "hindcast_week_map.png")
        return 0
    his = ah.open_his(case)
    t0, t1 = pd.Timestamp(meta["start"]), pd.Timestamp(meta["stop"])
    blue = pd.read_csv(ah.BLUE_CSV, parse_dates=["timestamp"], index_col="timestamp")[t0:t1]
    st = his.sel(station="blue_buoy")
    plt.rcParams.update({"font.size": 9.5, "axes.edgecolor": "#8a8984", "axes.labelcolor": INK,
                         "xtick.color": MUTED, "ytick.color": MUTED})
    fmt = mdates.DateFormatter("%d %b")

    # Level and forcing
    zos = xr.open_dataset(next(ah.CMEMS.glob("cmems_zos_*.nc"))).zos
    lon, lat = meta["stations"]["blue_buoy"]
    c = (ah.nearest_wet(zos, lon, lat).to_series() - meta["zos_offset"])[t0:t1]
    wl = st["waterlevel"].to_series()[t0:t1]
    u10, v10, msl = (ah.era5_at(k, *ah.BLUE)[t0:t1] for k in ("u10", "v10", "msl"))
    fig, axes = plt.subplots(3, 1, figsize=(9, 7.6), sharex=True)
    ax = axes[0]
    ax.plot(c.index, c * 100, color=C_CMEMS, lw=1.6, label="CMEMS, less the boundary offset")
    ax.plot(wl.index, wl * 100, color=C_TOP, lw=1.0, label="model")
    style(ax, "water level, cm")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=2)
    ax.set_title("Water level at the BLUE station", fontsize=10, loc="left")
    ax = axes[1]
    ax.plot(blue.index, blue.wind_speed, color=INK, lw=0.8, label="BLUE, 10 min")
    ax.plot(u10.index, np.hypot(u10, v10), color=C_CMEMS, lw=1.6, label="ERA5, hourly")
    style(ax, "wind speed, m/s")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=2)
    ax.set_title("Wind at 10 m", fontsize=10, loc="left")
    ax = axes[2]
    ax.plot(blue.index, blue.air_pressure, color=INK, lw=0.8, label="BLUE, 10 min")
    ax.plot(msl.index, msl / 100, color=C_CMEMS, lw=1.6, label="ERA5, hourly")
    style(ax, "pressure, hPa")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=2)
    ax.set_title("Air pressure at sea level", fontsize=10, loc="left")
    ax.xaxis.set_major_formatter(fmt)
    fig.tight_layout()
    fig.savefig(ROOT / "figures" / "hindcast_week_level_forcing.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)

    # Buoy comparison
    uo = xr.open_dataset(next(ah.CMEMS.glob("cmems_uo_*.nc"))).uo
    vo = xr.open_dataset(next(ah.CMEMS.glob("cmems_vo_*.nc"))).vo
    th = xr.open_dataset(next(ah.CMEMS.glob("cmems_thetao_*.nc"))).thetao
    cm = {k: ah.nearest_wet(da, *ah.BLUE).sel(depth=1, method="nearest").to_series()[t0:t1]
          for k, da in (("u", uo), ("v", vo), ("t", th))}
    model = {k: {d: layer_series(st, n, d) for d in (1.0, 20.0)}
             for k, n in (("u", "x_velocity"), ("v", "y_velocity"), ("t", "temperature"))}
    obs = {"u": blue.current_u / 100, "v": blue.current_v / 100, "t": blue.sea_temperature}
    fig, axes = plt.subplots(3, 1, figsize=(9, 8.2), sharex=True)
    for ax, key, label, title in ((axes[0], "u", "m/s", "Eastward current"),
                                  (axes[1], "v", "m/s", "Northward current"),
                                  (axes[2], "t", "°C", "Sea temperature")):
        o = obs[key].resample("1h").mean()
        ax.plot(o.index, o, color=INK, lw=1.0, label="BLUE, hourly mean")
        ax.plot(model[key][1.0].resample("1h").mean(), color=C_TOP, lw=1.3,
                label="model, top layer")
        ax.plot(model[key][20.0].resample("1h").mean(), color=C_DEEP, lw=1.3,
                label="model, layer nearest 20 m")
        # daily means are drawn as steps over the day they represent
        cmk = cm[key]
        ax.step(cmk.index, cmk.values, where="post", color=C_CMEMS, lw=1.8,
                label="CMEMS, 1 m, daily mean")
        style(ax, label)
        ax.set_title(title, fontsize=10, loc="left")
    axes[0].legend(frameon=False, fontsize=8.5, loc="upper left", ncol=2)
    axes[2].xaxis.set_major_formatter(fmt)
    fig.tight_layout()
    fig.savefig(ROOT / "figures" / "hindcast_week_blue.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)

    # Coastal cooling
    fig, ax = plt.subplots(figsize=(9, 3.6))
    for name, color, label in (("plateau_north", C_CMEMS, "plateau, north edge of domain B, 144 m"),
                               ("blue_buoy", C_TOP, "BLUE station, 104 m"),
                               ("gh_mouth", C_DEEP, "mouth of the Grand Harbour, 21 m")):
        s = his.sel(station=name)["temperature"].to_pandas().iloc[:, -1].resample("1h").mean()
        ax.plot(s.index, s.values, color=color, lw=1.4, label=label)
    o = obs["t"].resample("1h").mean()
    ax.plot(o.index, o, color=INK, lw=1.0, label="BLUE buoy")
    style(ax, "top layer temperature, °C")
    ax.legend(frameon=False, fontsize=8.5, loc="lower left", ncol=2)
    ax.xaxis.set_major_formatter(fmt)
    fig.tight_layout()
    fig.savefig(ROOT / "figures" / "hindcast_week_coastal_cooling.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)
    print("figures written to", ROOT / "figures")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

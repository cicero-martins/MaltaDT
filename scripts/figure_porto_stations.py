"""Figures of the PORTO station records against ERA5 and the BLUE buoy.

Draws, for docs/porto_stations_dataset.md, the position of the stations with
the ERA5 grid (porto_stations_map.png), the hourly wind speed of the harbour
stations, the buoy and ERA5 over the two July windows (porto_wind_series.png),
the ratio of the wind at each harbour station to that at the buoy by the
direction of the wind at the buoy (porto_wind_by_direction.png), and the air
pressure and the sea level at Portomaso over the event of 13 June 2024
(porto_event_2024-06-13.png). The station records are those written by
download_porto_stations.py.

Usage:
    python figure_porto_stations.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
PORTO = ROOT / "data" / "raw" / "porto"
BLUE_CSV = ROOT / "data" / "processed" / "blue_buoy_10min.csv"
COAST = ROOT / "data" / "processed" / "malta_coastline_wgs84.gpkg"
FIG = ROOT / "figures"

# position and altitude as stated by the portal (getStationFullCategoryList)
STATIONS = {
    "MetElmo": ("Elmo", 14.519, 35.903, 36),
    "MetKord": ("Kordin", 14.510, 35.885, 62),
    "MetMsida": ("Msida", 14.484, 35.903, 64),
    "MetDelim": ("Delimara", 14.559, 35.822, 36),
    "MetMXlokk": ("Marsaxlokk", 14.550, 35.818, 5),
    "MetCirk": ("Ċirkewwa", 14.330, 35.991, 0),
    "MetMgarG": ("Mġarr", 14.298, 36.024, 5),
    "MetQamm": ("Qammieħ", 14.325, 35.972, 128),
}
SEA_LEVEL = {"SLevPMaso": ("Portomaso", 14.493, 35.922)}
BLUE = (14.5388, 35.9294)
WINDOWS = {"Jul 2025": ("2025-07", "2025-07-25", "2025-08-01"),
           "May 2026": ("2026-05", "2026-05-17", "2026-05-22"),
           "Jul 2026": ("2026-07", "2026-07-03", "2026-07-09")}
# categorical slots 1 to 4 of the reference palette, validated for colour vision deficiency
COLOURS = {"BLUE": "#2a78d6", "Kordin": "#eb6834", "Msida": "#1baf7a", "Elmo": "#eda100"}
ERA5_COLOUR = "#3a3a38"
INK, MUTED = "#2b2b29", "#8c8a82"


def station(ref: str, t0: str, t1: str) -> pd.DataFrame:
    files = sorted((PORTO / ref).glob(f"{ref}_*.csv"))
    d = pd.concat([pd.read_csv(f, parse_dates=["time"]) for f in files]).set_index("time").sort_index()
    return d.loc[t0:t1]


def wind_hourly(ref: str, t0: str, t1: str) -> pd.DataFrame:
    d = station(ref, t0, t1)
    d = d[(d.wind_speed >= 0) & (d.wind_speed < 60)]
    th = np.radians(d.wind_dir)
    return pd.DataFrame({"u": -d.wind_speed * np.sin(th), "v": -d.wind_speed * np.cos(th),
                         "s": d.wind_speed}).resample("1h").mean()


def blue_hourly(t0: str, t1: str) -> pd.DataFrame:
    b = pd.read_csv(BLUE_CSV, parse_dates=["timestamp"]).set_index("timestamp")
    b = b.loc[t0:t1, ["wind_speed", "wind_direction"]].dropna()
    th = np.radians(b.wind_direction)
    return pd.DataFrame({"u": -b.wind_speed * np.sin(th), "v": -b.wind_speed * np.cos(th),
                         "s": b.wind_speed}).resample("1h").mean()


def era5_hourly(month: str, lon: float, lat: float, t0: str, t1: str) -> pd.DataFrame:
    def series(var):
        ds = xr.open_dataset(ROOT / "data" / "raw" / f"era5_{month}" / f"era5_{var}_{month}.nc")
        da = ds[var].rename(valid_time="time").sortby("latitude")
        return da.interp(latitude=lat, longitude=lon).to_series()
    e = pd.DataFrame({"u": series("u10"), "v": series("v10")}).loc[t0:t1]
    e["s"] = np.hypot(e.u, e.v)
    return e


def style(ax):
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=INK, labelsize=8)
    ax.grid(color="#e4e2dc", lw=0.6)
    ax.set_axisbelow(True)


def figure_map(plt, gpd) -> Path:
    coast = gpd.read_file(COAST)
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(12, 5.6), gridspec_kw=dict(width_ratios=[1.25, 1]),
                                 layout="constrained")
    for a, (x0, x1, y0, y1) in ((ax, (14.15, 14.68, 35.72, 36.10)), (bx, (14.465, 14.56, 35.875, 35.935))):
        coast.plot(ax=a, color="#e8e4d8", edgecolor="#8c8678", linewidth=0.5)
        a.set(xlim=(x0, x1), ylim=(y0, y1), aspect=1 / np.cos(np.radians((y0 + y1) / 2)))
        a.tick_params(labelsize=8, colors=INK)
    # ERA5 grid of 0.25 degree: the points and the edges of the cells they represent
    for g in np.arange(14.0, 14.8, 0.25):
        ax.axvline(g + 0.125, color=MUTED, lw=0.6, ls=":")
    for g in np.arange(35.75, 36.2, 0.25):
        ax.axhline(g + 0.125, color=MUTED, lw=0.6, ls=":")
    gx, gy = np.meshgrid(np.arange(14.0, 14.8, 0.25), np.arange(35.75, 36.2, 0.25))
    ax.plot(gx.ravel(), gy.ravel(), "+", color=ERA5_COLOUR, ms=9, mew=1.2, label="ERA5 grid point")
    harbour = {"MetElmo", "MetKord", "MetMsida"}
    for a in (ax, bx):
        for ref, (name, lon, lat, alt) in STATIONS.items():
            c = COLOURS.get(name, INK)
            a.plot(lon, lat, "^", ms=8 if a is bx else 6, color=c, mec="white", mew=0.8, zorder=5)
            if a is bx and ref in harbour or a is ax and ref not in harbour:
                # Marsaxlokk sits 0.5 km from Delimara and is labelled below it
                off = (5, -11) if ref == "MetMXlokk" else (5, 4)
                a.annotate(f"{name}, {alt} m", (lon, lat), xytext=off, textcoords="offset points",
                           fontsize=8, color=INK)
        for ref, (name, lon, lat) in SEA_LEVEL.items():
            a.plot(lon, lat, "s", ms=7, color=INK, mec="white", mew=0.8, zorder=5)
            if a is bx:
                a.annotate(f"{name} (sea level)", (lon, lat), xytext=(5, 4), textcoords="offset points",
                           fontsize=8, color=INK)
        a.plot(*BLUE, "o", ms=8, color=COLOURS["BLUE"], mec="white", mew=0.8, zorder=5)
        a.annotate("BLUE buoy", BLUE, xytext=(5, 4), textcoords="offset points", fontsize=8, color=INK)
    x0, x1, y0, y1 = 14.465, 14.56, 35.875, 35.935
    ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], color=INK, lw=0.8)
    ax.annotate("(b)", (x1, y0), xytext=(4, 0), textcoords="offset points", fontsize=8, color=INK)
    ax.legend(fontsize=8, loc="lower left", frameon=False)
    ax.set_title("(a) PORTO meteorological stations, BLUE buoy and ERA5 grid", loc="left", fontsize=10)
    bx.set_title("(b) Grand Harbour and Marsamxett", loc="left", fontsize=10)
    path = FIG / "porto_stations_map.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def figure_series(plt) -> Path:
    fig, axs = plt.subplots(2, 1, figsize=(12, 6.4), layout="constrained")
    for ax, key in zip(axs, ("Jul 2025", "Jul 2026")):
        month, t0, t1 = WINDOWS[key]
        ax.plot(era5_hourly(month, *BLUE, t0, t1).s, color=ERA5_COLOUR, lw=1.4, ls="--", label="ERA5 at BLUE")
        ax.plot(blue_hourly(t0, t1).s, color=COLOURS["BLUE"], lw=2, label="BLUE buoy")
        for ref in ("MetKord", "MetElmo", "MetMsida"):
            name = STATIONS[ref][0]
            try:
                w = wind_hourly(ref, t0, t1)
            except ValueError:
                continue
            if w.s.notna().any():
                ax.plot(w.s, color=COLOURS[name], lw=2, label=f"{name}, {STATIONS[ref][3]} m")
        style(ax)
        ax.set(ylabel="Wind speed (m/s)", ylim=(0, None))
        ax.set_title(f"({'ab'[key == 'Jul 2026']}) {t0} to {t1}, hourly means", loc="left", fontsize=10)
        ax.legend(fontsize=8, ncol=5, loc="upper left", frameon=False)
    path = FIG / "porto_wind_series.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def ratios_by_direction() -> pd.DataFrame:
    """Ratio of the mean speed at each station to that at the buoy, by the direction at the buoy."""
    rows = []
    for key, (month, t0, t1) in WINDOWS.items():
        b = blue_hourly(t0, t1)
        b["dir"] = (np.degrees(np.arctan2(-b.u, -b.v)) + 360) % 360
        for ref in ("MetKord", "MetElmo", "MetMsida"):
            try:
                w = wind_hourly(ref, t0, t1)
            except ValueError:
                continue
            j = b.join(w.s.rename("st")).dropna()
            j = j[j.s > 3.0]
            for _, r in j.iterrows():
                rows.append(dict(station=STATIONS[ref][0], dir=r["dir"], blue=r.s, st=r.st))
    d = pd.DataFrame(rows)
    d["sector"] = ((d["dir"] + 22.5) // 45 % 8).astype(int)
    return d


def figure_direction(plt) -> Path:
    d = ratios_by_direction()
    labels = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    fig, ax = plt.subplots(figsize=(9, 4.4), layout="constrained")
    names = ["Kordin", "Elmo", "Msida"]
    width = 0.26
    for k, name in enumerate(names):
        g = d[d.station == name].groupby("sector")
        ratio = (g.st.sum() / g.blue.sum()).reindex(range(8))
        n = g.size().reindex(range(8)).fillna(0)
        ratio[n < 6] = np.nan
        x = np.arange(8) + (k - 1) * width
        ax.bar(x, ratio.values, width=width - 0.03, color=COLOURS[name], label=name)
        for xi, (ri, ni) in enumerate(zip(ratio.values, n.values)):
            if np.isfinite(ri):
                ax.annotate(f"{int(ni)}", (x[xi], ri), xytext=(0, 2), textcoords="offset points",
                            ha="center", fontsize=6.5, color=MUTED)
    ax.axhline(1.0, color=INK, lw=0.8)
    style(ax)
    ax.set_xticks(range(8), labels)
    ax.set(xlabel="Direction from which the wind blows at the BLUE buoy",
           ylabel="Station speed over BLUE speed", ylim=(0, 1.4))
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="upper left")
    ax.set_title("Ratio of mean speeds by sector, hours with more than 3 m/s at BLUE, three windows",
                 loc="left", fontsize=10)
    path = FIG / "porto_wind_by_direction.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path, d


def figure_event(plt) -> Path:
    t0, t1 = "2024-06-12 18:00", "2024-06-13 12:00"
    fig, (ax, bx) = plt.subplots(2, 1, figsize=(12, 5.6), sharex=True, layout="constrained")
    for ref in ("MetElmo", "MetKord"):
        name = STATIONS[ref][0]
        p = station(ref, t0, t1).atm_press
        ax.plot(p, color=COLOURS[name], lw=1.4, label=f"{name}, 1 min")
    style(ax)
    ax.set(ylabel="Air pressure (hPa)")
    ax.legend(fontsize=8, frameon=False, loc="upper right")
    ax.set_title("(a) Air pressure at the harbour stations", loc="left", fontsize=10)
    sl = station("SLevPMaso", "2024-06-12 12:00", "2024-06-13 18:00").avg_level
    hp = (sl - sl.rolling("3h", center=True).mean()).loc[t0:t1]
    bx.plot(hp, color=INK, lw=0.8)
    style(bx)
    bx.set(ylabel="Sea level minus 3 h mean (m)", xlabel="UTC")
    bx.set_title("(b) Sea level at Portomaso, 10 s, variation slower than 3 hours removed",
                 loc="left", fontsize=10)
    path = FIG / "porto_event_2024-06-13.png"
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main() -> int:
    import geopandas as gpd
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    print(f"wrote {figure_map(plt, gpd)}")
    print(f"wrote {figure_series(plt)}")
    path, d = figure_direction(plt)
    print(f"wrote {path}")
    g = d.groupby(["station", "sector"])
    print((g.st.sum() / g.blue.sum()).unstack().round(2).to_string())
    print(g.size().unstack().to_string())
    print(f"wrote {figure_event(plt)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

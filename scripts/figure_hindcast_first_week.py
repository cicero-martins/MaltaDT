"""Figures of the first hindcast week on mesh v03 against CMEMS, ERA5 and BLUE.

Three figures are written to figures/:

- hindcast_week_level_forcing.png: water level at the BLUE station against the
  CMEMS sea surface height, less the offset removed at the boundary, and ERA5
  wind speed and pressure against the buoy;
- hindcast_week_blue.png: eastward and northward current and sea temperature at
  the buoy against the top layer of the model, the layer nearest 20 m and the
  daily CMEMS fields;
- hindcast_week_coastal_cooling.png: temperature of the top layer at stations
  from the open plateau to the mouth of the Grand Harbour.

Usage:
    python figure_hindcast_first_week.py [model/hindcast/v03_3d20_0722_0801]
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
    k = np.abs(zc - (wl[:, None] - depth)).argmin(axis=1)
    return pd.Series(st[name].values[np.arange(len(k)), k], index=st["time"].values)


def main(argv=None) -> int:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates

    case = Path(argv[0]) if argv else CASE
    case = case if case.is_absolute() else ROOT / case
    meta = json.loads((case / "case.json").read_text())
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

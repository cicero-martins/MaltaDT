"""Classify the fixes of the three drifters of 2026 and write the record used for validation.

The files supplied by the group, data/raw/drifters/SST_DATA_<buoy>.csv, hold
every fix the units transmitted, at about 30 minutes, from switch-on to
recovery, with position and sea surface temperature. They include fixes on
land before deployment and after recovery, fixes taken aboard the vessel on
the way to the release point, fixes of units stranded on the Libyan coast,
and one unit held at a fixed point. Each fix is given a status:

- drifting, inside a deployment and passing every test below;
- moored, unit 12 from 21 July 2026, held within metres of one point;
- land, inside the coastline of the Maltese Islands;
- shore, within SHORE_DISTANCE of that coastline, where a unit is grounding or
  being handled and the model cells of 120 m do not resolve the flow;
- transport, at a speed from the previous fix above TRANSPORT_SPEED, aboard
  a vessel or a vehicle;
- stationary, held within STATIONARY_RANGE over STATIONARY_HOURS, a unit
  grounded on a coast outside the Maltese coastline;
- outside, before the first or after the last fix of a deployment.

A deployment is the bracket of DEPLOYMENTS within which the unit was at sea,
read from the record. Its drifting part runs from the first fix after the
last failure of the tests within the first hours of the bracket to the last
fix before the next failure, so that a unit that grounds or is recovered ends
its deployment there.

Usage:
    python prepare_drifters_2026.py [--figure]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import contains_xy, distance, points

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "drifters"
OUT = ROOT / "data" / "processed" / "drifters_2026.csv"
FIGURE = ROOT / "figures" / "drifters_2026_overview.png"
COAST = ROOT / "data" / "processed" / "malta_coastline_wgs84.gpkg"

BUOYS = (9, 11, 12)
# Brackets in UTC within which each unit was at sea, read from the record
DEPLOYMENTS = {
    "9_may": (9, "2026-05-20 00:00", "2026-05-22 00:00"),
    "11_may": (11, "2026-05-20 00:00", "2026-05-22 00:00"),
    "9_jul": (9, "2026-07-06 06:00", "2026-09-30 00:00"),
    "11_jul": (11, "2026-07-06 06:00", "2026-09-30 00:00"),
}
MOORED = (12, "2026-07-21 08:30")
TRANSPORT_SPEED = 1.0          # m/s, from the previous fix
SHORE_DISTANCE = 50.0          # m from the coastline of the Maltese Islands
STATIONARY_RANGE = 200.0       # m, extent of the positions over the window
STATIONARY_HOURS = 12
START_SEARCH_HOURS = 6         # failures within this time of the bracket start delay it
DOMAIN_B = (14.0287, 15.0125, 35.6850, 36.3120)   # extent of mesh v03
M_PER_DEG_LAT = 111_000.0


def haversine(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = (np.sin((p2 - p1) / 2) ** 2
         + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2)
    return 2 * 6371e3 * np.arcsin(np.sqrt(a))


def load(buoy: int) -> pd.DataFrame:
    d = pd.read_csv(RAW / f"SST_DATA_{buoy}.csv")
    d = pd.DataFrame({"buoy": buoy,
                      "time": pd.to_datetime(d.UtcTimestamp, utc=True).dt.tz_localize(None),
                      "lat": d.Latitude, "lon": d.Longitude, "sst": d.SST})
    d = d.sort_values("time").drop_duplicates("time").reset_index(drop=True)
    dt = d.time.diff().dt.total_seconds()
    d["speed"] = haversine(d.lat.shift(), d.lon.shift(), d.lat, d.lon) / dt
    return d


def stationary(d: pd.DataFrame) -> np.ndarray:
    """Fixes whose positions over the following STATIONARY_HOURS stay within STATIONARY_RANGE."""
    s = d.set_index("time")[["lat", "lon"]]
    win = f"{STATIONARY_HOURS}h"
    # forward window, by reversing time
    rev = s.iloc[::-1].copy()
    rev.index = rev.index.max() - rev.index
    rng_lat = (rev.lat.rolling(win).max() - rev.lat.rolling(win).min()).iloc[::-1].values
    rng_lon = (rev.lon.rolling(win).max() - rev.lon.rolling(win).min()).iloc[::-1].values
    span = np.hypot(rng_lat * M_PER_DEG_LAT, rng_lon * M_PER_DEG_LAT * np.cos(np.radians(s.lat.values)))
    full = (s.index.max() - s.index) >= pd.Timedelta(win)
    return (span < STATIONARY_RANGE) & full


def classify(d: pd.DataFrame, coast) -> pd.DataFrame:
    pts = points(d.lon.values, d.lat.values)
    d["land"] = contains_xy(coast, d.lon.values, d.lat.values)
    # degrees to metres at the latitude of Malta, adequate below 100 m
    d["shore_m"] = distance(coast.boundary, pts) * M_PER_DEG_LAT * np.cos(np.radians(35.9))
    d["shore_m"] = np.where(d.lon.between(14.0, 14.8) & d.lat.between(35.7, 36.15),
                            d.shore_m, np.inf)
    d["status"] = np.where(d.land, "land", "outside")
    d["deployment"] = ""
    fail = pd.Series("", index=d.index)
    fail[d.speed > TRANSPORT_SPEED] = "transport"
    fail[stationary(d)] = "stationary"
    fail[d.shore_m < SHORE_DISTANCE] = "shore"
    fail[d.land] = "land"
    for name, (buoy, a, b) in DEPLOYMENTS.items():
        if buoy != d.buoy.iloc[0]:
            continue
        idx = d.index[(d.time >= a) & (d.time < b)]
        early = idx[(d.time[idx] < pd.Timestamp(a) + pd.Timedelta(hours=START_SEARCH_HOURS))
                    & (fail[idx] != "")]
        first = early.max() + 1 if early.size else idx.min()
        later = idx[(idx >= first) & (fail[idx] != "")]
        last = later.min() - 1 if later.size else idx.max()
        sel = (d.index >= first) & (d.index <= last)
        d.loc[sel, "status"] = "drifting"
        d.loc[sel, "deployment"] = name
        rest = d.index.isin(idx) & ~sel & (fail != "")
        d.loc[rest, "status"] = fail[rest]
    if d.buoy.iloc[0] == MOORED[0]:
        sel = d.time >= MOORED[1]
        d.loc[sel, "status"] = "moored"
        d.loc[sel, "deployment"] = "12_moored"
    d["in_domain_b"] = (d.lon.between(DOMAIN_B[0], DOMAIN_B[1])
                        & d.lat.between(DOMAIN_B[2], DOMAIN_B[3]))
    return d


def report(d: pd.DataFrame) -> None:
    for name, g in d[d.deployment != ""].groupby("deployment", sort=False):
        b = g[g.in_domain_b]
        dt = g.time.diff().dt.total_seconds() / 60
        print(f"{name:10s} {g.time.iloc[0]:%Y-%m-%d %H:%M} to {g.time.iloc[-1]:%Y-%m-%d %H:%M}, "
              f"{len(g)} fixes, gaps above 45 min {int((dt > 45).sum())}, "
              f"speed median {g.speed.iloc[1:].median():.3f} max {g.speed.iloc[1:].max():.2f} m/s")
        if len(b) and g.status.iloc[0] == "drifting":
            hrs = (b.time.iloc[-1] - b.time.iloc[0]).total_seconds() / 3600
            print(f"{'':10s} in domain B {b.time.iloc[0]:%Y-%m-%d %H:%M} to "
                  f"{b.time.iloc[-1]:%Y-%m-%d %H:%M}, {hrs:.1f} h, {len(b)} fixes")
    print(d.groupby(["buoy", "status"]).size().unstack(fill_value=0))


def figure(d: pd.DataFrame, coast) -> None:
    import cartopy.io.shapereader as shpreader
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.dates as mdates
    import matplotlib.pyplot as plt

    colours = {9: "#2a78d6", 11: "#eb6834", 12: "#1baf7a"}
    status_colour = {"drifting": "#2a78d6", "moored": "#1baf7a", "land": "#8a6d3b",
                     "shore": "#d4a017", "transport": "#c0392b", "stationary": "#7d3c98",
                     "outside": "#b9b6ae"}
    land = gpd.read_file(shpreader.natural_earth(resolution="50m", category="physical",
                                                 name="land"))
    fig = plt.figure(figsize=(11, 8.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.25, 1], hspace=0.28, wspace=0.18)

    ax = fig.add_subplot(gs[0, 0])
    land.plot(ax=ax, color="#d9d6cf", edgecolor="#9a978f", lw=0.4)
    for buoy, g in d.groupby("buoy"):
        dr = g[g.status == "drifting"]
        for _, s in dr.groupby("deployment"):
            ax.plot(s.lon, s.lat, color=colours[buoy], lw=0.8)
        ax.plot([], [], color=colours[buoy], label=f"unit {buoy}")
    m = d[d.status == "moored"]
    ax.plot(m.lon.median(), m.lat.median(), "s", color=colours[12], ms=5)
    x0, x1, y0, y1 = DOMAIN_B
    ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0], color="#0b0b0b", lw=0.8)
    ax.set_xlim(12.5, 21.0)
    ax.set_ylim(30.2, 37.6)
    ax.set_aspect(1 / np.cos(np.radians(34)))
    ax.legend(fontsize=7, frameon=False, loc="upper right")
    ax.set_title("(a) drifting tracks, July to September, and domain B", fontsize=9, loc="left")
    ax.tick_params(labelsize=7)

    bx = fig.add_subplot(gs[0, 1])
    gpd.GeoSeries([coast]).plot(ax=bx, color="#d9d6cf", edgecolor="#9a978f", lw=0.4)
    for status, g in d[d.in_domain_b].groupby("status"):
        if status in ("drifting",):
            continue
        moored = status == "moored"
        bx.scatter(g.lon, g.lat, s=18 if moored else 4, color=status_colour[status],
                   label=status, zorder=5 if moored else 3, marker="s" if moored else "o")
    for (buoy, dep), s in d[(d.status == "drifting") & d.in_domain_b].groupby(["buoy", "deployment"]):
        ls = "-" if dep.endswith("jul") else "--"
        bx.plot(s.lon, s.lat, color=colours[buoy], lw=1.2, ls=ls, zorder=2)
        bx.plot(s.lon.iloc[0], s.lat.iloc[0], "o", color=colours[buoy], ms=4, zorder=4)
        # the two May units were released together, so one label serves both
        label = {"9_may": "9 and 11, 20 May", "11_may": None}.get(
            dep, f"{buoy}, {s.time.iloc[0]:%d %b %H:%M}")
        if label:
            bx.annotate(label, (s.lon.iloc[0], s.lat.iloc[0]), fontsize=6,
                        xytext=(4, 3), textcoords="offset points")
    bx.plot(14.5388, 35.9294, "^", color="#0b0b0b", ms=6, zorder=5)
    bx.annotate("BLUE", (14.5388, 35.9294), fontsize=7, xytext=(4, -8), textcoords="offset points")
    bx.set_xlim(DOMAIN_B[0], DOMAIN_B[1])
    bx.set_ylim(DOMAIN_B[2], DOMAIN_B[3])
    bx.set_aspect(1 / np.cos(np.radians(35.9)))
    bx.legend(fontsize=6, frameon=False, loc="lower left", markerscale=2)
    bx.set_title("(b) domain B, drifting in lines (May dashed), other fixes by status",
                 fontsize=9, loc="left")
    bx.tick_params(labelsize=7)

    cx = fig.add_subplot(gs[1, :])
    for k, buoy in enumerate(BUOYS):
        g = d[d.buoy == buoy]
        cx.scatter(g.time, g.sst, s=1.2, c=[status_colour[s] for s in g.status], lw=0)
    for status, c in status_colour.items():
        cx.scatter([], [], color=c, s=12, label=status)
    cx.set_ylabel("temperature of the unit (°C)", fontsize=8)
    cx.legend(fontsize=7, frameon=False, ncol=7, loc="upper left")
    cx.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    cx.tick_params(labelsize=7)
    cx.grid(color="#e8e7e3", lw=0.6)
    cx.set_title("(c) temperature of all three units by status of the fix", fontsize=9, loc="left")
    fig.savefig(FIGURE, dpi=170, facecolor="#fcfcfb", bbox_inches="tight")
    print(f"wrote {FIGURE}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--figure", action="store_true")
    args = ap.parse_args(argv)
    coast = gpd.read_file(COAST).union_all()
    d = pd.concat([classify(load(b), coast) for b in BUOYS], ignore_index=True)
    report(d)
    cols = ["buoy", "time", "lat", "lon", "sst", "speed", "status", "deployment", "in_domain_b"]
    d[cols].to_csv(OUT, index=False, float_format="%.6f")
    print(f"wrote {OUT}")
    if args.figure:
        figure(d, coast)
    return 0


if __name__ == "__main__":
    sys.exit(main())

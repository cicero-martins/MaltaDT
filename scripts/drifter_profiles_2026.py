"""Vertical profile of the current at the positions of the July 2026 drifters.

The profiles of the model at the hourly positions of units 9 and 11, extracted
from the partitioned map by `extract_profiles_map.py`, are set beside the
profiles of the hourly CMEMS analysis-forecast current over the column,
interpolated to the same positions and hours, and beside the velocity of the
drifters at the surface. Both sources are interpolated onto common depths and
averaged by day of run and over the deployment, for the run with the daily and
for the run with the hourly CMEMS current at the boundary.

Output: data/processed/drifter_profiles_2026.csv, figures/drifter_profiles_2026.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
CASES = {"model_daily": "v03_3d20s_0703_0709_uv_thd_2026", "model_hourly": "v03_3d20s_0703_0709_uvh_thd_2026"}
CMEMS = ROOT / "data" / "raw" / "cmems_2026-07" / "cmems-currents-1h_2026-07-02_2026-07-10.nc"
OUT = ROOT / "data" / "processed" / "drifter_profiles_2026.csv"
FIGURE = ROOT / "figures" / "drifter_profiles_2026.png"
DEPTHS = np.array([1, 2, 3, 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100.0])
START = pd.Timestamp("2026-07-03")
COLOURS = {"model_daily": "#2a78d6", "model_hourly": "#7b4fc4", "cmems": "#eb6834"}
LABELS = {"model_daily": "model, daily boundary current", "model_hourly": "model, hourly boundary current",
          "cmems": "CMEMS, hourly over the column"}


def model_profiles(case: str) -> dict:
    ds = xr.open_dataset(ROOT / "model" / "hindcast" / case / "output" / f"{case}_profiles.nc")
    sigma = ds.layer_sigma.values
    # depth of the layer centres below the surface, sigma running from -1 at the bed to 0
    z = -sigma[None, :] * ds.mesh2d_waterdepth.values[:, None]
    order = np.argsort(z[0])
    res = {}
    for name, var in (("u", "mesh2d_ucx"), ("v", "mesh2d_ucy"), ("tem", "mesh2d_tem1")):
        a = ds[var].values
        res[name] = np.array([np.interp(DEPTHS, z[i, order], a[i, order], right=np.nan) for i in range(len(z))])
    res["top_depth"] = z.min(1)
    res["depth"] = ds.mesh2d_waterdepth.values
    res["wind"] = ds.mesh2d_windx.values + 1j * ds.mesh2d_windy.values
    res["points"] = ds[["time", "lon", "lat", "deployment", "u", "v"]].to_dataframe().reset_index()
    return res


def cmems_profiles(points: pd.DataFrame) -> dict:
    ds = xr.open_dataset(CMEMS).sel(depth=slice(0, 130))
    sel = dict(time=xr.DataArray(points.time.values, dims="point"),
               longitude=xr.DataArray(points.lon.values, dims="point"),
               latitude=xr.DataArray(points.lat.values, dims="point"))
    res = {}
    for name, var in (("u", "uo"), ("v", "vo")):
        a = ds[var].interp(**sel).transpose("point", "depth").values
        near = ds[var].sel(time=sel["time"], longitude=sel["longitude"], latitude=sel["latitude"],
                           method="nearest").transpose("point", "depth").values
        a = np.where(np.isfinite(a), a, near)
        res[name] = np.array([np.interp(DEPTHS, ds.depth.values, row) for row in a])
    return res


def main() -> int:
    prof = {k: model_profiles(c) for k, c in CASES.items()}
    points = prof["model_daily"]["points"]
    prof["cmems"] = cmems_profiles(points)
    day = ((points.time - START) / pd.Timedelta(days=1)).astype(int).values + 1
    groups = {f"day {d}": day == d for d in np.unique(day)}
    groups["all"] = np.ones(len(points), bool)

    m = prof["model_daily"]
    print(f"{len(points)} drifter hours, water depth {np.nanmin(m['depth']):.0f} to {np.nanmax(m['depth']):.0f} m, "
          f"centre of the top layer at {np.nanmedian(m['top_depth']):.2f} m")
    rows = []
    for g, sel in groups.items():
        w = m["wind"][sel].mean()
        print(f"{g}: {sel.sum()} hours, drifter u {points.u[sel].mean():.2f} v {points.v[sel].mean():.2f} m/s, "
              f"wind {abs(w):.1f} m/s towards {np.degrees(np.arctan2(w.real, w.imag)) % 360:.0f} deg")
        for s in prof:
            for k, z in enumerate(DEPTHS):
                rows.append(dict(group=g, source=s, depth=z, n=int(sel.sum()),
                                 u=np.nanmean(prof[s]["u"][sel, k]), v=np.nanmean(prof[s]["v"][sel, k])))
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False, float_format="%.4f")
    table = out[out.group == "all"].pivot(index="depth", columns="source", values=["u", "v"])
    print(table.to_string(float_format=lambda x: f"{x:.2f}"))
    for g in groups:
        t = out[out.group == g].pivot(index="depth", columns="source", values="v")
        print(g, "v:", t.loc[[1, 5, 10, 20, 30, 50]].round(2).to_dict("list"))
    print("model temperature, all hours:",
          dict(zip(DEPTHS, np.round(np.nanmean(m["tem"], 0), 2))))

    fig, axes = plt.subplots(2, len(groups), figsize=(3.1 * len(groups), 8), sharey=True)
    for j, (g, sel) in enumerate(groups.items()):
        for i, comp in enumerate("uv"):
            ax = axes[i, j]
            d = out[out.group == g]
            for s in prof:
                p = d[d.source == s]
                ax.plot(p[comp], p.depth, "-", color=COLOURS[s], lw=1.6, label=LABELS[s])
            ax.plot(points[comp][sel].mean(), 0, "*", color="k", ms=13, clip_on=False, zorder=5,
                    label="drifters, units 9 and 11")
            ax.axvline(0, color="0.7", lw=0.5)
            ax.set_xlim(-0.32, 0.2)
            ax.set_ylim(100, 0)
            ax.grid(alpha=0.3)
            title = "deployment" if g == "all" else f"{g}, {(START + pd.Timedelta(days=int(g[4:]) - 1)):%d %B}"
            ax.set_title(f"({'abcdefgh'[i * len(groups) + j]}) {title}, {sel.sum()} h", loc="left", fontsize=9)
            if i == 1:
                ax.set_xlabel("northward current (m/s)")
            else:
                ax.set_xlabel("eastward current (m/s)")
            if j == 0:
                ax.set_ylabel("depth (m)")
    axes[0, 0].legend(fontsize=7, loc="lower left")
    fig.tight_layout()
    fig.savefig(FIGURE, dpi=150)
    print(FIGURE)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Zonal sections of the northward current and of the density in July 2026.

The southward current that CMEMS holds in the upper 50 m east of Malta is
followed from the northern to the southern boundary of domain B along seven
zonal sections. The profiles of the model along each section, at every hour,
come from the partitioned map through `extract_profiles_map.py`, and the
hourly CMEMS current over the column and the daily CMEMS temperature and
salinity are interpolated to the same points. For each section and day of run
the northward current is averaged east of Malta over two depth ranges, and the
shear that the zonal density gradient of each source sustains by the thermal
wind relation is set beside the shear of the current itself.

The density follows a linear equation of state, adequate for the gradients
along a section, with the same coefficients for both sources.

Output: data/processed/current_sections_2026.csv, figures/current_sections_2026.png,
figures/current_sections_2026_series.png
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
CASE = "v03_3d20s_0703_0709_uv_thd_2026"
RAW = ROOT / "data" / "raw" / "cmems_2026-07"
OUT = ROOT / "data" / "processed" / "current_sections_2026.csv"
FIGURE = ROOT / "figures" / "current_sections_2026.png"
FIGURE_SERIES = ROOT / "figures" / "current_sections_2026_series.png"
DEPTHS = np.array([1, 2, 3, 5, 7.5, 10, 15, 20, 25, 30, 40, 50, 60, 80, 100.0])
EAST = (14.60, 15.00)                 # east of Malta, the longitudes of the July tracks
UPPER, LOWER = (0, 10), (10, 40)      # m, the wind-driven layer and the thermocline
REFERENCE = 60.0                      # m, level of reference of the thermal wind
START = pd.Timestamp("2026-07-03")
MAX_OFFSET = 0.02                     # degrees, a point farther from its face lies on land
G, RHO0 = 9.81, 1027.0
SHOWN = ("36.29N", "36.10N", "35.90N", "35.71N")


def density(tem, sal):
    return RHO0 * (1 - 2.5e-4 * (tem - 18.0) + 7.6e-4 * (sal - 38.0))


def to_depths(z, a):
    """Profiles a over the depths z of the layer centres, onto DEPTHS."""
    order = np.argsort(z, -1)
    z, a = np.take_along_axis(z, order, -1), np.take_along_axis(a, order, -1)
    out = np.full(a.shape[:-1] + (DEPTHS.size,), np.nan, "float32")
    for i in np.ndindex(a.shape[:-1]):
        if np.isfinite(a[i]).all():
            out[i] = np.interp(DEPTHS, z[i], a[i], right=np.nan)
    return out


def load_model() -> dict:
    ds = xr.open_dataset(ROOT / "model" / "hindcast" / CASE / "output" / f"{CASE}_sections.nc")
    wet = np.hypot(ds.lon.values - ds.face_x.values, ds.lat.values - ds.face_y.values) < MAX_OFFSET
    z = -ds.layer_sigma.values[None, None, :] * ds.mesh2d_waterdepth.values[:, :, None]
    res = dict(time=pd.to_datetime(ds.time.values), lon=ds.lon.values, lat=ds.lat.values,
               section=ds.section.values.astype(str), wet=wet)
    for name, var in (("v", "mesh2d_ucy"), ("tem", "mesh2d_tem1"), ("sal", "mesh2d_sa1")):
        a = to_depths(z, ds[var].values)
        a[:, ~wet] = np.nan
        res[name] = a
    return res


def load_cmems(m: dict) -> dict:
    lon = xr.DataArray(m["lon"], dims="point")
    lat = xr.DataArray(m["lat"], dims="point")
    depth = xr.DataArray(DEPTHS, dims="z")
    cur = xr.open_dataset(RAW / "cmems-currents-1h_2026-07-02_2026-07-10.nc").sel(depth=slice(0, 130))
    v = cur.vo.sel(time=m["time"]).interp(longitude=lon, latitude=lat).interp(depth=depth, kwargs={"fill_value": "extrapolate"})
    res = dict(v=v.transpose("time", "point", "z").values)
    for name, var in (("tem", "thetao"), ("sal", "so")):
        f = xr.open_dataset(next(RAW.glob(f"cmems_{var}_*.nc")))[var].sel(depth=slice(0, 130))
        a = f.interp(longitude=lon, latitude=lat).interp(depth=depth, kwargs={"fill_value": "extrapolate"}).interp(time=m["time"])
        res[name] = a.transpose("time", "point", "z").values
    return res


def layer_mean(a, lo, hi):
    k = (DEPTHS >= lo) & (DEPTHS <= hi)
    return np.trapezoid(a[..., k], DEPTHS[k], axis=-1) / (DEPTHS[k][-1] - DEPTHS[k][0])


def thermal_wind(rho, lon, lat):
    """Northward geostrophic current relative to REFERENCE from the zonal density gradient.

    rho over (time, point, z) along one section, the points ordered eastward.
    """
    f = 2 * 7.2921e-5 * np.sin(np.radians(lat))
    x = lon * 111320 * np.cos(np.radians(lat))
    drdx = np.gradient(rho, x, axis=1)
    shear = -G / (f * RHO0) * drdx              # dv/dz, z upward
    kref = np.argmin(np.abs(DEPTHS - REFERENCE))
    v = np.zeros_like(rho)
    for k in range(kref - 1, -1, -1):
        v[..., k] = v[..., k + 1] + 0.5 * (shear[..., k] + shear[..., k + 1]) * (DEPTHS[k + 1] - DEPTHS[k])
    v[..., kref + 1:] = np.nan
    return v


def main() -> int:
    m = load_model()
    c = load_cmems(m)
    src = {"model": m, "cmems": c}
    day = ((m["time"] - START) / pd.Timedelta(days=1)).astype(int) + 1
    sections = sorted(set(m["section"]), reverse=True)
    rows, series = [], {}
    for sec in sections:
        p = np.where(m["section"] == sec)[0]
        p = p[np.argsort(m["lon"][p])]
        lon, lat = m["lon"][p], float(m["lat"][p][0])
        east = (lon >= EAST[0]) & (lon <= EAST[1])
        for s, d in src.items():
            v = d["v"][:, p]
            vg = thermal_wind(density(d["tem"][:, p], d["sal"][:, p]), lon, lat)
            valid = east & np.isfinite(m["v"][:, p][..., :12]).all((0, 2)) & np.isfinite(c["v"][:, p][..., :12]).all((0, 2))
            up = np.nanmean(layer_mean(v, *UPPER)[:, valid], 1)
            low = np.nanmean(layer_mean(v, *LOWER)[:, valid], 1)
            ref = np.nanmean(v[:, valid][..., DEPTHS == REFERENCE][..., 0], 1)
            geo = np.nanmean(layer_mean(vg, *LOWER)[:, valid], 1)
            series[sec, s] = dict(upper=up, lower=low, geo=geo, rel=low - ref)
            for dd in np.unique(day):
                t = day == dd
                if t.sum() < 12:
                    continue
                rows.append(dict(section=sec, source=s, day=int(dd), n_points=int(valid.sum()),
                                 v_upper=up[t].mean(), v_lower=low[t].mean(),
                                 v_lower_rel=(low - ref)[t].mean(), v_lower_geo=geo[t].mean()))
    out = pd.DataFrame(rows)
    out.to_csv(OUT, index=False, float_format="%.4f")
    for col in ("v_lower", "v_upper", "v_lower_rel", "v_lower_geo"):
        print(col)
        print(out.pivot(index=["section", "source"], columns="day", values=col).sort_index(ascending=False)
              .to_string(float_format=lambda x: f"{x:.2f}"))

    late = np.isin(day, (4, 5, 6))
    fig, axes = plt.subplots(2, len(SHOWN), figsize=(3.6 * len(SHOWN), 6.2), sharey=True, sharex=True)
    for j, sec in enumerate(SHOWN):
        p = np.where(m["section"] == sec)[0]
        p = p[np.argsort(m["lon"][p])]
        for i, (s, label) in enumerate((("cmems", "CMEMS"), ("model", "model"))):
            ax = axes[i, j]
            a = np.nanmean(src[s]["v"][late][:, p], 0).T
            a = np.where(m["wet"][p][None, :], a, np.nan)
            pc = ax.pcolormesh(m["lon"][p], DEPTHS, a, cmap="RdBu_r", vmin=-0.25, vmax=0.25, shading="nearest")
            ax.contour(m["lon"][p], DEPTHS, a, levels=[-0.2, -0.15, -0.1, -0.05], colors="k", linewidths=0.5)
            ax.set_ylim(100, 0)
            ax.set_facecolor("0.8")
            ax.set_title(f"({'abcdefgh'[i * len(SHOWN) + j]}) {label}, {sec[:-1]}° N", loc="left", fontsize=9)
            if j == 0:
                ax.set_ylabel("depth (m)")
            if i == 1:
                ax.set_xlabel("longitude (° E)")
    fig.colorbar(pc, ax=axes, label="northward current, 6 to 8 July (m/s)", shrink=0.8, pad=0.02)
    fig.savefig(FIGURE, dpi=150, bbox_inches="tight")
    plt.close(fig)

    fig, axes = plt.subplots(2, len(SHOWN), figsize=(3.6 * len(SHOWN), 5.6), sharex=True, sharey=True)
    days = (m["time"] - START) / pd.Timedelta(days=1) + 1
    for j, sec in enumerate(SHOWN):
        for i, (key, label) in enumerate((("lower", "10 to 40 m"), ("upper", "0 to 10 m"))):
            ax = axes[i, j]
            for s, colour in (("cmems", "#eb6834"), ("model", "#2a78d6")):
                ax.plot(days, pd.Series(series[sec, s][key]).rolling(25, center=True, min_periods=13).mean(),
                        color=colour, lw=1.6, label="CMEMS" if s == "cmems" else "model")
                if key == "lower":
                    ax.plot(days, pd.Series(series[sec, s]["geo"]).rolling(25, center=True, min_periods=13).mean(),
                            color=colour, lw=1, ls="--",
                            label=("CMEMS" if s == "cmems" else "model") + ", thermal wind from 60 m")
            ax.axhline(0, color="0.7", lw=0.5)
            ax.grid(alpha=0.3)
            ax.set_title(f"({'abcdefgh'[i * len(SHOWN) + j]}) {sec[:-1]}° N, {label}", loc="left", fontsize=9)
            if j == 0:
                ax.set_ylabel("northward current (m/s)")
            if i == 1:
                ax.set_xlabel("day of run")
    axes[0, 0].legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(FIGURE_SERIES, dpi=150)
    print(FIGURE, FIGURE_SERIES)
    return 0


if __name__ == "__main__":
    sys.exit(main())

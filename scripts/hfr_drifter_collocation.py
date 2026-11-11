"""Collocate the 2026 drifters with the CALYPSO HF radar, the model and CMEMS.

The velocity of each drifting unit is formed at every full hour of its track
inside domain B as the displacement between the positions interpolated linearly
in time half an hour before and half an hour after, so that it spans the hour
over which the radar averages. Fixes are about 30 minutes apart, so that each
estimate rests on two to three fixes.

At each such point and hour the following are taken.
- The total of the radar in the grid cell containing the drifter, with the
  overall flag equal to 1.
- For each Maltese radar station with data in the window, the radial velocity in
  the bin containing the drifter (nearest range within half a range cell and
  nearest bearing within half a bearing cell), filtered as in hfr_skill.py, set
  against the drifter velocity projected on the geodesic azimuth at the drifter
  pointing away from the antenna.
- The top layer of the model and the hourly CMEMS surface current, interpolated
  to the drifter position, with no spin-up excluded, since the drifters were
  released on the third day of each run.

The drifter is the reference. The units carry some windage, whose value is not
known (drifter_skill_2026.py), and the radar a share of the Stokes drift, so
neither is a pure Eulerian surface current.

Usage:
    python hfr_drifter_collocation.py [--figure]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import hfr_skill as hs  # noqa: E402

OUT = ROOT / "data" / "processed" / "hfr_drifter_collocation.csv"
METRICS = ROOT / "data" / "processed" / "hfr_drifter_metrics.csv"
FIGURE = ROOT / "figures" / "hfr_drifter_{}.png"
WINDOWS = {"may26": "may", "jul26": "jul"}
SITES = ("BARK", "CENC", "LAPS")


def drifter_hourly(window: str) -> pd.DataFrame:
    rows = []
    for dep, g in hs.tracks(window).groupby("deployment"):
        g = g.sort_values("time")
        t = g.time.values.astype("datetime64[s]").astype(float)
        hours = pd.date_range(g.time.min().ceil("h"), g.time.max().floor("h"), freq="h")
        for h in hours:
            th = h.to_datetime64().astype("datetime64[s]").astype(float)
            if th - 1800 < t[0] or th + 1800 > t[-1]:
                continue
            lon = np.interp([th - 1800, th, th + 1800], t, g.lon.values)
            lat = np.interp([th - 1800, th, th + 1800], t, g.lat.values)
            u = (lon[2] - lon[0]) * 111320 * np.cos(np.radians(lat[1])) / 3600
            v = (lat[2] - lat[0]) * 110540 / 3600
            rows.append(dict(deployment=dep, time=h, lon=lon[1], lat=lat[1], u=u, v=v))
    return pd.DataFrame(rows)


def collocate(window: str) -> pd.DataFrame:
    from pyproj import Geod
    cfg = hs.WINDOWS[window]
    d = drifter_hourly(window)
    times = d.time.values
    # totals in the containing cell
    tot = xr.open_dataset(hs.HFR / f"calypso_total_{window}.nc").squeeze("depth", drop=True)
    glon, glat = tot.longitude.values, tot.latitude.values
    ix = np.abs(glon[None, :] - d.lon.values[:, None]).argmin(1)
    iy = np.abs(glat[None, :] - d.lat.values[:, None]).argmin(1)
    it = np.array([np.flatnonzero(tot.time.values == t)[0] if (tot.time.values == t).any() else -1 for t in times])
    ok = it >= 0
    hu = np.full(len(d), np.nan)
    hv = np.full(len(d), np.nan)
    q = tot.QCflag.values
    eu, ev = tot.EWCT.values, tot.NSCT.values
    for k in np.flatnonzero(ok):
        if q[it[k], iy[k], ix[k]] == 1:
            hu[k], hv[k] = eu[it[k], iy[k], ix[k]], ev[it[k], iy[k], ix[k]]
    d["hfr_u"], d["hfr_v"] = hu, hv
    # model and CMEMS at the drifter
    fm = xr.open_dataset(ROOT / "model" / "hindcast" / cfg["case"] / "output" / f"{cfg['case']}_surface_map.nc")
    from regrid_wetwise_source import FastGridInterp
    interp = FastGridInterp(np.c_[fm.mesh2d_face_x.values, fm.mesh2d_face_y.values], np.c_[d.lon, d.lat])
    mu, mv = np.full(len(d), np.nan), np.full(len(d), np.nan)
    for t in np.unique(times):
        sel = times == t
        if t not in fm.time.values:
            continue
        snap = fm.sel(time=t)
        mu[sel] = interp(snap.mesh2d_ucx.values)[sel]
        mv[sel] = interp(snap.mesh2d_ucy.values)[sel]
    d["model_u"], d["model_v"] = mu, mv
    cu, cv = hs.cmems_at(cfg["cmems"], np.unique(times), d.lon.values, d.lat.values)
    tix = np.searchsorted(np.unique(times), times)
    d["cmems_u"], d["cmems_v"] = cu[tix, np.arange(len(d))], cv[tix, np.arange(len(d))]
    # radials of each Maltese station in the containing bin
    geod = Geod(ellps="WGS84")
    for site in SITES:
        path = hs.HFR / f"calypso_radial_{site}_{window}.nc"
        if not path.exists():
            continue
        ds = xr.open_dataset(path).squeeze("depth", drop=True)
        lon0, lat0 = float(ds.attrs["site_lon"]), float(ds.attrs["site_lat"])
        az, back, dist = geod.inv(np.full(len(d), lon0), np.full(len(d), lat0), d.lon.values, d.lat.values)
        rng, bear = ds.RNGE.values, ds.BEAR.values
        ir = np.abs(rng[None, :] - np.asarray(dist)[:, None] / 1000).argmin(1)
        dbear = (bear[None, :] - np.asarray(az)[:, None] % 360 + 180) % 360 - 180
        ib = np.abs(dbear).argmin(1)
        inside = (np.abs(rng[ir] - np.asarray(dist) / 1000) <= 1.51) & (np.abs(dbear[np.arange(len(d)), ib]) <= 2.5)
        good = np.isfinite(ds.RDVA.values)
        for test in hs.RADIAL_TESTS:
            good &= ds[test].values == 1
        good &= np.isin(ds.VART_QC.values, (0, 1))
        r = np.full(len(d), np.nan)
        for k in np.flatnonzero(inside):
            m = np.flatnonzero(ds.time.values == times[k])
            if m.size and good[m[0], ir[k], ib[k]]:
                r[k] = ds.RDVA.values[m[0], ir[k], ib[k]]
        away = np.radians((np.asarray(back) + 180) % 360)
        d[f"{site}_r"] = r
        for s in ("drifter", "model", "cmems", "hfr"):
            uu = d["u"] if s == "drifter" else d[f"{s}_u"]
            vv = d["v"] if s == "drifter" else d[f"{s}_v"]
            d[f"{site}_{s}_r"] = uu * np.sin(away) + vv * np.cos(away)
    d.insert(0, "window", window)
    return d


def component_stats(o, m) -> dict:
    """Correlation, rms difference and the regression m = a o + b with 95 per cent limits,
    the statistics of Capodici et al. (2019), Table 5."""
    from scipy import stats
    ok = np.isfinite(o) & np.isfinite(m)
    if ok.sum() < 4:
        return dict(n=int(ok.sum()))
    o, m = o[ok], m[ok]
    fit = stats.linregress(o, m)
    tq = stats.t.ppf(0.975, ok.sum() - 2)
    return dict(n=int(ok.sum()), R=fit.rvalue, rmsd=np.sqrt(((m - o) ** 2).mean()),
                a=fit.slope, a_lo=fit.slope - tq * fit.stderr, a_hi=fit.slope + tq * fit.stderr,
                b=fit.intercept, b_lo=fit.intercept - tq * fit.intercept_stderr,
                b_hi=fit.intercept + tq * fit.intercept_stderr)


def metrics(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    w = d.window.iloc[0]
    for s in ("hfr", "model", "cmems"):
        for comp in ("u", "v"):
            st = component_stats(d[comp].values, d[f"{s}_{comp}"].values)
            rows.append(dict(window=w, product=f"component {comp.upper()}", source=s, subset="all hours", **st))
    for s in ("hfr", "model", "cmems"):
        both = np.isfinite(d.hfr_u)
        for subset, sel in (("all hours", np.ones(len(d), bool)), ("hours with a radar total", both)):
            st = hs.vector_stats(d.u.values[sel], d.v.values[sel], d[f"{s}_u"].values[sel], d[f"{s}_v"].values[sel])
            rows.append(dict(window=w, product="vector", source=s, subset=subset, **st))
    for site in SITES:
        if f"{site}_r" not in d:
            continue
        for s, col in (("hfr", f"{site}_r"), ("model", f"{site}_model_r"), ("cmems", f"{site}_cmems_r")):
            sel = np.isfinite(d[f"{site}_r"])
            st = component_stats(d[f"{site}_drifter_r"].values[sel], d[col].values[sel])
            rows.append(dict(window=w, product=f"radial {site}", source=s, subset="hours with a radial", **st))
    return pd.DataFrame(rows)


def figure(d: pd.DataFrame) -> Path:
    import geopandas as gpd
    import matplotlib.pyplot as plt

    w = d.window.iloc[0]
    coast = gpd.read_file(hs.COAST)
    deps = sorted(d.deployment.unique())
    fig = plt.figure(figsize=(13, 3.0 * len(deps) + 1), layout="constrained")
    gs = fig.add_gridspec(len(deps) * 2, 2, width_ratios=[1, 2.4])
    ax = fig.add_subplot(gs[:, 0])
    coast.plot(ax=ax, color="#d9d4c7", edgecolor="#8c8678", linewidth=0.5)
    for dep, g in d.groupby("deployment"):
        ax.plot(g.lon, g.lat, color="k", lw=1.2)
        has = np.isfinite(g.hfr_u)
        ax.scatter(g.lon[has], g.lat[has], s=10, color="#2ca02c", zorder=5, label="radar total" if dep == deps[0] else None)
        ax.text(g.lon.iloc[0], g.lat.iloc[0], f" {dep.split('_')[0]}", fontsize=8)
    lon0, lon1, lat0, lat1 = d.lon.min() - 0.08, d.lon.max() + 0.08, d.lat.min() - 0.05, d.lat.max() + 0.05
    ax.set(xlim=(lon0, lon1), ylim=(lat0, lat1), aspect=1 / np.cos(np.radians((lat0 + lat1) / 2)),
           xlabel="Longitude (°E)", ylabel="Latitude (°N)")
    ax.legend(fontsize=8, loc="lower left")
    ax.set_title("(a) tracks, hours with a radar total", loc="left", fontsize=10)
    n = 0
    for dep in deps:
        g = d[d.deployment == dep]
        for comp in ("u", "v"):
            bx = fig.add_subplot(gs[n, 1])
            bx.plot(g.time, g[comp], color="k", lw=1.5, label="drifter")
            bx.plot(g.time, g[f"hfr_{comp}"], "o", ms=3, color="#2ca02c", label="radar total")
            bx.plot(g.time, g[f"model_{comp}"], color=hs.COLOURS["model"], lw=1.1, label="model")
            bx.plot(g.time, g[f"cmems_{comp}"], color=hs.COLOURS["cmems"], lw=1.1, label="CMEMS")
            bx.axhline(0, color="0.6", lw=0.6)
            bx.grid(alpha=0.3)
            bx.set_ylabel(f"{'Eastward' if comp == 'u' else 'Northward'} (m/s)", fontsize=8)
            bx.set_title(f"({'bcdefg'[n]}) unit {dep.split('_')[0]}", loc="left", fontsize=9)
            if n == 0:
                bx.legend(fontsize=7, ncol=4)
            n += 1
    path = Path(str(FIGURE).format(w))
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--figure", action="store_true")
    args = ap.parse_args(argv)
    parts, mets = [], []
    for w in WINDOWS:
        d = collocate(w)
        print(f"{w}: {len(d)} drifter hours, {np.isfinite(d.hfr_u).sum()} with a radar total, "
              + ", ".join(f"{s} {np.isfinite(d[f'{s}_r']).sum()}" for s in SITES if f"{s}_r" in d))
        parts.append(d)
        mets.append(metrics(d))
        if args.figure:
            print(f"  {figure(d)}")
    pd.concat(parts).to_csv(OUT, index=False, float_format="%.4f")
    m = pd.concat(mets, ignore_index=True)
    m.to_csv(METRICS, index=False, float_format="%.4g")
    cols = ["window", "product", "source", "subset", "n", "R", "rmsd", "a", "a_lo", "a_hi", "b",
            "rmse", "rho", "phase", "std_ratio", "uo", "vo", "um", "vm"]
    m = m[m.n > 0]
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(m[[c for c in cols if c in m]].round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

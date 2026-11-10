"""Score the surface currents of the 2026 runs against the drifter deployments of 2026.

Particles are released by OpenDrift (OceanDrift) at observed positions of the
drifting units, every RELEASE_EVERY hours along each track inside domain B, and
advected for SEGMENT_HOURS hours in the top-layer currents of the model, as
written by extract_surface_map.py, or in the hourly surface currents of the
CMEMS analysis-forecast product, the field that forces the boundary of the
model. Both fields are interpolated onto the same regular grid, with the land
mask of the model mesh, so that the two sources differ in the current alone.
Points off the water take the values of the nearest wet point, as in
extract_harbour_currents_3d.py. The 10 m wind of ERA5 enters as a fraction of
the wind speed added to the drift, tested over WINDAGES since the drogue of
the units is not known.

Each particle is deterministic, with no random walk, as in the drifter
validation of StagnoneDT, where the diffusivity set was not applied by
OpenDrift 1.14. The track of each segment is scored on the output times of
OpenDrift, the observed fixes being interpolated linearly in time onto them,
by the separation from the observed position and by the skill score of Liu
and Weisberg (2011), one minus the sum of the separations normalised by the
cumulative length of the observed track, floored at zero.

Usage:
    python drifter_skill_2026.py [--month may jul] [--figure]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "StagnoneDT" / "scripts"))
from regrid_wetwise_source import FastGridInterp, wet_mask  # noqa: E402

RECORD = ROOT / "data" / "processed" / "drifters_2026.csv"
OUT = ROOT / "outputs" / "drifters_2026"
METRICS = ROOT / "data" / "processed" / "drifter_skill_2026.csv"
FIGURE = ROOT / "figures" / "drifter_skill_2026_{}.png"
COAST = ROOT / "data" / "processed" / "malta_coastline_wgs84.gpkg"

MONTHS = {
    "may": dict(case="v03_3d20s_0517_0522_uv_thd_2026", forcing="2026-05",
                box=(14.30, 14.56, 35.88, 36.06), step=0.001,
                extent=(14.355, 14.485, 35.925, 36.015), title="20 to 21 May 2026"),
    "jul": dict(case="v03_3d20s_0703_0709_uv_thd_2026", forcing="2026-07",
                box=(14.03, 15.01, 35.69, 36.31), step=0.002,
                extent=(14.30, 14.90, 35.68, 36.20), title="6 to 8 July 2026"),
}
SEGMENT_HOURS = 24
RELEASE_EVERY = 6                     # hours between releases along a track
WINDAGES = (0.0, 0.01, 0.02, 0.03)
TIME_STEP = 300                       # s
OUTPUT_STEP = 900                     # s, scoring grid
SEPARATION_HOURS = (6, 12, 24)
COLOURS = {"model": "#2a78d6", "cmems": "#eb6834"}


def haversine_m(lon1, lat1, lon2, lat2):
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    a = (np.sin((phi2 - phi1) / 2) ** 2
         + np.cos(phi1) * np.cos(phi2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2)
    return 2 * 6371000.0 * np.arcsin(np.sqrt(a))


def liu_weisberg(olon, olat, slon, slat) -> float:
    d = haversine_m(olon, olat, slon, slat)
    L = np.cumsum(np.r_[0.0, haversine_m(olon[:-1], olat[:-1], olon[1:], olat[1:])])
    ok = L > 0
    return max(0.0, 1.0 - (d[ok] / L[ok]).sum() / ok.sum()) if ok.any() else np.nan


def segments(record: pd.DataFrame, month: str) -> pd.DataFrame:
    """Release time and position of each segment, at observed fixes."""
    d = record[(record.status == "drifting") & record.in_domain_b
               & record.deployment.str.endswith(month)]
    rows = []
    for dep, g in d.groupby("deployment"):
        g = g.sort_values("time")
        t0, t1 = g.time.iloc[0], g.time.iloc[-1]
        k = 0
        # a tolerance of one fix interval keeps a segment ending on the last fix
        while t0 + pd.Timedelta(hours=k * RELEASE_EVERY + SEGMENT_HOURS) <= t1 + pd.Timedelta(minutes=30):
            i = (g.time - (t0 + pd.Timedelta(hours=k * RELEASE_EVERY))).abs().idxmin()
            rows.append(dict(deployment=dep, buoy=g.buoy.iloc[0], segment=k,
                             t0=g.time[i], lon0=g.lon[i], lat0=g.lat[i]))
            k += 1
    return pd.DataFrame(rows)


def era5_wind(forcing: str, glon, glat, times) -> tuple[np.ndarray, np.ndarray]:
    out = []
    for var in ("u10", "v10"):
        ds = xr.open_dataset(ROOT / "data" / "raw" / f"era5_{forcing}" / f"era5_{var}_{forcing}.nc")
        da = ds[var].rename(valid_time="time").sortby("latitude")
        da = da.interp(time=times).interp(latitude=glat, longitude=glon)
        out.append(da.transpose("time", "latitude", "longitude").values.astype(np.float32))
    return out[0], out[1]


def write_reader(path: Path, times, glon, glat, u, v, uw, vw, mask) -> None:
    ds = xr.Dataset(
        {"x_sea_water_velocity": (("time", "lat", "lon"), u, {"standard_name": "x_sea_water_velocity", "units": "m s-1"}),
         "y_sea_water_velocity": (("time", "lat", "lon"), v, {"standard_name": "y_sea_water_velocity", "units": "m s-1"}),
         "x_wind": (("time", "lat", "lon"), uw, {"standard_name": "x_wind", "units": "m s-1"}),
         "y_wind": (("time", "lat", "lon"), vw, {"standard_name": "y_wind", "units": "m s-1"}),
         "land_binary_mask": (("lat", "lon"), (~mask).astype(np.int8), {"standard_name": "land_binary_mask"})},
        coords={"time": times,
                "lat": ("lat", glat, {"standard_name": "latitude", "units": "degrees_north"}),
                "lon": ("lon", glon, {"standard_name": "longitude", "units": "degrees_east"})})
    ds.to_netcdf(path, encoding={k: {"zlib": True, "complevel": 4} for k in ds.data_vars})


def build_readers(month: str) -> dict[str, Path]:
    """Model and CMEMS surface currents with the ERA5 wind on one regular grid."""
    cfg = MONTHS[month]
    OUT.mkdir(parents=True, exist_ok=True)
    paths = {s: OUT / f"{month}_{s}.nc" for s in ("model", "cmems")}
    if all(p.exists() for p in paths.values()):
        return paths
    lon0, lon1, lat0, lat1 = cfg["box"]
    glon = np.arange(lon0, lon1 + cfg["step"] / 2, cfg["step"])
    glat = np.arange(lat0, lat1 + cfg["step"] / 2, cfg["step"])
    L, A = np.meshgrid(glon, glat)

    case = ROOT / "model" / "hindcast" / cfg["case"] / "output" / f"{cfg['case']}_surface_map.nc"
    fm = xr.open_dataset(case)
    mask = wet_mask(fm.mesh2d_face_x_bnd.values, fm.mesh2d_face_y_bnd.values, glon, glat)
    _, (iy, ix) = distance_transform_edt(~mask, return_indices=True)
    interp = FastGridInterp(np.c_[fm.mesh2d_face_x.values, fm.mesh2d_face_y.values],
                            np.c_[L.ravel(), A.ravel()][mask.ravel()])
    times = fm.time.values

    def to_grid(values):
        g = np.full(mask.size, np.nan, np.float32)
        g[mask.ravel()] = interp(values)
        g = g.reshape(mask.shape)
        # wet grid points outside the triangulation of the face centres take their nearest neighbour too
        ok = np.isfinite(g)
        _, (jy, jx) = distance_transform_edt(~ok, return_indices=True)
        return g[jy, jx]

    u = np.stack([to_grid(fm.mesh2d_ucx.values[i]) for i in range(times.size)])
    v = np.stack([to_grid(fm.mesh2d_ucy.values[i]) for i in range(times.size)])
    uw, vw = era5_wind(cfg["forcing"], glon, glat, times)
    write_reader(paths["model"], times, glon, glat, u, v, uw, vw, mask)
    print(f"{month} model: grid {glon.size} x {glat.size}, {int(mask.sum())} wet points, {times.size} times")

    src = sorted((ROOT / "data" / "raw" / f"cmems_{cfg['forcing']}").glob("cmems-surface-1h_*.nc"))[0]
    cm = xr.open_dataset(src).sel(time=slice(times[0], times[-1]))
    cu, cv = [], []
    for var, acc in (("uo", cu), ("vo", cv)):
        for i in range(cm.time.size):
            f = cm[var].isel(time=i).values
            ok = np.isfinite(f)
            _, (jy, jx) = distance_transform_edt(~ok, return_indices=True)
            # coastal cells absent from CMEMS take the nearest sea cell before the bilinear interpolation
            filled = xr.DataArray(f[jy, jx], coords={"latitude": cm.latitude, "longitude": cm.longitude},
                                  dims=("latitude", "longitude"))
            acc.append(filled.interp(latitude=glat, longitude=glon).values.astype(np.float32))
    uw, vw = era5_wind(cfg["forcing"], glon, glat, cm.time.values)
    write_reader(paths["cmems"], cm.time.values, glon, glat, np.stack(cu), np.stack(cv), uw, vw, mask)
    print(f"{month} cmems: {cm.time.size} hourly fields from {src.name}")
    return paths


def simulate(reader: Path, seg: pd.DataFrame, windage: float, out: Path) -> Path:
    from opendrift.models.oceandrift import OceanDrift
    from opendrift.readers import reader_netCDF_CF_generic

    o = OceanDrift(loglevel=50)
    o.add_reader(reader_netCDF_CF_generic.Reader(str(reader)))
    for key, value in {"general:use_auto_landmask": False,
                       "general:coastline_action": "previous",
                       "drift:advection_scheme": "runge-kutta4",
                       "drift:vertical_mixing": False,
                       "environment:constant:horizontal_diffusivity": 0.0}.items():
        o.set_config(key, value)
    for _, s in seg.iterrows():
        o.seed_elements(lon=s.lon0, lat=s.lat0, z=0, time=s.t0.to_pydatetime(),
                        number=1, wind_drift_factor=windage)
    # the run starts at the first release, so the output times follow it in steps of OUTPUT_STEP
    o.run(end_time=(seg.t0.max() + pd.Timedelta(hours=SEGMENT_HOURS)).to_pydatetime(),
          time_step=TIME_STEP, time_step_output=OUTPUT_STEP, outfile=str(out),
          export_variables=["lon", "lat"])
    return out


def score(sim: Path, seg: pd.DataFrame, record: pd.DataFrame) -> list[dict]:
    with xr.open_dataset(sim) as ds:
        lon, lat = ds.lon.values, ds.lat.values
        times = pd.to_datetime(ds.time.values)
    ts = times.values.astype("datetime64[s]").astype(float)
    rows = []
    for n, s in enumerate(seg.itertuples()):
        obs = record[(record.deployment == s.deployment) & (record.status == "drifting")].sort_values("time")
        ot = obs.time.values.astype("datetime64[s]").astype(float)
        t0 = s.t0.to_datetime64().astype("datetime64[s]").astype(float)
        # half an output step of tolerance, the output times following the first release of the run
        m = ((ts >= t0) & (ts <= t0 + SEGMENT_HOURS * 3600 + OUTPUT_STEP / 2) & (ts <= ot.max())
             & np.isfinite(lon[n]))
        if m.sum() < 3:
            continue
        t = ts[m]
        olon, olat = np.interp(t, ot, obs.lon.values), np.interp(t, ot, obs.lat.values)
        # the release fix itself opens the scored track
        olon, olat = np.r_[s.lon0, olon], np.r_[s.lat0, olat]
        slon, slat = np.r_[s.lon0, lon[n][m]], np.r_[s.lat0, lat[n][m]]
        tt = np.r_[t0, t]
        d = haversine_m(olon, olat, slon, slat)
        row = dict(deployment=s.deployment, buoy=s.buoy, segment=s.segment, t0=s.t0,
                   hours=(tt[-1] - t0) / 3600, lw=liu_weisberg(olon, olat, slon, slat),
                   obs_path_km=haversine_m(olon[:-1], olat[:-1], olon[1:], olat[1:]).sum() / 1e3,
                   sim_path_km=haversine_m(slon[:-1], slat[:-1], slon[1:], slat[1:]).sum() / 1e3)
        for h in SEPARATION_HOURS:
            k = np.flatnonzero(np.abs(tt - t0 - h * 3600) <= OUTPUT_STEP / 2)
            row[f"sep_{h}h_km"] = d[k[0]] / 1e3 if k.size else np.nan
        rows.append(row)
    return rows


def figure(month: str, metrics: pd.DataFrame, record: pd.DataFrame) -> Path:
    import geopandas as gpd
    import matplotlib.pyplot as plt

    cfg = MONTHS[month]
    mm = metrics[metrics.month == month]
    best = mm[mm.source == "model"].groupby("windage").lw.mean().idxmax()
    coast = gpd.read_file(COAST)
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(12, 5.4), gridspec_kw=dict(width_ratios=[1.5, 1]))
    coast.plot(ax=ax, color="#d9d4c7", edgecolor="#8c8678", linewidth=0.5)
    obs = record[(record.status == "drifting") & record.in_domain_b & record.deployment.str.endswith(month)]
    for dep, g in obs.groupby("deployment"):
        ax.plot(g.lon, g.lat, color="k", lw=1.6, label="observed" if dep.startswith("9") else None)
    seg = segments(record, month)
    for source in ("model", "cmems"):
        with xr.open_dataset(OUT / f"{month}_{source}_w{best:.2f}.nc") as ds:
            times = pd.to_datetime(ds.time.values)
            # each particle drawn over its scored segment alone, the run carrying it to the last release
            for n, t0 in enumerate(seg.t0):
                m = (times >= t0) & (times <= t0 + pd.Timedelta(hours=SEGMENT_HOURS))
                ax.plot(np.r_[seg.lon0[n], ds.lon[n].values[m]], np.r_[seg.lat0[n], ds.lat[n].values[m]],
                        color=COLOURS[source], lw=0.9, alpha=0.85,
                        label=f"{'model' if source == 'model' else 'CMEMS'}, windage {best:.0%}" if n == 0 else None)
    ax.scatter(seg.lon0, seg.lat0, s=14, color="k", zorder=5, label="release")
    lon0, lon1, lat0, lat1 = cfg["extent"]
    ax.set(xlim=(lon0, lon1), ylim=(lat0, lat1), aspect=1 / np.cos(np.radians((lat0 + lat1) / 2)),
           xlabel="Longitude (°E)", ylabel="Latitude (°N)")
    ax.set_title(f"(a) {cfg['title']}, segments of {SEGMENT_HOURS} h", loc="left", fontsize=10)
    ax.legend(fontsize=8, loc="best")
    for source in ("model", "cmems"):
        g = mm[mm.source == source].groupby("windage").lw
        w = np.array(g.mean().index) * 100
        bx.fill_between(w, g.min(), g.max(), color=COLOURS[source], alpha=0.15, lw=0)
        bx.plot(w, g.mean(), "o-", color=COLOURS[source], label="model" if source == "model" else "CMEMS")
    bx.set(xlabel="Windage (% of the 10 m wind)", ylabel="Liu-Weisberg skill", ylim=(0, 1))
    bx.set_title(f"(b) mean and range over {len(seg)} segments", loc="left", fontsize=10)
    bx.legend(fontsize=8)
    bx.grid(alpha=0.3)
    fig.tight_layout()
    path = Path(str(FIGURE).format(month))
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def along_track(month: str, record: pd.DataFrame) -> pd.DataFrame:
    """Velocity of the units from fix to fix against both fields at the same place and time."""
    obs = record[(record.status == "drifting") & record.in_domain_b & record.deployment.str.endswith(month)]
    parts = []
    for _, g in obs.groupby("deployment"):
        g = g.sort_values("time")
        dt = np.diff(g.time.values).astype("timedelta64[s]").astype(float)
        lat = g.lat.values
        parts.append(pd.DataFrame(dict(
            time=g.time.values[:-1] + np.diff(g.time.values) / 2,
            lon=(g.lon.values[:-1] + g.lon.values[1:]) / 2, lat=(lat[:-1] + lat[1:]) / 2,
            u=np.diff(g.lon.values) * 111320 * np.cos(np.radians(lat[:-1])) / dt,
            v=np.diff(lat) * 110540 / dt)))
    o = pd.concat(parts, ignore_index=True)
    rows = [dict(source="observed", n=len(o), u=o.u.mean(), v=o.v.mean(), speed=np.hypot(o.u, o.v).mean())]
    for source in ("model", "cmems"):
        with xr.open_dataset(OUT / f"{month}_{source}.nc") as ds:
            pts = {k: xr.DataArray(o[k].values, dims="p") for k in ("time", "lon", "lat")}
            u = ds.x_sea_water_velocity.interp(**pts).values
            v = ds.y_sea_water_velocity.interp(**pts).values
        ok = np.isfinite(u)
        rows.append(dict(source=source, n=int(ok.sum()), u=u[ok].mean(), v=v[ok].mean(),
                         speed=np.hypot(u[ok], v[ok]).mean()))
    return pd.DataFrame(rows)


def field_figure(month: str, record: pd.DataFrame) -> Path:
    """Mean surface current of both fields over the drifting part of the deployment."""
    import geopandas as gpd
    import matplotlib.pyplot as plt

    obs = record[(record.status == "drifting") & record.in_domain_b & record.deployment.str.endswith(month)]
    window = slice(obs.time.min(), obs.time.max())
    coast = gpd.read_file(COAST)
    fig, axs = plt.subplots(1, 2, figsize=(12.5, 4.8), sharey=True, layout="constrained")
    for ax, source, label in zip(axs, ("model", "cmems"), ("(a) model, top layer", "(b) CMEMS, hourly surface")):
        with xr.open_dataset(OUT / f"{month}_{source}.nc") as ds:
            mean = ds.sel(time=window).mean("time")
            u, v = mean.x_sea_water_velocity.values, mean.y_sea_water_velocity.values
            land = ds.land_binary_mask.values == 1
            glon, glat = ds.lon.values, ds.lat.values
        u, v = np.where(land, np.nan, u), np.where(land, np.nan, v)
        pc = ax.pcolormesh(glon, glat, np.hypot(u, v), vmin=0, vmax=0.4, cmap="viridis", shading="auto")
        k = max(1, glon.size // 40)
        L, A = np.meshgrid(glon[::k], glat[::k])
        ax.quiver(L, A, u[::k, ::k], v[::k, ::k], scale=4, width=0.0025, color="w")
        coast.plot(ax=ax, color="#d9d4c7", edgecolor="#8c8678", linewidth=0.5)
        for _, g in obs.groupby("deployment"):
            ax.plot(g.lon, g.lat, color="#e8402e", lw=1.4)
        lat0, lat1 = glat[0], glat[-1]
        ax.set(xlim=(glon[0], glon[-1]), ylim=(lat0, lat1), xlabel="Longitude (°E)",
               aspect=1 / np.cos(np.radians((lat0 + lat1) / 2)))
        ax.set_title(label, loc="left", fontsize=10)
    axs[0].set_ylabel("Latitude (°N)")
    fig.colorbar(pc, ax=axs, shrink=0.8, label="Mean speed (m/s)")
    path = Path(str(FIGURE).format(f"{month}_field"))
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--month", nargs="+", choices=tuple(MONTHS), default=list(MONTHS))
    ap.add_argument("--figure", action="store_true")
    args = ap.parse_args(argv)
    record = pd.read_csv(RECORD, parse_dates=["time"])
    record["deployment"] = record.deployment.fillna("")
    rows = []
    for month in args.month:
        seg = segments(record, month)
        print(f"{month}: {len(seg)} segments of {SEGMENT_HOURS} h")
        for source, reader in build_readers(month).items():
            for w in WINDAGES:
                sim = simulate(reader, seg, w, OUT / f"{month}_{source}_w{w:.2f}.nc")
                for r in score(sim, seg, record):
                    rows.append(dict(month=month, source=source, windage=w, **r))
    metrics = pd.DataFrame(rows)
    if METRICS.exists():
        old = pd.read_csv(METRICS, parse_dates=["t0"])
        metrics = pd.concat([old[~old.month.isin(args.month)], metrics], ignore_index=True)
    metrics.to_csv(METRICS, index=False, float_format="%.4f")
    summary = metrics.groupby(["month", "source", "windage"]).agg(
        n=("lw", "size"), lw=("lw", "mean"), sep_6h=("sep_6h_km", "mean"),
        sep_12h=("sep_12h_km", "mean"), sep_24h=("sep_24h_km", "mean"),
        path_ratio=("sim_path_km", "sum")).reset_index()
    summary["path_ratio"] /= metrics.groupby(["month", "source", "windage"]).obs_path_km.sum().values
    print(summary.round(3).to_string(index=False))
    for month in args.month:
        print(f"{month}, velocity along the tracks (m/s)")
        print(along_track(month, record).round(3).to_string(index=False))
    if args.figure:
        for month in args.month:
            print(f"wrote {figure(month, metrics, record)}")
            print(f"wrote {field_figure(month, record)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

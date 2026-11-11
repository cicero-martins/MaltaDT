"""Compare the surface currents of the hindcast runs with the CALYPSO HF radar.

The hourly totals of the network and the radial velocities of the station at
Ta' Barkat (BARK), some 2 km east of the mouth of the Grand Harbour, written by
download_hfr_calypso.py, are compared with the top layer of the model, from the
surface map written by extract_surface_map.py, and where available with the
hourly surface current of the CMEMS analysis-forecast product, the field that
forces the boundary of the model.

Only radar cells inside the mesh of domain B are kept. Totals enter with the
overall quality flag of the European HFR Node equal to 1 (good). For the
radials the overall flag is 4 at every cell of every station, set by the
average radial bearing test (AVRB_QC) alone, a test of the station as a whole,
so the radials enter when every other test is passed or, for the temporal
derivative test (VART_QC), not performed. Bin positions follow from the range
and bearing on the WGS84 ellipsoid about the site. The radial velocity RDVA is
positive away from the antenna along the bearing of the bin, the convention by
which the files themselves compose EWCT and NSCT, while the published direction
of the radial vector (DRVA), labelled as pointing away from the instrument,
lies 180 degrees from the bearing and points towards it. The modelled radial
velocity is therefore the projection of the current on the geodesic azimuth at
the bin pointing away from the antenna, and not on DRVA.

The model starts from rest, so the first SPINUP_HOURS hours are excluded. The
model is interpolated linearly between face centres at each radar cell, a point
value set against a radar estimate over a cell of some 3 km. Statistics are the
mean vectors, the bias of each component, the root mean square of the vector
difference and the complex correlation of Kundu (1976) on the demeaned series,
whose modulus measures the agreement of the fluctuations and whose phase the
mean veering of the model from the radar, positive anticlockwise. They are
computed over all cells and hours pooled, cell by cell, and over the corridor
of the drifter tracks of the same month, the radar cells within CORRIDOR_KM of
any drifting fix inside domain B, both pooled and as the series averaged over
the corridor at each hour. The window of 2025 has no drifters and takes the
corridor of July 2026, so that the two summers are scored over the same water.
The direct comparison with the drifters, fix by fix, is made by
hfr_drifter_collocation.py.

Usage:
    python hfr_skill.py [--window may26 jul26 jul25] [--figure]
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
from regrid_wetwise_source import FastGridInterp  # noqa: E402

HFR = ROOT / "data" / "raw" / "hfr_calypso"
METRICS = ROOT / "data" / "processed" / "hfr_skill.csv"
FIGURE = ROOT / "figures" / "hfr_skill_{}.png"
COAST = ROOT / "data" / "processed" / "malta_coastline_wgs84.gpkg"

WINDOWS = {
    "may26": dict(case="v03_3d20s_0517_0522_uv_thd_2026", cmems="2026-05", title="17 to 22 May 2026"),
    "jul26": dict(case="v03_3d20s_0703_0709_uv_thd_2026", cmems="2026-07", title="3 to 9 July 2026"),
    "jul25": dict(case="v03_3d20s_0722_0801_uv_thd", cmems=None, title="22 July to 1 August 2025"),
}
SITE = "BARK"
SPINUP_HOURS = 72
DRIFTERS = ROOT / "data" / "processed" / "drifters_2026.csv"
TRACKS = {"may26": "may", "jul26": "jul", "jul25": "jul"}
CORRIDOR_KM = 5.0
RADIAL_TESTS = ("OWTR_QC", "CSPD_QC", "MDFL_QC", "RDCT_QC", "POSITION_QC")
COLOURS = {"hfr": "k", "model": "#2a78d6", "cmems": "#eb6834"}
LABELS = {"hfr": "HF radar", "model": "model, top layer", "cmems": "CMEMS, hourly surface"}


# -- fields -------------------------------------------------------------------

def domain(fm: xr.Dataset):
    """Union of the mesh faces, the wet area of domain B."""
    import shapely
    xb, yb = fm.mesh2d_face_x_bnd.values, fm.mesh2d_face_y_bnd.values
    polys = []
    for px, py in zip(xb, yb):
        ok = np.isfinite(px)
        polys.append(shapely.Polygon(np.c_[px[ok], py[ok]]))
    return shapely.union_all(shapely.make_valid(np.array(polys)))


def inside(area, lon, lat) -> np.ndarray:
    import shapely
    return shapely.contains_xy(area, lon, lat)


def model_at(fm: xr.Dataset, times, lon, lat) -> tuple[np.ndarray, np.ndarray]:
    interp = FastGridInterp(np.c_[fm.mesh2d_face_x.values, fm.mesh2d_face_y.values], np.c_[lon, lat])
    sub = fm.sel(time=times)
    u = np.stack([interp(sub.mesh2d_ucx.values[i]) for i in range(len(times))])
    v = np.stack([interp(sub.mesh2d_ucy.values[i]) for i in range(len(times))])
    return u, v


def cmems_at(month: str, times, lon, lat) -> tuple[np.ndarray, np.ndarray]:
    src = sorted((ROOT / "data" / "raw" / f"cmems_{month}").glob("cmems-surface-1h_*.nc"))[0]
    cm = xr.open_dataset(src).sel(time=times)
    out = []
    pts = dict(longitude=xr.DataArray(lon, dims="p"), latitude=xr.DataArray(lat, dims="p"))
    for var in ("uo", "vo"):
        f = cm[var].squeeze(drop=True).values
        filled = np.empty_like(f)
        for i in range(f.shape[0]):
            ok = np.isfinite(f[i])
            _, (jy, jx) = distance_transform_edt(~ok, return_indices=True)
            # coastal cells absent from CMEMS take the nearest sea cell, as in drifter_skill_2026.py
            filled[i] = f[i][jy, jx]
        da = xr.DataArray(filled, dims=("time", "latitude", "longitude"),
                          coords=dict(latitude=cm.latitude, longitude=cm.longitude))
        out.append(da.interp(**pts).values)
    return out[0], out[1]


def totals(window: str, area, t_ok) -> dict:
    ds = xr.open_dataset(HFR / f"calypso_total_{window}.nc").squeeze("depth", drop=True)
    ds = ds.sel(time=[t for t in ds.time.values if t in t_ok])
    L, A = np.meshgrid(ds.longitude.values, ds.latitude.values)
    keep = inside(area, L.ravel(), A.ravel())
    flat = lambda a: a.reshape(a.shape[0], -1)[:, keep]   # noqa: E731
    good = flat(ds.QCflag.values) == 1
    u = np.where(good, flat(ds.EWCT.values), np.nan)
    v = np.where(good, flat(ds.NSCT.values), np.nan)
    return dict(times=ds.time.values, lon=L.ravel()[keep], lat=A.ravel()[keep], u=u, v=v)


def radials(window: str, area, t_ok) -> dict:
    from pyproj import Geod
    ds = xr.open_dataset(HFR / f"calypso_radial_{SITE}_{window}.nc").squeeze("depth", drop=True)
    ds = ds.sel(time=[t for t in ds.time.values if t in t_ok])
    if ds.time.size == 0:
        return {}
    R, B = np.meshgrid(ds.RNGE.values, ds.BEAR.values, indexing="ij")
    lon0, lat0 = float(ds.attrs["site_lon"]), float(ds.attrs["site_lat"])
    lon, lat, back = Geod(ellps="WGS84").fwd(np.full(R.size, lon0), np.full(R.size, lat0),
                                             B.ravel(), R.ravel() * 1000.0)
    away = (np.asarray(back) + 180.0) % 360.0   # azimuth at the bin pointing away from the antenna
    keep = inside(area, lon, lat)
    flat = lambda a: a.reshape(a.shape[0], -1)[:, keep]   # noqa: E731
    good = np.isfinite(flat(ds.RDVA.values))
    for test in RADIAL_TESTS:
        good &= flat(ds[test].values) == 1
    good &= np.isin(flat(ds.VART_QC.values), (0, 1))
    return dict(times=ds.time.values, lon=lon[keep], lat=lat[keep],
                r=np.where(good, flat(ds.RDVA.values), np.nan),
                dir=np.broadcast_to(away[keep], (ds.time.size, int(keep.sum()))))


# -- statistics ---------------------------------------------------------------

def vector_stats(uo, vo, um, vm) -> dict:
    ok = np.isfinite(uo) & np.isfinite(vo) & np.isfinite(um) & np.isfinite(vm)
    if ok.sum() < 3:
        return dict(n=int(ok.sum()))
    uo, vo, um, vm = uo[ok], vo[ok], um[ok], vm[ok]
    wo, wm = uo + 1j * vo, um + 1j * vm
    a, b = wo - wo.mean(), wm - wm.mean()
    rho = (np.conj(a) * b).mean() / np.sqrt((np.abs(a) ** 2).mean() * (np.abs(b) ** 2).mean())
    return dict(n=int(ok.sum()), uo=uo.mean(), vo=vo.mean(), um=um.mean(), vm=vm.mean(),
                bias_u=(um - uo).mean(), bias_v=(vm - vo).mean(),
                rmse=np.sqrt((np.abs(wm - wo) ** 2).mean()),
                speed_o=np.abs(wo).mean(), speed_m=np.abs(wm).mean(),
                rho=np.abs(rho), phase=np.degrees(np.angle(rho)),
                std_ratio=np.sqrt((np.abs(b) ** 2).mean() / (np.abs(a) ** 2).mean()))


def scalar_stats(ro, rm) -> dict:
    ok = np.isfinite(ro) & np.isfinite(rm)
    if ok.sum() < 3:
        return dict(n=int(ok.sum()))
    ro, rm = ro[ok], rm[ok]
    return dict(n=int(ok.sum()), mean_o=ro.mean(), mean_m=rm.mean(), bias=(rm - ro).mean(),
                rmse=np.sqrt(((rm - ro) ** 2).mean()), r=np.corrcoef(ro, rm)[0, 1],
                std_ratio=rm.std() / ro.std())


def tracks(window: str) -> pd.DataFrame:
    rec = pd.read_csv(DRIFTERS, parse_dates=["time"])
    return rec[(rec.status == "drifting") & rec.in_domain_b
               & rec.deployment.fillna("").str.endswith(TRACKS[window])]


def in_box(window: str, lon, lat) -> np.ndarray:
    """True for radar cells within CORRIDOR_KM of a drifting fix of the month."""
    from scipy.spatial import cKDTree
    fx = tracks(window)
    k = np.cos(np.radians(36.0))
    tree = cKDTree(np.c_[fx.lon.values * 111.32 * k, fx.lat.values * 110.57])
    d, _ = tree.query(np.c_[np.asarray(lon) * 111.32 * k, np.asarray(lat) * 110.57])
    return d <= CORRIDOR_KM


def draw_tracks(ax, window: str) -> None:
    for _, g in tracks(window).groupby("deployment"):
        ax.plot(g.lon, g.lat, color="#e8402e", lw=1.2)


def box_series(u, v, sel, min_cells: int = 5):
    """Mean over the corridor at each hour, only hours with at least min_cells radar cells."""
    ok = np.isfinite(u[:, sel])
    n = ok.sum(1)
    with np.errstate(invalid="ignore"):
        bu = np.where(n >= min_cells, np.nanmean(np.where(ok, u[:, sel], np.nan), 1), np.nan)
        bv = np.where(n >= min_cells, np.nanmean(np.where(ok, v[:, sel], np.nan), 1), np.nan)
    return bu, bv


# -- driver -------------------------------------------------------------------

def run(window: str, figure: bool) -> list[dict]:
    cfg = WINDOWS[window]
    fm = xr.open_dataset(ROOT / "model" / "hindcast" / cfg["case"] / "output" / f"{cfg['case']}_surface_map.nc")
    t_model = pd.to_datetime(fm.time.values)
    t_ok = set(t_model[(t_model >= t_model[0] + pd.Timedelta(hours=SPINUP_HOURS)) & (t_model.minute == 0)]
               .to_numpy())
    area = domain(fm)
    rows = []

    tot = totals(window, area, t_ok)
    fields = {"hfr": (tot["u"], tot["v"])}
    fields["model"] = model_at(fm, tot["times"], tot["lon"], tot["lat"])
    if cfg["cmems"]:
        fields["cmems"] = cmems_at(cfg["cmems"], tot["times"], tot["lon"], tot["lat"])
    # every source on the cells and hours where the radar holds a good total
    mask = np.isfinite(tot["u"])
    for s in fields:
        fields[s] = tuple(np.where(mask, f, np.nan) for f in fields[s])
    box = in_box(window, tot["lon"], tot["lat"])
    print(f"{window}: {len(tot['times'])} hours after spin-up, {tot['lon'].size} total cells in domain B, "
          f"{mask.sum()} good values, {box.sum()} cells in the track corridor")
    for s in fields:
        if s == "hfr":
            continue
        for region, sel in (("domain B", slice(None)), ("track corridor", box)):
            st = vector_stats(fields["hfr"][0][:, sel].ravel(), fields["hfr"][1][:, sel].ravel(),
                              fields[s][0][:, sel].ravel(), fields[s][1][:, sel].ravel())
            rows.append(dict(window=window, product="total", source=s, region=region, **st))
        bo, bm = box_series(*fields["hfr"], box), box_series(*fields[s], box)
        st = vector_stats(bo[0], bo[1], bm[0], bm[1])
        rows.append(dict(window=window, product="total", source=s, region="track corridor mean", **st))

    rad = radials(window, area, t_ok)
    if not rad:
        print(f"  radials {SITE}: no hours after spin-up")
        if figure:
            print(f"  {field_figure(window, tot, fields)}")
            print(f"  {series_figure(window, tot, fields, box)}")
        return rows
    rfields = {"hfr": rad["r"]}
    th = np.radians(rad["dir"])
    um, vm = model_at(fm, rad["times"], rad["lon"], rad["lat"])
    rfields["model"] = um * np.sin(th) + vm * np.cos(th)
    if cfg["cmems"]:
        uc, vc = cmems_at(cfg["cmems"], rad["times"], rad["lon"], rad["lat"])
        rfields["cmems"] = uc * np.sin(th) + vc * np.cos(th)
    rbox = in_box(window, rad["lon"], rad["lat"])
    print(f"  radials {SITE}: {rad['lon'].size} bins in domain B, {np.isfinite(rad['r']).sum()} good values")
    for s in rfields:
        if s == "hfr":
            continue
        for region, sel in (("domain B", slice(None)), ("track corridor", rbox)):
            st = scalar_stats(rad["r"][:, sel].ravel(), rfields[s][:, sel].ravel())
            rows.append(dict(window=window, product=f"radial {SITE}", source=s, region=region, **st))

    if figure:
        print(f"  {radial_figure(window, rad, rfields, rbox)}")
        print(f"  {field_figure(window, tot, fields)}")
        print(f"  {series_figure(window, tot, fields, box)}")
    return rows


def field_figure(window: str, tot: dict, fields: dict) -> Path:
    """Mean current over the hours after spin-up and the complex correlation by cell."""
    import geopandas as gpd
    import matplotlib.pyplot as plt

    coast = gpd.read_file(COAST)
    sources = list(fields)
    lon, lat = tot["lon"], tot["lat"]
    n_ok = np.isfinite(fields["hfr"][0]).sum(0)
    show = n_ok >= 0.5 * len(tot["times"])
    fig, axs = plt.subplots(2, len(sources), figsize=(4.4 * len(sources), 8.2), layout="constrained",
                            sharex=True, sharey=True)
    lon0, lon1, lat0, lat1 = 14.04, 15.00, 35.69, 36.30
    for k, s in enumerate(sources):
        ax = axs[0, k]
        with np.errstate(invalid="ignore"):
            mu, mv = np.nanmean(fields[s][0], 0), np.nanmean(fields[s][1], 0)
        sc = ax.scatter(lon[show], lat[show], c=np.hypot(mu, mv)[show], s=26, marker="s",
                        vmin=0, vmax=0.4, cmap="viridis")
        ax.quiver(lon[show], lat[show], mu[show], mv[show], scale=4, width=0.004, color="w")
        ax.set_title(f"({'abc'[k]}) {LABELS[s]}, mean", loc="left", fontsize=10)
        ax = axs[1, k]
        if s == "hfr":
            sc2 = ax.scatter(lon[show], lat[show], c=n_ok[show] / len(tot["times"]), s=26, marker="s",
                             vmin=0, vmax=1, cmap="Greys")
            ax.set_title(f"({'def'[k]}) fraction of hours with a good total", loc="left", fontsize=10)
            fig.colorbar(sc2, ax=ax, shrink=0.7, label="Fraction")
        else:
            rho = np.full(lon.size, np.nan)
            for j in np.flatnonzero(show):
                st = vector_stats(fields["hfr"][0][:, j], fields["hfr"][1][:, j], fields[s][0][:, j], fields[s][1][:, j])
                rho[j] = st.get("rho", np.nan)
            sc3 = ax.scatter(lon[show], lat[show], c=rho[show], s=26, marker="s", vmin=0, vmax=1, cmap="magma")
            ax.set_title(f"({'def'[k]}) {LABELS[s].split(',')[0]}, complex correlation", loc="left", fontsize=10)
    fig.colorbar(sc, ax=axs[0, :], shrink=0.7, label="Mean speed (m/s)")
    if len(sources) > 1:
        fig.colorbar(sc3, ax=axs[1, 1:], shrink=0.7, label="|ρ| (Kundu)")
    for ax in axs.ravel():
        coast.plot(ax=ax, color="#d9d4c7", edgecolor="#8c8678", linewidth=0.5)
        draw_tracks(ax, window)
        ax.set(xlim=(lon0, lon1), ylim=(lat0, lat1), aspect=1 / np.cos(np.radians((lat0 + lat1) / 2)))
    for ax in axs[:, 0]:
        ax.set_ylabel("Latitude (°N)")
    for ax in axs[1]:
        ax.set_xlabel("Longitude (°E)")
    fig.suptitle(f"Surface current against the CALYPSO totals, {WINDOWS[window]['title']}, "
                 f"after {SPINUP_HOURS} h of spin-up", fontsize=11)
    path = Path(str(FIGURE).format(f"{window}_field"))
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return path


def series_figure(window: str, tot: dict, fields: dict, box) -> Path:
    import matplotlib.pyplot as plt

    t = pd.to_datetime(tot["times"])
    fig, axs = plt.subplots(2, 1, figsize=(10, 5.4), sharex=True, layout="constrained")
    for s in fields:
        bu, bv = box_series(*fields[s], box)
        for ax, x in zip(axs, (bu, bv)):
            ax.plot(t, x, color=COLOURS[s], lw=1.4 if s == "hfr" else 1.1, label=LABELS[s])
    for ax, comp in zip(axs, ("Eastward", "Northward")):
        ax.axhline(0, color="0.6", lw=0.6)
        ax.set_ylabel(f"{comp} (m/s)")
        ax.grid(alpha=0.3)
    axs[0].legend(fontsize=8, ncol=3)
    axs[0].set_title(f"Mean over the radar cells within {CORRIDOR_KM:g} km of the drifter tracks of "
                     f"{TRACKS[window]} 2026, {WINDOWS[window]['title']}", loc="left", fontsize=10)
    path = Path(str(FIGURE).format(f"{window}_corridor"))
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def radial_figure(window: str, rad: dict, rfields: dict, box) -> Path:
    """Bins of the station in domain B and the radial velocity averaged over those in the track corridor."""
    import geopandas as gpd
    import matplotlib.pyplot as plt

    coast = gpd.read_file(COAST)
    t = pd.to_datetime(rad["times"])
    good = np.isfinite(rad["r"])
    fig, (ax, bx) = plt.subplots(1, 2, figsize=(13, 4.6), layout="constrained",
                                 gridspec_kw=dict(width_ratios=[1, 2.2]))
    frac = good.mean(0)
    sc = ax.scatter(rad["lon"], rad["lat"], c=frac, s=6, vmin=0, vmax=1, cmap="Greys")
    coast.plot(ax=ax, color="#d9d4c7", edgecolor="#8c8678", linewidth=0.5)
    draw_tracks(ax, window)
    ax.set(xlim=(14.30, 14.95), ylim=(35.75, 36.25), aspect=1 / np.cos(np.radians(36.0)),
           xlabel="Longitude (°E)", ylabel="Latitude (°N)")
    ax.set_title(f"(a) bins of {SITE}, fraction of good hours", loc="left", fontsize=10)
    fig.colorbar(sc, ax=ax, shrink=0.8)
    for s, f in rfields.items():
        x = np.where(good[:, box], f[:, box], np.nan)
        n = np.isfinite(x).sum(1)
        with np.errstate(invalid="ignore"):
            m = np.where(n >= 10, np.nanmean(x, 1), np.nan)
        bx.plot(t, m, color=COLOURS[s], lw=1.4 if s == "hfr" else 1.1, label=LABELS[s])
    bx.axhline(0, color="0.6", lw=0.6)
    bx.set_ylabel("Radial velocity away from the antenna (m/s)")
    bx.grid(alpha=0.3)
    bx.legend(fontsize=8, ncol=3)
    bx.set_title(f"(b) mean over the bins in the track corridor, {WINDOWS[window]['title']}", loc="left", fontsize=10)
    path = Path(str(FIGURE).format(f"{window}_radial"))
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--window", nargs="+", default=list(WINDOWS), choices=list(WINDOWS))
    ap.add_argument("--figure", action="store_true")
    args = ap.parse_args(argv)
    rows = []
    for w in args.window:
        rows += run(w, args.figure)
    df = pd.DataFrame(rows)
    if METRICS.exists():
        old = pd.read_csv(METRICS)
        df = pd.concat([old[~old.window.isin(args.window)], df], ignore_index=True)
    df.to_csv(METRICS, index=False, float_format="%.4g")
    cols = ["window", "product", "source", "region", "n", "rmse", "rho", "phase", "std_ratio", "r",
            "bias_u", "bias_v", "bias", "speed_o", "speed_m"]
    with pd.option_context("display.width", 220, "display.max_columns", 30):
        print(df[[c for c in cols if c in df]].round(3).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

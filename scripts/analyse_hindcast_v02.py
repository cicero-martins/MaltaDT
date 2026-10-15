"""Compare a hindcast on mesh v02 with CMEMS, ERA5 and the BLUE buoy.

Three comparisons are made, each over the window given.

- level: the modelled water level at the offshore stations against the CMEMS
  sea surface height at the nearest wet cell of its 4.2 km grid, less the offset
  removed at the boundary. The two should agree outside the harbours, since the
  domain is small against the scale of the tide and of the surge, and a
  departure points to the treatment of the boundary.
- forcing: ERA5 wind at 10 m and mean sea level pressure, interpolated to the
  mooring, against the wind and pressure measured on the BLUE buoy.
- buoy: in three-dimensional runs, the modelled current, temperature and
  salinity at the BLUE station at a set of depths against the buoy, with the
  same statistics for the CMEMS fields at the nearest wet cell, so that the
  model is read against its own boundary source.

Statistics are the bias, the root mean square error, the correlation and the
ratio of standard deviations, on the raw series and on the anomalies about the
mean of the window.

Usage:
    python analyse_hindcast_v02.py model/hindcast/v02_2d_0722_0724_tf0 \\
        --from 2025-07-22T12 --to 2025-07-24
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

ROOT = Path(__file__).resolve().parents[1]
CMEMS = ROOT / "data" / "raw" / "cmems_2025-07"
ERA5 = ROOT / "data" / "raw" / "era5_2025-07"
BLUE_CSV = ROOT / "data" / "processed" / "blue_buoy_10min.csv"
BLUE = (14.5388, 35.9294)
OFFSHORE = ("blue_buoy", "offshore_4km", "plateau_east", "plateau_north", "gh_mouth", "mx_mouth")
DEPTHS = (1.0, 3.0, 5.0, 10.0, 20.0)


def stats(model: pd.Series, obs: pd.Series) -> dict:
    j = pd.concat([model.rename("m"), obs.rename("o")], axis=1).dropna()
    if len(j) < 3:
        return dict(n=len(j))
    m, o = j.m, j.o
    ma, oa = m - m.mean(), o - o.mean()
    return dict(n=len(j), bias=float((m - o).mean()), rmse=float(np.sqrt(((m - o) ** 2).mean())),
                rmse_anom=float(np.sqrt(((ma - oa) ** 2).mean())), r=float(np.corrcoef(m, o)[0, 1]),
                std_ratio=float(m.std() / o.std()) if o.std() > 0 else np.nan)


def lag_minutes(model: pd.Series, obs: pd.Series, max_lag: int = 120) -> float:
    """Lag of the model behind the observation maximising the correlation, minutes."""
    j = pd.concat([model.rename("m"), obs.rename("o")], axis=1).dropna().resample("1min").mean().interpolate()
    best, arg = -2.0, 0
    for k in range(-max_lag, max_lag + 1, 2):
        r = j.m.corr(j.o.shift(k))
        if r > best:
            best, arg = r, k
    return float(arg)


def open_his(case: Path) -> xr.Dataset:
    his = next((case / "output").glob("*_his.nc"))
    ds = xr.open_dataset(his)
    names = [s.decode().strip() if isinstance(s, bytes) else str(s).strip() for s in ds.station_name.values]
    return ds.assign_coords(station=names)


def nearest_wet(da: xr.DataArray, lon: float, lat: float) -> xr.DataArray:
    """The CMEMS series at the wet cell nearest to a point."""
    first = da.isel(time=0)
    if "depth" in first.dims:
        first = first.isel(depth=0)
    wet = first.notnull()
    lo, la = np.meshgrid(da.longitude.values, da.latitude.values)
    dist = np.where(wet.values, (lo - lon) ** 2 * np.cos(np.radians(lat)) ** 2 + (la - lat) ** 2, np.inf)
    i, k = np.unravel_index(np.argmin(dist), dist.shape)
    return da.isel(latitude=i, longitude=k)


def compare_level(case: Path, his: xr.Dataset, meta: dict, t0, t1) -> dict:
    zos = xr.open_dataset(next(CMEMS.glob("cmems_zos_*.nc"))).zos
    out = {}
    for st in OFFSHORE:
        if st not in his.station.values:
            continue
        lon, lat = meta["stations"][st]
        m = his.waterlevel.sel(station=st).to_series()[t0:t1]
        c = (nearest_wet(zos, lon, lat).to_series() - meta["zos_offset"])[t0:t1]
        m15 = m.reindex(c.index, method="nearest", tolerance=pd.Timedelta("1min"))
        s = stats(m15, c)
        s["lag_min"] = lag_minutes(m, c)
        s["range_model"], s["range_cmems"] = float(m.max() - m.min()), float(c.max() - c.min())
        out[st] = s
    return out


def era5_at(key: str, lon: float, lat: float) -> pd.Series:
    files = sorted(ERA5.glob(f"era5_{key}_*.nc"))
    ds = xr.open_mfdataset(files, combine="by_coords") if len(files) > 1 else xr.open_dataset(files[0])
    if "valid_time" in ds.dims:
        ds = ds.rename(valid_time="time")
    return ds[key].interp(longitude=lon, latitude=lat).to_series()


def compare_forcing(t0, t1) -> dict:
    blue = pd.read_csv(BLUE_CSV, parse_dates=["timestamp"], index_col="timestamp")[t0:t1]
    u, v, p = (era5_at(k, *BLUE)[t0:t1] for k in ("u10", "v10", "msl"))
    ws = np.hypot(u, v)
    # The buoy reports the direction the wind blows from, in degrees from north
    wd = np.radians(blue.wind_direction)
    bu, bv = -blue.wind_speed * np.sin(wd), -blue.wind_speed * np.cos(wd)
    hourly = lambda s: s.resample("1h").mean()
    return {"wind_speed": stats(ws, hourly(blue.wind_speed)),
            "wind_u": stats(u, hourly(bu)), "wind_v": stats(v, hourly(bv)),
            "pressure_hpa": stats(p / 100.0, hourly(blue.air_pressure))}


def compare_buoy(his: xr.Dataset, meta: dict, t0, t1) -> dict:
    """Model and CMEMS against the buoy at a set of depths below the surface."""
    blue = pd.read_csv(BLUE_CSV, parse_dates=["timestamp"], index_col="timestamp")[t0:t1]
    obs = {"u": blue.current_u / 100.0, "v": blue.current_v / 100.0,
           "temperature": blue.sea_temperature, "salinity": blue.salinity}
    st = his.sel(station="blue_buoy")
    wl = st["waterlevel"].to_series()
    index = wl.index
    if "zcoordinate_c" in st:
        zc = st["zcoordinate_c"].values
    else:
        # Uniform sigma layers counted from the bed, the history file of FM
        # 2026.01 carrying no layer levels
        kmx = st.sizes["laydim"]
        frac = (np.arange(kmx) + 0.5) / kmx
        bed = float(st["bedlevel"])
        zc = bed + (wl.values[:, None] - bed) * frac[None, :]
    var = {"u": "x_velocity", "v": "y_velocity", "temperature": "temperature", "salinity": "salinity"}
    out = {"model": {}, "model_daily": {}, "cmems": {}}
    for depth in DEPTHS:
        target = wl.values[:, None] - depth
        k = np.abs(zc - target).argmin(axis=1)
        row, daily = {}, {}
        for key, name in var.items():
            series = pd.Series(st[name].values[np.arange(len(k)), k], index=index)[t0:t1]
            row[key] = stats(series, obs[key].resample("10min").mean())
            # daily means, on the footing of the daily CMEMS fields
            daily[key] = stats(series.resample("1D").mean(), obs[key].resample("1D").mean())
        out["model"][f"{depth:g} m"] = row
        out["model_daily"][f"{depth:g} m"] = daily
    lon, lat = BLUE
    files = {"u": ("uo", "uo"), "v": ("vo", "vo"), "temperature": ("thetao", "thetao"),
             "salinity": ("so", "so")}
    for depth in DEPTHS:
        row = {}
        for key, (f, v) in files.items():
            da = xr.open_dataset(next(CMEMS.glob(f"cmems_{f}_*.nc")))[v]
            c = nearest_wet(da, lon, lat).sel(depth=depth, method="nearest").to_series()
            # daily means centred on midday against daily means of the buoy
            row[key] = stats(c[t0:t1], obs[key].resample("1D").mean())
        out["cmems"][f"{depth:g} m"] = row
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("case", type=Path)
    ap.add_argument("--from", dest="t0", required=True)
    ap.add_argument("--to", dest="t1", required=True)
    args = ap.parse_args(argv)
    case = args.case if args.case.is_absolute() else ROOT / args.case
    meta = json.loads((case / "case.json").read_text())
    his = open_his(case)
    t0, t1 = pd.Timestamp(args.t0), pd.Timestamp(args.t1)
    res = {"case": meta["case"], "window": [str(t0), str(t1)],
           "level": compare_level(case, his, meta, t0, t1), "forcing": compare_forcing(t0, t1)}
    if meta["kmx"] > 0:
        res["buoy"] = compare_buoy(his, meta, t0, t1)
    (case / "comparison.json").write_text(json.dumps(res, indent=2))
    print(f"level against CMEMS, {t0} to {t1}")
    for st, s in res["level"].items():
        print(f"  {st:14s} r {s['r']:.3f}  bias {s['bias'] * 100:+6.2f} cm  rmse(anom) "
              f"{s['rmse_anom'] * 100:5.2f} cm  std ratio {s['std_ratio']:.3f}  lag {s['lag_min']:+.0f} min  "
              f"range {s['range_model'] * 100:.1f} / {s['range_cmems'] * 100:.1f} cm")
    print("ERA5 against BLUE")
    for k, s in res["forcing"].items():
        print(f"  {k:13s} n {s['n']}  bias {s['bias']:+.2f}  rmse {s['rmse']:.2f}  r {s['r']:.3f}  "
              f"std ratio {s['std_ratio']:.2f}")
    if "buoy" in res:
        for src, label in (("model", "model, 10 min"), ("model_daily", "model, daily"),
                           ("cmems", "CMEMS, daily")):
            print(f"BLUE against {label}")
            for depth, row in res["buoy"][src].items():
                cells = []
                for key, s in row.items():
                    if s.get("n", 0) < 3:
                        cells.append(f"{key} n<3")
                        continue
                    cells.append(f"{key} bias {s['bias']:+.2f} rmse {s['rmse']:.2f} r {s['r']:+.2f}")
                print(f"  {depth:>5s}  " + " | ".join(cells))
    return 0


if __name__ == "__main__":
    sys.exit(main())

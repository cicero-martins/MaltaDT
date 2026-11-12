"""Extract vertical profiles from the partitioned map output of a 3D run.

For each point of a table of times and positions the face whose centre is
nearest is found among the faces owned by each partition, and the profile of
the current components, salinity and temperature over the layers is read at
the map time nearest to the time of the point, together with the water level,
the water depth and the wind at that face. The layer interfaces are kept as
sigma, so that the depth of a layer follows from the level and the depth.

The script needs xarray and netCDF4 alone, so that it runs on simit-server,
where the map files stay, and only the profiles are transferred.

Usage:
    python extract_profiles_map.py <case_dir> <points.csv> [--out <file>]

The table of points holds the columns time, lon and lat.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

PROFILES = ("mesh2d_ucx", "mesh2d_ucy", "mesh2d_sa1", "mesh2d_tem1")
SCALARS = ("mesh2d_s1", "mesh2d_waterdepth", "mesh2d_windx", "mesh2d_windy")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("case", type=Path)
    ap.add_argument("points", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    files = sorted((args.case / "output").glob("*_0[0-9][0-9][0-9]_map.nc"))
    if not files:
        print(f"no partitioned map files in {args.case / 'output'}", file=sys.stderr)
        return 1
    pts = pd.read_csv(args.points, parse_dates=["time"])
    n = len(pts)
    scale = np.cos(np.radians(pts.lat.mean()))

    # nearest owned face of each partition, the closest over the partitions being kept
    best = np.full(n, np.inf)
    part = np.zeros(n, int)
    face = np.zeros(n, int)
    for rank, f in enumerate(files):
        with xr.open_dataset(f) as ds:
            own = np.where(ds["mesh2d_flowelem_domain"].values.astype(int) == rank)[0]
            x, y = ds["mesh2d_face_x"].values[own], ds["mesh2d_face_y"].values[own]
        d2 = ((pts.lon.values[:, None] - x[None]) * scale) ** 2 + (pts.lat.values[:, None] - y[None]) ** 2
        j = d2.argmin(1)
        d = d2[np.arange(n), j]
        closer = d < best
        best[closer], part[closer], face[closer] = d[closer], rank, own[j[closer]]

    out = {}
    for rank, f in enumerate(files):
        idx = np.where(part == rank)[0]
        if not idx.size:
            continue
        with xr.open_dataset(f) as ds:
            times = pd.to_datetime(ds.time.values)
            ti = np.abs(times.values[None] - pts.time.values[idx, None]).argmin(1)
            faces, inv = np.unique(face[idx], return_inverse=True)
            sub = ds.isel(mesh2d_nFaces=faces)
            for v in PROFILES + SCALARS:
                if v not in sub:
                    continue
                a = sub[v].values                       # time, face(, layer)
                if v not in out:
                    out[v] = np.full((n,) + a.shape[2:], np.nan, "float32")
                out[v][idx] = a[ti, inv]
            for v, key in (("mesh2d_face_x", "face_x"), ("mesh2d_face_y", "face_y"), ("mesh2d_flowelem_bl", "bl")):
                out.setdefault(key, np.full(n, np.nan))[idx] = sub[v].values[inv]
            out.setdefault("map_time", np.full(n, np.datetime64("NaT"), "datetime64[ns]"))[idx] = times.values[ti]
            sigma = ds["mesh2d_layer_sigma"].values
            interfaces = ds["mesh2d_interface_sigma"].values
        print(f"  {f.name}: {idx.size} points on {faces.size} faces", flush=True)

    res = xr.Dataset(
        {k: (("point", "layer") if v.ndim == 2 else ("point",), v) for k, v in out.items()},
        coords=dict(time=("point", pts.time.values), lon=("point", pts.lon.values), lat=("point", pts.lat.values),
                    layer_sigma=("layer", sigma), interface_sigma=("interface", interfaces)))
    for c in pts.columns:
        if c not in ("time", "lon", "lat"):
            res[c] = ("point", pts[c].values)
    res.attrs["source"] = f"partitioned map of {args.case.name}, extract_profiles_map.py"
    path = args.out or args.case / "output" / f"{args.case.name}_profiles.nc"
    res.to_netcdf(path)
    print(f"{n} profiles of {sigma.size} layers written to {path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

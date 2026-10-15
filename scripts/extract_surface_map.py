"""Merge the partitioned map output of a 3D run into one file of surface fields.

Each partition contributes the faces it owns, mesh2d_flowelem_domain equal to
its rank, so that the ghost cells along the partition edges are not counted
twice, ordered by the global face number. The fields kept are the water level
and depth, and in the top layer the current components, temperature and
salinity, which is what the interactive map draws. In sigma and z-sigma runs
alike the top layer is the last index of the layer dimension.

The script needs xarray and netCDF4 alone, so that it runs on simit-server,
where the map files stay, and only the merged file is transferred.

Usage:
    python extract_surface_map.py <case_dir> [--out <file>]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import xarray as xr

FACE_VARS = ("mesh2d_face_x", "mesh2d_face_y", "mesh2d_face_x_bnd", "mesh2d_face_y_bnd")
FIELDS_2D = ("mesh2d_s1", "mesh2d_waterdepth")
FIELDS_TOP = ("mesh2d_ucx", "mesh2d_ucy", "mesh2d_tem1", "mesh2d_sa1")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("case", type=Path)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args(argv)
    files = sorted((args.case / "output").glob("*_0[0-9][0-9][0-9]_map.nc"))
    if not files:
        print(f"no partitioned map files in {args.case / 'output'}", file=sys.stderr)
        return 1
    parts = []
    for rank, f in enumerate(files):
        ds = xr.open_dataset(f)
        own = np.where(ds["mesh2d_flowelem_domain"].values.astype(int) == rank)[0]
        sel = ds.isel(mesh2d_nFaces=own)
        out = {v: sel[v].load() for v in FACE_VARS + FIELDS_2D}
        for v in FIELDS_TOP:
            if v in sel:
                out[v] = sel[v].isel(mesh2d_nLayers=-1).load()
        out["globalnr"] = sel["mesh2d_flowelem_globalnr"].load()
        parts.append(xr.Dataset(out).drop_vars([c for c in ("mesh2d_face_x", "mesh2d_face_y")
                                                 if c in xr.Dataset(out).coords], errors="ignore"))
        print(f"  {f.name}: {own.size} own faces of {ds.sizes['mesh2d_nFaces']}", flush=True)
        ds.close()
    merged = xr.concat(parts, dim="mesh2d_nFaces")
    order = np.argsort(merged["globalnr"].values)
    merged = merged.isel(mesh2d_nFaces=order)
    for v in FIELDS_2D + FIELDS_TOP:
        if v in merged:
            merged[v] = merged[v].astype("float32")
    merged.attrs["source"] = f"top layer of the partitioned map of {args.case.name}, extract_surface_map.py"
    out = args.out or args.case / "output" / f"{args.case.name}_surface_map.nc"
    enc = {v: {"zlib": True, "complevel": 4} for v in merged.data_vars}
    merged.to_netcdf(out, encoding=enc)
    print(f"{merged.sizes['mesh2d_nFaces']} faces, {merged.sizes['time']} times, written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

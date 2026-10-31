"""Extract the 3D currents of a hindcast case around the Valletta harbours for OpenDrift.

The partitioned map output is read with the reader of
StagnoneDT/scripts/extract_velocity_sections.py and interpolated onto a regular
grid in longitude and latitude, as in extract_harbour_sections.py, and then
from the stretched sigma layers onto fixed depths below the free surface. The
file follows the CF names read by the GenericReader of OpenDrift, with the
three velocity components, the depth of the bed and a land mask.

The box holds both harbours and some 3 km of the approach, so that particles
leaving a harbour can return with the next reversal of the exchange before
they leave the box. A particle that reaches the edge of the box is counted as
renewed.

Each depth below the surface maps to sigma = 1 - d/H in a column of depth H,
the same in every column, so the vertical interpolation is linear in sigma
between the layer centres. Above the top centre the top layer applies, and
below the bed the deepest layer, which OpenDrift does not reach since the bed
is declared.

The script needs xarray and scipy alone, so that it runs on simit-server next
to the partitioned map output, with the StagnoneDT repository beside this one.

Usage:
    python extract_harbour_currents_3d.py model/hindcast/<case>
        [--start 2025-07-25T00:00] [--stop 2025-08-01T00:00] [--step 0.0004]
"""

from __future__ import annotations

import argparse
import sys
import types
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT.parent / "StagnoneDT" / "scripts"))
import extract_velocity_sections as ev  # noqa: E402
from extract_harbour_sections import layer_sigma, partition_glob  # noqa: E402
from regrid_wetwise_source import FastGridInterp, wet_mask  # noqa: E402

BOX_LON = (14.470, 14.560)
BOX_LAT = (35.865, 35.930)
DEPTHS = np.array([0.5, 1, 2, 3, 4, 6, 8, 10, 13, 16, 20, 25, 30, 40, 50, 60, 80, 100],
                  dtype=np.float32)


def to_depths(field: np.ndarray, H: np.ndarray, sigma: np.ndarray) -> np.ndarray:
    """(point, layer) on sigma to (depth, point) on DEPTHS below the surface."""
    st = 1.0 - DEPTHS[:, None] / np.maximum(H[None, :], 1e-3)       # (depth, point)
    st = np.clip(st, sigma[0], sigma[-1])
    k = np.clip(np.searchsorted(sigma, st) - 1, 0, sigma.size - 2)
    t = (st - sigma[k]) / (sigma[k + 1] - sigma[k])
    p = np.arange(field.shape[0])[None, :]
    return (1 - t) * field[p, k] + t * field[p, k + 1]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("case", type=Path)
    ap.add_argument("--start", default="2025-07-25T00:00")
    ap.add_argument("--stop", default="2025-08-01T00:00")
    ap.add_argument("--step", type=float, default=0.0004, help="grid step, degrees, ~40 m")
    ap.add_argument("--out", type=Path, help="default <case>/output/currents_3d.nc")
    args = ap.parse_args(argv)
    out = args.out or args.case / "output" / "currents_3d.nc"

    ev.BOX_LON, ev.BOX_LAT = BOX_LON, BOX_LAT
    ev._glob = types.SimpleNamespace(glob=partition_glob)
    times, f = ev.load_box(args.case)
    it = np.flatnonzero((times >= np.datetime64(pd.Timestamp(args.start)))
                        & (times <= np.datetime64(pd.Timestamp(args.stop))))
    sigma = layer_sigma(args.case)

    glon = np.arange(BOX_LON[0], BOX_LON[1] + args.step / 2, args.step)
    glat = np.arange(BOX_LAT[0], BOX_LAT[1] + args.step / 2, args.step)
    L, A = np.meshgrid(glon, glat)
    mask = wet_mask(f["xb"], f["yb"], glon, glat).ravel()
    interp = FastGridInterp(np.c_[f["cx"], f["cy"]], np.c_[L.ravel(), A.ravel()][mask])
    npt = int(mask.sum())
    print(f"grid {glon.size} x {glat.size}, {npt} wet points, {it.size} times, {sigma.size} layers")

    bed = interp(f["bl"][0])
    shp = (it.size, DEPTHS.size, glat.size, glon.size)
    fields = {k: np.full(shp, np.nan, np.float32) for k in ("ucx", "ucy", "ucz")}
    for n, i in enumerate(it):
        H = interp(f["s1"][i]) - bed
        for key in fields:
            lay = np.stack([interp(f[key][i, :, k]) for k in range(sigma.size)], axis=-1)
            g = np.full((DEPTHS.size, mask.size), np.nan, np.float32)
            g[:, mask] = to_depths(lay, H, sigma)
            fields[key][n] = g.reshape(DEPTHS.size, glat.size, glon.size)
        if n % 48 == 0:
            print(f"  {str(times[i])[:16]}")

    floor = np.full(mask.size, np.nan, np.float32)
    floor[mask] = -bed
    # Every point off the water takes the values of the nearest wet point. Zero
    # current and depth on land would make the bilinear interpolation of
    # OpenDrift taper both toward the shore across one grid cell, a band in
    # which particles come to rest on a bed near the surface.
    valid = (np.isfinite(floor) & np.isfinite(fields["ucx"][0, 0].ravel())).reshape(L.shape)
    _, (iy, ix) = distance_transform_edt(~valid, return_indices=True)
    floor = floor.reshape(L.shape)[iy, ix].ravel()
    for key in fields:
        fields[key] = fields[key][:, :, iy, ix]
    names = {"ucx": ("x_sea_water_velocity", "eastward sea water velocity"),
             "ucy": ("y_sea_water_velocity", "northward sea water velocity"),
             "ucz": ("upward_sea_water_velocity", "upward sea water velocity")}
    ds = xr.Dataset(
        {name: (("time", "depth", "lat", "lon"), np.nan_to_num(fields[k], nan=0.0),
                {"standard_name": name, "long_name": ln, "units": "m s-1"})
         for k, (name, ln) in names.items()},
        coords={"time": times[it],
                "depth": ("depth", DEPTHS, {"standard_name": "depth", "positive": "down",
                                            "units": "m"}),
                "lat": ("lat", glat, {"standard_name": "latitude", "units": "degrees_north"}),
                "lon": ("lon", glon, {"standard_name": "longitude", "units": "degrees_east"})})
    ds["sea_floor_depth_below_sea_level"] = (
        ("lat", "lon"), np.nan_to_num(floor, nan=0.0).reshape(L.shape),
        {"standard_name": "sea_floor_depth_below_sea_level", "units": "m"})
    ds["land_binary_mask"] = (("lat", "lon"), (~mask).reshape(L.shape).astype(np.int8),
                              {"standard_name": "land_binary_mask"})
    ds.attrs.update(source=args.case.name, layer_distribution="stretched sigma",
                    vertical="linear in sigma between layer centres")
    ds.to_netcdf(out, encoding={v: {"zlib": True, "complevel": 4} for v in ds.data_vars})
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

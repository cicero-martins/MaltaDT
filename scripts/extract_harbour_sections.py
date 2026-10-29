"""Extract vertical sections of the 3D velocity field in the Valletta harbours.

The Stagnone portal carries a perspective view of vertical sections, written by
StagnoneDT/scripts/extract_velocity_sections.py and drawn by
build_wetwise_sections_view.py. This script writes the same cache file,
sections.nc, for a hindcast case on mesh v03, reusing the reading of the
partitioned output, the sampling of the polylines and the interpolation of
that script without modification of its code. What differs at Valletta is
passed in or replaced:

1. four sections, along the main axis and across the central basin of the
   Grand Harbour and of Marsamxett;
2. the layer elevations, taken from the sigma of the layer centres written by
   FM, since the layers are stretched rather than uniform;
3. the harbour faces drawn as the surface plane, which on v03 are quadrilaterals
   and triangles of the quadtree and are split into triangles here.

The script needs xarray, scipy and matplotlib alone, so that it runs on
simit-server next to the partitioned map output, with the StagnoneDT repository
beside this one.

Usage:
    python extract_harbour_sections.py model/hindcast/<case> [--out <dir>]
"""

from __future__ import annotations

import argparse
import glob as _glob
import sys
import types
from pathlib import Path

import numpy as np
import xarray as xr
from matplotlib.path import Path as MplPath

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / "StagnoneDT" / "scripts"))
import extract_velocity_sections as ev  # noqa: E402
from regrid_wetwise_source import FastGridInterp, wet_mask  # noqa: E402

# The axes follow the deep channel from outside the mouth to the head, Marsa
# for the Grand Harbour and Msida Creek for Marsamxett, with vertices placed so
# that every sample but one or two falls in a wet face of v03. The cross
# sections cut the central basin of each harbour normal to its axis, the Grand
# Harbour from Valletta toward Kalkara, Marsamxett from the Sliema shore to
# Valletta east of Manoel Island.
SECTIONS = {
    "gh_axis": [(14.5290, 35.9025), (14.5235, 35.9005), (14.5200, 35.8975),
                (14.5170, 35.8950), (14.5130, 35.8925), (14.5095, 35.8894),
                (14.5065, 35.8871), (14.5040, 35.8858), (14.5022, 35.8845),
                (14.5016, 35.8828), (14.5019, 35.8812), (14.5008, 35.8802),
                (14.4990, 35.8800)],
    "gh_cross": [(14.5188, 35.8983), (14.5228, 35.8945)],
    "mx_axis": [(14.5200, 35.9070), (14.5150, 35.9045), (14.5110, 35.9035),
                (14.5065, 35.9015), (14.5030, 35.8993), (14.5012, 35.8978),
                (14.5000, 35.8970), (14.4975, 35.8970), (14.4950, 35.8967),
                (14.4925, 35.8964), (14.4915, 35.8962)],
    "mx_cross": [(14.5090, 35.9052), (14.5098, 35.9000)],
}
SECTION_DS = 20.0                 # m between section samples

BOX_LON = (14.485, 14.532)        # faces read for the interpolation
BOX_LAT = (35.876, 35.910)
SURF_STEP = 0.0004                # ~40 m, particles and arrows on the surface

# Faces drawn as the surface plane. The polygon closes the box a few hundred
# metres outside both mouths, so that the approach is shown and the open sea,
# whose currents exceed those of the harbours, does not enter the scales.
HARBOUR_CLIP = [(14.485, 35.876), (14.485, 35.910), (14.5125, 35.910),
                (14.5200, 35.9080), (14.5280, 35.9040), (14.5310, 35.9000),
                (14.5310, 35.876)]


def partition_glob(pattern: str) -> list[str]:
    """The Stagnone reader looks in DFM_OUTPUT_*, the cases here write to output.

    Its pattern also matches the merged surface map beside the partitions,
    which the case name makes end in _0..._map.nc, so the partition number is
    spelled out.
    """
    pattern = pattern.replace("DFM_OUTPUT_*", "output").replace("*_0*_map.nc", "*_0[0-9][0-9][0-9]_map.nc")
    return _glob.glob(pattern)


def layer_sigma(case: Path) -> np.ndarray:
    """Height of each layer centre above the bed as a fraction of the column."""
    f = sorted((case / "output").glob("*_0000_map.nc"))[0]
    with xr.open_dataset(f) as ds:
        return 1.0 + ds["mesh2d_layer_sigma"].values      # -1 at the bed in FM


def harbour_triangles(xb: np.ndarray, yb: np.ndarray, cx, cy):
    """Faces inside HARBOUR_CLIP, split into triangles fanned from the first node."""
    inside = MplPath(HARBOUR_CLIP).contains_points(np.c_[cx, cy])
    face, tx, ty = [], [], []
    for k in np.flatnonzero(inside):
        good = np.isfinite(xb[k]) & np.isfinite(yb[k])
        px, py = xb[k][good], yb[k][good]
        for j in range(1, len(px) - 1):
            face.append(k)
            tx.append([px[0], px[j], px[j + 1]])
            ty.append([py[0], py[j], py[j + 1]])
    return inside, np.array(face), np.array(tx), np.array(ty)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("case", type=Path)
    ap.add_argument("--out", type=Path, help="default <case>/output/sections")
    args = ap.parse_args(argv)
    out_dir = args.out or args.case / "output" / "sections"
    out_dir.mkdir(parents=True, exist_ok=True)

    ev.BOX_LON, ev.BOX_LAT = BOX_LON, BOX_LAT
    ev._glob = types.SimpleNamespace(glob=partition_glob)
    times, f = ev.load_box(args.case)
    sigma = layer_sigma(args.case)
    kmx = sigma.size
    lat0 = float(np.mean(BOX_LAT))
    pts_faces = np.c_[f["cx"], f["cy"]]

    data_vars, coords = {}, {"time": times, "layer": np.arange(kmx),
                             "sigma": ("layer", sigma)}
    for name, verts in SECTIONS.items():
        s, lon, lat, tx, ty = ev.sample_polyline(verts, SECTION_DS, lat0)
        wet = ev.point_in_faces(f["xb"], f["yb"], lon, lat)
        interp = FastGridInterp(pts_faces, np.c_[lon, lat])
        s1, bl, u, v, w = (ev.interp_all(interp, f[k]) for k in ("s1", "bl", "ucx", "ucy", "ucz"))
        for a in (s1, bl, u, v, w):
            a[:, ~wet] = np.nan
        nx, ny = -ty, tx                  # normal positive to the left of travel
        un = u * nx[None, :, None] + v * ny[None, :, None]
        ut = u * tx[None, :, None] + v * ty[None, :, None]
        z = bl[..., None] + sigma[None, None, :] * (s1 - bl)[..., None]
        d = f"{name}_pt"
        coords.update({f"{name}_dist": (d, s), f"{name}_lon": (d, lon), f"{name}_lat": (d, lat)})
        data_vars[f"{name}_s1"] = (("time", d), s1)
        data_vars[f"{name}_bl"] = (("time", d), bl)
        for key, arr in (("z", z), ("un", un), ("ut", ut), ("w", w)):
            data_vars[f"{name}_{key}"] = (("time", d, "layer"), arr.astype(np.float32))
        print(f"[{name}] {s.size} samples over {s[-1]:.0f} m, {int(wet.sum())} wet")

    # the variable names of the lagoon are kept, since the page reads them
    inside, face, txb, tyb = harbour_triangles(f["xb"], f["yb"], f["cx"], f["cy"])
    data_vars["lag_xb"] = (("lface", "corner"), txb)
    data_vars["lag_yb"] = (("lface", "corner"), tyb)
    data_vars["lag_s1"] = (("time", "lface"), f["s1"][:, face])
    for v in ("ucx", "ucy"):
        data_vars[f"lag_{v}"] = (("time", "lface"), f[v][:, face, -1])
    print(f"[harbours] {int(inside.sum())} faces, {face.size} triangles")

    glon = np.arange(BOX_LON[0], BOX_LON[1] + SURF_STEP / 2, SURF_STEP)
    glat = np.arange(BOX_LAT[0], BOX_LAT[1] + SURF_STEP / 2, SURF_STEP)
    L, A = np.meshgrid(glon, glat)
    mask = wet_mask(f["xb"][inside], f["yb"][inside], glon, glat)
    interp = FastGridInterp(pts_faces, np.c_[L.ravel(), A.ravel()])
    shp = (len(times),) + L.shape
    for key, arr in (("ucx", f["ucx"][:, :, -1]), ("ucy", f["ucy"][:, :, -1]), ("s1", f["s1"])):
        g = ev.interp_all(interp, arr).reshape(shp)
        g[:, ~mask] = np.nan
        data_vars[f"surf_{key}"] = (("time", "slat", "slon"), g)
    coords.update(slon=glon, slat=glat)

    ds = xr.Dataset(data_vars, coords=coords)
    ds.attrs.update(source=args.case.name, kmx=kmx, layer_distribution="stretched sigma",
                    section_ds_m=SECTION_DS, normal_convention="positive to the left of travel")
    for name, verts in SECTIONS.items():
        ds.attrs[f"{name}_vertices"] = str(verts)
    path = out_dir / "sections.nc"
    ds.to_netcdf(path, encoding={v: {"zlib": True, "complevel": 4} for v in ds.data_vars})
    print(f"wrote {path} ({path.stat().st_size / 1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

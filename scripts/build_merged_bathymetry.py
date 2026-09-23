"""Merge the LiDAR and sonar components of CDI 4036_MEPA into a single field.

The two grids supplied by the host group are complementary rather than
redundant. The sonar survey covers navigable and deeper water; the LiDAR
survey penetrates shallow water of sufficient clarity and additionally
records the land surface. Over the Valletta harbours each alone leaves
substantial gaps, whereas together they cover 86 per cent of the Grand
Harbour window and 75 per cent of the Marsamxett window.

Sonar is given precedence where both are present, since it constitutes a
direct measurement of the seabed. LiDAR fills the remainder, supplying both
the shallow margins and the terrestrial surface required for shoreline and
quay representation.

Two properties of the source data govern the implementation.

The coordinate reference system is ED50 / UTM Zone 33N (EPSG:23033), but
the `prj.adf` does not encode the datum. GDAL reports an unnamed system on
the International 1924 ellipsoid with no EPSG code attached, and the
projection parameters are indistinguishable from WGS84 / UTM 33N
(EPSG:32633). Substituting one for the other displaces the field by 197 m
at the Grand Harbour, approximately 20 cells, without raising an error. The
CRS is therefore assigned explicitly rather than inherited from the file.

Both grids are nearest-neighbour resamples of 2 m mosaics, so isolated
extreme values present in the source survive into the 10 m product. A
despiking pass is available but is not applied by default, and the reason is
recorded here because the default is counter-intuitive. Applied globally at a
tolerance of 5 m over a 5 by 5 median, the pass flags 70,989 cells whose
median local gradient is 49.5 per cent, against 7.1 per cent for the cells it
leaves untouched, and among them 7.2 per cent of all emerged cells. It is
therefore removing the coastal cliffs and the Valletta bastions rather than
resampling artefacts. Despiking belongs at mesh construction, restricted to
the model domain and governed by a slope-aware criterion, not to the archival
product.

Usage:
    python build_merged_bathymetry.py --to-wgs84
    python build_merged_bathymetry.py --despike 5.0   # see the caution above
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.warp import Resampling, reproject

# The grids are ED50 / UTM 33N. The files do not say so. See module docstring.
SOURCE_EPSG = 23033

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "mepa_4036"
OUT = ROOT / "data" / "processed"


def _read(path: Path):
    """Open a component grid and return its array, transform and profile.

    The CRS reported by the file is discarded and replaced, deliberately.
    """
    with rasterio.open(path) as src:
        z = src.read(1).astype("float32")
        if src.nodata is not None:
            z[z == src.nodata] = np.nan
        profile = src.profile.copy()
        transform = src.transform
        if abs(src.res[0] - src.res[1]) > 1e-6:
            raise ValueError(f"{path.name}: non-square cells {src.res}")
    profile.update(crs=CRS.from_epsg(SOURCE_EPSG))
    return z, transform, profile


def _union_grid(grids):
    """Define the grid spanning every input, at the common cell size."""
    res = {round(abs(t.a), 6) for _, t, _ in grids}
    if len(res) != 1:
        raise ValueError(f"components differ in cell size: {res}")
    cell = res.pop()

    lefts, rights, tops, bottoms = [], [], [], []
    for z, t, _ in grids:
        h, w = z.shape
        lefts.append(t.c)
        tops.append(t.f)
        rights.append(t.c + w * cell)
        bottoms.append(t.f - h * cell)

    left, top = min(lefts), max(tops)
    right, bottom = max(rights), min(bottoms)
    width = int(round((right - left) / cell))
    height = int(round((top - bottom) / cell))
    transform = rasterio.Affine(cell, 0.0, left, 0.0, -cell, top)
    return transform, width, height


def _place(z, src_transform, dst_transform, width, height):
    """Resample a component onto the union grid.

    Nearest neighbour is used because the components are already aligned to a
    common 10 m lattice, so this is a translation rather than an interpolation.
    """
    out = np.full((height, width), np.nan, dtype="float32")
    crs = CRS.from_epsg(SOURCE_EPSG)
    reproject(
        source=z,
        destination=out,
        src_transform=src_transform,
        src_crs=crs,
        dst_transform=dst_transform,
        dst_crs=crs,
        resampling=Resampling.nearest,
        src_nodata=np.nan,
        dst_nodata=np.nan,
    )
    return out


def despike(z, tolerance: float, size: int = 5):
    """Replace cells departing from the local median by more than `tolerance`.

    Isolated extremes are an artefact of nearest-neighbour resampling from the
    2 m mosaics rather than a property of the seabed.
    """
    try:
        from scipy.ndimage import median_filter
    except ImportError:
        print("  scipy unavailable, despiking skipped", file=sys.stderr)
        return z, 0

    filled = np.where(np.isnan(z), np.nanmedian(z), z)
    med = median_filter(filled, size=size)
    spikes = np.isfinite(z) & (np.abs(z - med) > tolerance)
    out = z.copy()
    out[spikes] = med[spikes]
    return out, int(spikes.sum())


def _describe(z, label: str) -> None:
    valid = np.isfinite(z)
    wet = valid & (z < 0)
    print(f"  {label}")
    print(f"    cells        {z.shape[1]} x {z.shape[0]}")
    print(f"    valid        {valid.sum():,} ({100 * valid.sum() / z.size:.1f}%)")
    print(f"    submerged    {int(wet.sum()):,}")
    if wet.any():
        d = -z[wet]
        print(f"    depth        min {d.min():.1f}  median {np.median(d):.1f}  max {d.max():.1f} m")
    emerged = valid & (z >= 0)
    if emerged.any():
        print(f"    emerged      {int(emerged.sum()):,}, max {z[emerged].max():.1f} m")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--despike", type=float, metavar="METRES",
                    help="replace cells departing from the local median by more "
                         "than this tolerance. Not recommended globally, since "
                         "at 5 m the criterion flags genuine cliffs and bastions "
                         "rather than artefacts. See the module docstring")
    ap.add_argument("--to-wgs84", action="store_true",
                    help="additionally write a geographic version, reprojected "
                         "with a proper datum transformation")
    ap.add_argument("--out", type=Path, default=OUT / "mepa_4036_merged_10m.tif")
    args = ap.parse_args(argv)

    components = [("son_sbed", "sonar"), ("lid_sbed", "lidar")]
    grids = []
    print("Components")
    for name, label in components:
        path = RAW / name
        if not path.exists():
            print(f"  {name} not found under {RAW}", file=sys.stderr)
            return 1
        z, transform, profile = _read(path)
        grids.append((z, transform, profile))
        _describe(z, f"{name} ({label})")

    transform, width, height = _union_grid(grids)
    print(f"\nUnion grid: {width} x {height} at {abs(transform.a):.0f} m, EPSG:{SOURCE_EPSG}")

    # Sonar first, then LiDAR into whatever remains unfilled.
    placed = [_place(z, t, transform, width, height) for z, t, _ in grids]
    merged = placed[0].copy()
    gap = ~np.isfinite(merged)
    merged[gap] = placed[1][gap]
    filled_by_lidar = int((gap & np.isfinite(placed[1])).sum())

    print(f"\nMerge: sonar takes precedence, LiDAR fills {filled_by_lidar:,} cells")
    _describe(merged, "merged")

    if args.despike:
        merged, n = despike(merged, args.despike)
        print(f"\nDespiking at {args.despike} m: {n:,} cells replaced")
        print("    caution: a global tolerance flags genuine steep terrain. "
              "See the module docstring")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    profile = {
        "driver": "GTiff", "dtype": "float32", "count": 1,
        "width": width, "height": height, "transform": transform,
        "crs": CRS.from_epsg(SOURCE_EPSG), "nodata": np.nan,
        "compress": "deflate", "predictor": 3, "tiled": True,
    }
    with rasterio.open(args.out, "w", **profile) as dst:
        dst.write(merged, 1)
        dst.update_tags(
            source="CDI 4036_MEPA, EDMO 708, Oceanography Malta Research Group",
            components="son_sbed (sonar, precedence), lid_sbed (LiDAR seabed and topography)",
            native_resolution="2 m, supplied as nearest-neighbour resample to 10 m",
            crs_note="ED50 / UTM 33N assigned explicitly; source prj.adf omits the datum",
            vertical_datum="unknown, to be confirmed with the data provider",
        )
    print(f"\nWritten {args.out}")

    if args.to_wgs84:
        from rasterio.warp import calculate_default_transform
        dst_crs = CRS.from_epsg(4326)
        t, w, h = calculate_default_transform(
            CRS.from_epsg(SOURCE_EPSG), dst_crs, width, height,
            *rasterio.transform.array_bounds(height, width, transform))
        out_ll = np.full((h, w), np.nan, dtype="float32")
        reproject(source=merged, destination=out_ll,
                  src_transform=transform, src_crs=CRS.from_epsg(SOURCE_EPSG),
                  dst_transform=t, dst_crs=dst_crs,
                  resampling=Resampling.bilinear,
                  src_nodata=np.nan, dst_nodata=np.nan)
        path_ll = args.out.with_name(args.out.stem + "_wgs84.tif")
        prof_ll = dict(profile, width=w, height=h, transform=t, crs=dst_crs)
        with rasterio.open(path_ll, "w", **prof_ll) as dst:
            dst.write(out_ll, 1)
        print(f"Written {path_ll}")

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Remove returns from pontoons and moored vessels in the harbour bathymetry.

Inside the Grand Harbour and Marsamxett the LiDAR component of 4036_MEPA
records, along the marina pontoons, the deck of the pontoon or the hull of a
vessel instead of the seabed. These appear as rows of values near or above
zero, aligned with the piers, within water several metres deep. Within the
harbour box a water cell of the merged 10 m field is flagged when

- it carries no value,
- its level is at or above ABOVE_LIMIT, at any distance from the coastline,
  since a bed above mean sea level inside the water polygon is the deck of a
  vessel or pontoon, as at the shipyard at the head of Marsa, or a quay,
- its level is at or above SHALLOW_LIMIT and it lies more than COAST_BUFFER_M
  from the coastline, so that the natural shallow fringe along the shore is
  kept, or
- it stands more than SPIKE_LIMIT above the median of the valid water cells in
  a window of SPIKE_WINDOW cells and lies more than COAST_BUFFER_M from the
  coastline,

and the flagged set is dilated by one cell, since the edge of a deck or hull
yields mixed returns. Flagged cells are filled by inverse-distance
interpolation from the remaining water cells, land cells being excluded as
sources. The three limits are working values, to be checked against the
pontoons mapped in imagery.

A second field is written for sampling the mesh, in which land cells take the
value of the nearest water cell within LAND_FILL_M of them. A node on the
coastline then samples the bed beside a quay wall rather than the level of the
quay, and the bilinear sample of a node near the shore no longer meets a gap.
Cells farther from water keep no value, so that outside the MEPA coverage the
mesh still falls back to EMODnet.

Usage:
    python clean_harbour_bathymetry.py [--figure]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "processed" / "mepa_4036_merged_10m_wgs84.tif"
COAST = ROOT / "data" / "processed" / "malta_coastline_wgs84_open.gpkg"   # edit_coastline_openings.py
OUT_CLEAN = ROOT / "data" / "processed" / "mepa_4036_merged_10m_wgs84_harbour_clean.tif"
OUT_MESH = ROOT / "data" / "processed" / "mepa_4036_merged_10m_wgs84_mesh_sampling.tif"
OUT_FLAG = ROOT / "data" / "processed" / "mepa_4036_harbour_flags.tif"
FIGURE = ROOT / "figures" / "bathymetry_harbour_cleaning.png"

HARBOUR_BOX = (14.480, 35.870, 14.540, 35.915)   # lon0, lat0, lon1, lat1, both harbours
SHALLOW_LIMIT = -0.5        # m
ABOVE_LIMIT = 0.3           # m
COAST_BUFFER_M = 20.0       # m
SPIKE_LIMIT = 2.5           # m
SPIKE_WINDOW = 7            # cells
FILL_SEARCH_M = 300.0       # m, search radius of the interpolation
LAND_FILL_M = 30.0          # m

FLAG_NODATA, FLAG_SHALLOW, FLAG_SPIKE, FLAG_DILATED = 1, 2, 3, 4


def cell_size_m(transform, lat):
    dx = abs(transform.a) * 111320.0 * np.cos(np.radians(lat))
    dy = abs(transform.e) * 110574.0
    return dx, dy


def main(argv=None) -> int:
    import geopandas as gpd
    import rasterio
    from rasterio.features import rasterize
    from rasterio.fill import fillnodata
    from scipy.ndimage import binary_dilation, distance_transform_edt, generic_filter

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--figure", action="store_true")
    args = ap.parse_args(argv)

    with rasterio.open(SRC) as src:
        z = src.read(1).astype("float64")
        profile = src.profile
        t = src.transform
    coast = gpd.read_file(COAST).to_crs("EPSG:4326")
    land = rasterize(((g, 1) for g in coast.geometry), out_shape=z.shape, transform=t,
                     fill=0, dtype="uint8").astype(bool)
    water = ~land
    rows, cols = np.indices(z.shape)
    lon = t.c + t.a * (cols + 0.5)
    lat = t.f + t.e * (rows + 0.5)
    box = ((lon >= HARBOUR_BOX[0]) & (lon <= HARBOUR_BOX[2])
           & (lat >= HARBOUR_BOX[1]) & (lat <= HARBOUR_BOX[3]))
    dx, dy = cell_size_m(t, 0.5 * (HARBOUR_BOX[1] + HARBOUR_BOX[3]))
    dist_coast = distance_transform_edt(water, sampling=(dy, dx))

    # Median of the valid water cells around each cell, computed on the box alone
    r0, r1 = np.where(box.any(axis=1))[0][[0, -1]]
    c0, c1 = np.where(box.any(axis=0))[0][[0, -1]]
    sub = np.where(water & np.isfinite(z), z, np.nan)[r0:r1 + 1, c0:c1 + 1]
    med = np.full(z.shape, np.nan)
    med[r0:r1 + 1, c0:c1 + 1] = generic_filter(sub, np.nanmedian, size=SPIKE_WINDOW,
                                               mode="constant", cval=np.nan)

    inside = box & water
    flags = np.zeros(z.shape, dtype="uint8")
    flags[inside & ~np.isfinite(z)] = FLAG_NODATA
    # A bed above mean sea level inside the water polygon is a vessel, a pontoon or a
    # quay, the emerged part of a beach lying on the land side of the coastline
    flags[(flags == 0) & inside & (((z >= SHALLOW_LIMIT) & (dist_coast > COAST_BUFFER_M))
                                    | (z >= ABOVE_LIMIT))] = FLAG_SHALLOW
    # Near the shore the window mixes the shallow fringe with the channel, which
    # would read the fringe as a spike, so the spike test applies offshore of it
    flags[(flags == 0) & inside & np.isfinite(med) & (z - med > SPIKE_LIMIT)
          & (dist_coast > COAST_BUFFER_M)] = FLAG_SPIKE
    core = flags > 0
    grown = binary_dilation(core, structure=np.ones((3, 3), bool)) & inside & ~core
    flags[grown] = FLAG_DILATED
    bad = flags > 0

    clean = z.copy()
    clean[bad] = np.nan
    source = np.where(water, clean, np.nan)
    mask = np.isfinite(source).astype("uint8")
    filled = fillnodata(source.astype("float32"), mask=mask,
                        max_search_distance=FILL_SEARCH_M / dx, smoothing_iterations=0)
    clean[bad] = filled[bad]
    unfilled = bad & ~np.isfinite(clean)

    # Field for sampling the mesh: land cells near water take the nearest water value
    wet = water & np.isfinite(clean)
    dist_w, (ir, ic) = distance_transform_edt(~wet, sampling=(dy, dx), return_indices=True)
    mesh = np.where(wet, clean, np.nan)
    near = ~wet & (dist_w <= LAND_FILL_M)
    mesh[near] = clean[ir[near], ic[near]]

    profile.update(dtype="float32", nodata=np.nan, compress="deflate")
    for path, data in ((OUT_CLEAN, clean), (OUT_MESH, mesh)):
        with rasterio.open(path, "w", **profile) as dst:
            dst.write(data.astype("float32"), 1)
            dst.update_tags(source=SRC.name, script="clean_harbour_bathymetry.py")
    fprof = dict(profile, dtype="uint8", nodata=0)
    with rasterio.open(OUT_FLAG, "w", **fprof) as dst:
        dst.write(flags, 1)
        dst.update_tags(values="1 no data, 2 shallow away from coast, 3 upward spike, 4 dilation")

    n_in = int(inside.sum())
    print(f"harbour water cells {n_in}")
    for name, v in (("no data", FLAG_NODATA), ("shallow or above sea", FLAG_SHALLOW),
                    ("upward spike", FLAG_SPIKE), ("dilation", FLAG_DILATED)):
        print(f"  {name:24s} {(flags == v).sum():6d} ({(flags == v).sum() / n_in:.1%})")
    print(f"  flagged in all          {bad.sum():6d} ({bad.sum() / n_in:.1%}), left unfilled {unfilled.sum()}")
    change = clean[bad] - z[bad]
    ok = np.isfinite(change)
    print(f"  level change of flagged cells with a value: median {np.median(change[ok]):+.2f} m, "
          f"5 to 95 per cent {np.percentile(change[ok], 5):+.2f} to {np.percentile(change[ok], 95):+.2f} m")
    print(f"  harbour water cells at or above 0 m: before {(inside & (z >= 0)).sum()}, "
          f"after {(inside & (clean >= 0)).sum()}")
    print(f"written {OUT_CLEAN.name}, {OUT_MESH.name}, {OUT_FLAG.name}")
    if args.figure:
        figure(z, clean, flags, t, coast)
    return 0


def figure(z, clean, flags, t, coast):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from rasterio.windows import from_bounds

    views = [("Marsamxett", (14.488, 35.893, 14.512, 35.912)),
             ("Grand Harbour, Marsa and the creeks", (14.494, 35.874, 14.530, 35.898))]
    fig, axes = plt.subplots(2, 3, figsize=(15, 9.6))
    fcmap = ListedColormap(["#d64545", "#e8a33d", "#8a4fd6", "#f2d0e6"])
    for row, (title, b) in zip(axes, views):
        w = from_bounds(*b, t)
        r0, c0 = int(w.row_off), int(w.col_off)
        r1, c1 = r0 + int(w.height), c0 + int(w.width)
        ext = (t.c + t.a * c0, t.c + t.a * c1, t.f + t.e * r1, t.f + t.e * r0)
        zz, cc, ff = z[r0:r1, c0:c1], clean[r0:r1, c0:c1], flags[r0:r1, c0:c1]
        for ax, data, label in ((row[0], zz, "merged field as supplied"),
                                (row[2], cc, "after removal and interpolation")):
            im = ax.imshow(np.where(data < 0, data, np.nan), extent=ext, cmap="viridis",
                           vmin=-20, vmax=0, interpolation="nearest")
            ax.imshow(np.where(data >= 0, 1.0, np.nan), extent=ext, cmap=ListedColormap(["#c9c4b8"]),
                      interpolation="nearest")
            ax.set_title(f"{title}\n{label}", fontsize=10, loc="left")
        row[1].imshow(np.where(zz < 0, zz, np.nan), extent=ext, cmap="Greys_r", vmin=-20, vmax=0,
                      interpolation="nearest", alpha=0.45)
        row[1].imshow(np.where(ff > 0, ff, np.nan), extent=ext, cmap=fcmap, vmin=0.5, vmax=4.5,
                      interpolation="nearest")
        row[1].set_title(f"{title}\ncells removed", fontsize=10, loc="left")
        for ax in row:
            coast.boundary.plot(ax=ax, color="k", lw=0.5)
            ax.set_xlim(b[0], b[2]); ax.set_ylim(b[1], b[3])
            ax.tick_params(labelsize=8)
        fig.colorbar(im, ax=row[2], shrink=0.75, label="bed level, m")
    from matplotlib.patches import Patch
    axes[0, 1].legend(handles=[Patch(color=c, label=l) for c, l in zip(
        fcmap.colors, ["no value", f"above +{ABOVE_LIMIT} m, or above {SHALLOW_LIMIT} m over {COAST_BUFFER_M:.0f} m from coast",
                       f"over {SPIKE_LIMIT} m above local median", "edge, one cell"])],
        loc="lower left", fontsize=7.5, framealpha=0.9)
    fig.tight_layout()
    fig.savefig(FIGURE, dpi=130, facecolor="white")
    print(f"figure written to {FIGURE}")


if __name__ == "__main__":
    sys.exit(main())

"""Build the mesh of the outer domain used by the sweep of the long wave.

Domain B does not contain the generation of the long wave. A pressure
disturbance of the milghuba band is 55 to 280 km long, and a basin of the size
of domain B crossed by it retains a sixth to a half of the response of an
unbounded sea (docs/moving_pressure_channel_test.md). The outer domain covers
the Sicily Channel from 12.5 to 17.0 E and 34.5 to 37.7 N, some 400 by 355 km,
so that a disturbance is raised inside it and travels the shelf between Sicily
and Malta before reaching the harbours.

The mesh is the quadtree of build_mesh_v02.py with one coarser level. A base
cell of 3840 m covers the outer domain and halves to 1920 m over the box of
domain B, inside which the zones of version 02 are imposed unchanged. The base
grid of 3840 m lies on the lattice of the 1920 m grid of version 02, so the
cells inside domain B coincide with those of that mesh.

Land outside the Maltese Islands is taken from the EMODnet grid, as the cells
at or above zero, since at 2 to 4 km a surveyed coastline adds nothing. The
Maltese coastline is the one used for version 02. Bed level at the nodes is
taken from the MEPA 10 m grid, then from the EMODnet shelf grid, then from the
EMODnet grid of the channel written by download_emodnet_channel.py. Outside
domain B the nodes are held at MIN_DEPTH_OUTER or deeper, so that the coarse
cells along the Sicilian coast stay wet.

The mesh is for two-dimensional barotropic runs. It crosses the Malta
Escarpment and depths beyond 3000 m, where the argument that keeps domain B on
the plateau for sigma layers does not apply to a depth-averaged run.

Usage:
    python build_mesh_outer.py [--figure]
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_mesh_v02 as v2  # noqa: E402

ROOT = v2.ROOT
CHANNEL = ROOT / "data" / "external" / "emodnet_channel.tif"
OUT = ROOT / "data" / "processed" / "mesh_outer01"
FIGURE = ROOT / "figures" / "mesh_outer01.png"
NAME = "malta_outer01"

OUTER_LONLAT = (12.5, 34.5, 17.0, 37.7)
DOMAIN_B_LONLAT = v2.DOMAIN_LONLAT
BASE_OUTER_M = 3840.0
MIN_DEPTH_OUTER = 5.0           # m, shallowest bed outside domain B
MALTA_EXCLUSION = (14.0, 35.6, 14.8, 36.2)   # EMODnet land is not used here
RESONANT_DEPTHS = (70.0, 190.0)              # m, the plateau of the sizing exercise


def outer_land(dom):
    """Land polygons of the EMODnet grid in UTM 33N, the Maltese Islands excluded."""
    import geopandas as gpd
    import rasterio
    from rasterio.features import shapes
    from shapely.geometry import box, shape

    with rasterio.open(CHANNEL) as src:
        z = src.read(1)
        land = (z >= 0) | ~np.isfinite(z)
        polys = [shape(g) for g, v in shapes(land.astype("uint8"), mask=land,
                                             transform=src.transform) if v == 1]
    gs = gpd.GeoSeries(polys, crs=v2.CRS)
    gs = gs[~gs.intersects(box(*MALTA_EXCLUSION))]
    gs = gs.to_crs(v2.METRIC)
    gs = gs[gs.intersects(box(*dom))]
    # Islets below a tenth of a base cell are left as water.
    return gs[gs.area > 0.1 * BASE_OUTER_M ** 2].reset_index(drop=True)


def node_bed_level(lon, lat):
    z, src = v2.node_bed_level(lon, lat)
    channel = v2.sample_raster(CHANNEL, lon, lat)
    src = np.where(np.isfinite(z), src, np.where(np.isfinite(channel), 3, 0))
    z = np.where(np.isfinite(z), z, channel)
    lon0, lat0, lon1, lat1 = DOMAIN_B_LONLAT
    outside = (lon < lon0) | (lon > lon1) | (lat < lat0) | (lat > lat1)
    z = np.where(outside & ~(z < -MIN_DEPTH_OUTER), -MIN_DEPTH_OUTER, z)
    return z, src


def main(argv=None) -> int:
    global OUTER_LONLAT, OUT, FIGURE, NAME, CHANNEL
    import dfm_tools as dfmt
    import geopandas as gpd
    from shapely.geometry import box

    ap = argparse.ArgumentParser()
    ap.add_argument("--figure", action="store_true")
    ap.add_argument("--figure-only", action="store_true",
                    help="redraw the figure from the written mesh")
    ap.add_argument("--box", type=float, nargs=4, default=OUTER_LONLAT,
                    metavar=("LON0", "LAT0", "LON1", "LAT1"))
    ap.add_argument("--name", default="outer01", help="name of the variant")
    ap.add_argument("--bathymetry", default=str(CHANNEL),
                    help="EMODnet grid covering the box")
    args = ap.parse_args(argv)
    OUTER_LONLAT, CHANNEL = tuple(args.box), Path(args.bathymetry)
    OUT = ROOT / "data" / "processed" / f"mesh_{args.name}"
    FIGURE = ROOT / "figures" / f"mesh_{args.name}.png"
    NAME = f"malta_{args.name}"
    if args.figure_only:
        plot_from_file()
        return 0
    for p in (v2.BATHY, v2.SHELF, v2.COAST, CHANNEL):
        if not p.exists():
            print(f"missing input: {p}", file=sys.stderr)
            return 1
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    dom_b = v2.domain_metric()
    v2.DOMAIN_LONLAT, v2.BASE_M, v2.NAME = OUTER_LONLAT, BASE_OUTER_M, NAME
    dom = v2.domain_metric()
    v2.BASE_M = 1920.0
    print(f"outer domain in UTM 33N, {(dom[2] - dom[0]) / 1e3:.1f} x "
          f"{(dom[3] - dom[1]) / 1e3:.1f} km, base {BASE_OUTER_M:.0f} m")

    coast_m = gpd.read_file(v2.COAST).to_crs(v2.METRIC)
    zones = v2.zone_polygons(coast_m, dom_b)
    zones["domain_b"] = box(*dom_b)
    passes = (("domain_b", 1920.0),) + v2.PASSES

    m = dfmt.make_basegrid(dom[0], dom[2], dom[1], dom[3], dx=BASE_OUTER_M, dy=BASE_OUTER_M,
                           crs=v2.METRIC)
    print(f"  base grid           {m.mesh2d_get().face_x.size:8d} faces")
    for i, (key, target) in enumerate(passes):
        v2.refine(m, zones[key], target, last=i == len(passes) - 1)
        print(f"  refined {key:11s} {m.mesh2d_get().face_x.size:8d} faces (target {target:.0f} m)")
    v2.delete_land(m, coast_m)
    land = outer_land(dom)
    v2.delete_land(m, gpd.GeoDataFrame(geometry=land, crs=v2.METRIC))
    gm = m.mesh2d_get()
    print(f"  after land deletion {gm.face_x.size:8d} faces, {gm.node_x.size} nodes, "
          f"{len(land)} land polygons outside Malta ({time.time() - t0:.0f} s)")

    uds, _ = v2.to_wgs84_ugrid(m)
    grid = uds.grid
    z, src = node_bed_level(grid.node_x, grid.node_y)
    if np.isnan(z).any():
        print(f"  {np.isnan(z).sum()} nodes without bed level", file=sys.stderr)
        return 1
    uds["mesh2d_node_z"] = (grid.node_dimension, z)
    uds["mesh2d_node_z"].attrs.update(standard_name="altitude", long_name="bed level at nodes",
                                      units="m", mesh="mesh2d", location="node")
    net = OUT / f"{NAME}_net.nc"
    uds.ugrid.to_netcdf(net)
    v2.BASE_M = BASE_OUTER_M
    n_pli = v2.write_pli(OUT / f"{NAME}_bnd.pli", dom)

    sizes = v2.face_sizes(gm)
    tri = gm.nodes_per_face == 3
    print(f"\nwritten {net}")
    print(f"written {OUT / f'{NAME}_bnd.pli'} ({n_pli} points, one polyline)")
    print(f"\nfaces {sizes.size}, of which {tri.sum()} triangles from hanging-node transitions")
    print("faces by size class, quadrilaterals")
    for sz in (15, 30, 60, 120, 240, 480, 960, 1920, 3840):
        sel = (~tri) & (sizes > sz / 1.41) & (sizes <= sz * 1.41)
        print(f"  {sz:5d} m  {sel.sum():7d}")
    print(f"node bed level from MEPA {np.mean(src == 1):.1%}, EMODnet shelf "
          f"{np.mean(src == 2):.1%}, EMODnet channel {np.mean(src == 3):.1%}")
    depth = -z
    lo, hi = RESONANT_DEPTHS
    print(f"depth at the nodes: median {np.median(depth):.0f} m, maximum {depth.max():.0f} m, "
          f"between {lo:.0f} and {hi:.0f} m at {np.mean((depth >= lo) & (depth <= hi)):.1%}")
    o = v2.spherical_orthogonality(grid)
    print(f"orthogonality on the sphere, interior edges: p99 {np.percentile(o, 99):.5f}, "
          f"max {o.max():.5f}, above {v2.FM_ORTHO_LIMIT}: {(o > v2.FM_ORTHO_LIMIT).sum()}")
    print(f"total {time.time() - t0:.0f} s")

    if args.figure:
        plot(uds, z)
    return 0


def plot_from_file() -> None:
    import xugrid as xu

    uds = xu.open_dataset(OUT / f"{NAME}_net.nc")
    plot(uds, uds["mesh2d_node_z"].values)


def plot(uds, z) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection, PolyCollection
    from matplotlib.colors import LogNorm
    from matplotlib.patches import Rectangle

    grid = uds.grid
    fn = grid.face_node_connectivity
    depth = np.array([-z[row[row >= 0]].mean() for row in fn])
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6))
    xy = np.c_[grid.node_x, grid.node_y]
    segs = xy[grid.edge_node_connectivity]

    ax = axes[0]
    faces = [xy[row[row >= 0]] for row in fn]
    pc = PolyCollection(faces, array=np.clip(depth, 5, None), cmap="Blues",
                        norm=LogNorm(5, 4000), linewidths=0)
    ax.add_collection(pc)
    lo, hi = RESONANT_DEPTHS
    sel = (depth >= lo) & (depth <= hi)
    ax.add_collection(PolyCollection([f for f, s in zip(faces, sel) if s],
                                     facecolors="#eb6834", linewidths=0))
    ax.plot([], [], "s", color="#eb6834", label=f"depth of {lo:.0f} to {hi:.0f} m")
    ax.set_title("Outer domain, depth at the faces", fontsize=9, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    fig.colorbar(pc, ax=ax, label="depth, m", shrink=0.8)

    ax = axes[1]
    ax.add_collection(LineCollection(segs, colors="#52514e", linewidths=0.12))
    ax.set_title("Mesh, with domain B outlined", fontsize=9, loc="left")
    for a in axes:
        b = DOMAIN_B_LONLAT
        a.add_patch(Rectangle((b[0], b[1]), b[2] - b[0], b[3] - b[1], fill=False,
                              edgecolor="#0b0b0b", lw=1.2))
        a.set_xlim(OUTER_LONLAT[0], OUTER_LONLAT[2])
        a.set_ylim(OUTER_LONLAT[1], OUTER_LONLAT[3])
        a.set_aspect(1 / math.cos(math.radians(36.0)))
    fig.savefig(FIGURE, dpi=160, facecolor="#fcfcfb", bbox_inches="tight")
    print(f"figure written to {FIGURE}")


if __name__ == "__main__":
    sys.exit(main())

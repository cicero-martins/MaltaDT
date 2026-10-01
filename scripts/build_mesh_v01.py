"""Build the unstructured mesh of domain B, version 01.

Domain B covers the Maltese Islands and the near Malta Plateau, 14.05 to
15.00 E and 35.70 to 36.30 N, as proposed in docs/domain_and_discretisation.md.
The mesh is a single quadtree refined from a regular base grid, with no merge
of separately built meshes, since the merge of hand-built triangles into a
generated mesh is what left the StagnoneDT v05 mesh rejected by FM as not
orthogonal.

Resolution follows the zones of the sizing exercise. A base cell of 1920 m
halves to 960, 480, 240, 120, 60, 30 and 15 m, and each zone is imposed as a
polygon refined to its target edge.

    zone                                              target   sizing value
    beyond 15 km of the coast                         1920 m   1500 m
    within 15 km of the coast                          480 m    300 m
    within 2 km of the coast                           120 m    100 m
    Valletta harbours and approaches                    30 m     30 m
    Valletta channels narrower than 150 m               15 m     15 m

A band of the intermediate level, BAND_CELLS cells wide, separates every zone
from surroundings two levels coarser, so that neighbouring cells differ by one
level and the cell area changes by a factor of four at most.

The mesh is built in UTM 33N and its nodes are transformed to WGS84 at the end.
Refined directly in geographic coordinates, the transition triangles at the
hanging nodes of the quadtree reach an orthogonality of 1, against the 0.5 at
which FM rejects the network, whereas built in UTM they are orthogonal to
within 0.0002 after the transformation, since the transverse Mercator
projection is conformal and preserves the angles on which orthogonality
depends. The working coordinate system of the project, WGS84, is kept for the
mesh written to file.

Channel width in the harbours is measured as in domain_design_estimate.py,
twice the distance to land along the ridge of the distance transform, and the
narrow zone is confined to the water inside the two harbours, separated from
the sea by the outer section lines of estimate_basin_modes.py.

Order of operations follows the inherited mesh generation workflow: base grid,
refinement on the intact grid, deletion of land, conversion to UGRID. Land is
deleted where a cell centre falls inside a coastline polygon, so that narrow
channels keep their measured width rather than gaining the cells that straddle
the shore. The open boundary is the edge of the domain, written as a single
polyline, since FM reads only the first polyline of a .pli file.

Bed level is assigned at the nodes, from the MEPA 10 m grid where it has data
and from EMODnet elsewhere, for use with bedLevType = 3. The EMODnet DTM is
referred to lowest astronomical tide and the MEPA grid to a surface close to
mean sea level. The difference is of the order of 0.1 m at Malta and is not
corrected in this version, since it falls on the open plateau at depths of
50 to 190 m.

Usage:
    python build_mesh_v01.py [--figure]
"""

from __future__ import annotations

import argparse
import math
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
ROOT = Path(__file__).resolve().parents[1]
BATHY = ROOT / "data" / "processed" / "mepa_4036_merged_10m_wgs84.tif"
SHELF = ROOT / "data" / "external" / "emodnet_shelf.tif"
COAST = ROOT / "data" / "processed" / "malta_coastline_wgs84.gpkg"
OUT = ROOT / "data" / "processed" / "mesh_v01"
FIGURE = ROOT / "figures" / "mesh_v01.png"
NAME = "malta_v01"

CRS = "EPSG:4326"
METRIC = "EPSG:32633"
DOMAIN_LONLAT = (14.05, 35.70, 15.00, 36.30)
BASE_M = 1920.0

ZONE_COAST_FAR_M = 15000.0
ZONE_COAST_NEAR_M = 2000.0
HARBOUR_BOX = (14.488, 35.872, 14.535, 35.912)
NARROW_WIDTH_M = 150.0
HARBOUR_BUFFER_M = 60.0         # carries the basin zone over the shoreline
APPROACH_M = 300.0              # around the mouth lines, entrance and breakwater
NARROW_BUFFER_M = 30.0
BAND_CELLS = 3
# Refinement passes, coarse to fine, as (zone, target edge in metres). The zones
# named band_* are the intermediate levels.
PASSES = (("band_960", 960.0), ("coast_far", 480.0), ("band_240", 240.0),
          ("coast_near", 120.0), ("band_60", 60.0), ("harbour", 30.0), ("narrow", 15.0))
FM_ORTHO_LIMIT = 0.5


def domain_metric():
    """Domain rectangle in UTM 33N covering the nominal box, a whole number of base cells."""
    from pyproj import Transformer

    tr = Transformer.from_crs(CRS, METRIC, always_xy=True)
    lon0, lat0, lon1, lat1 = DOMAIN_LONLAT
    xs, ys = tr.transform([lon0, lon0, lon1, lon1], [lat0, lat1, lat0, lat1])
    x0 = math.floor(min(xs) / BASE_M) * BASE_M
    y0 = math.floor(min(ys) / BASE_M) * BASE_M
    x1 = x0 + math.ceil((max(xs) - x0) / BASE_M) * BASE_M
    y1 = y0 + math.ceil((max(ys) - y0) / BASE_M) * BASE_M
    return x0, y0, x1, y1


def zone_polygons(coast_m, dom):
    """Refinement polygons in UTM 33N, keyed as in PASSES."""
    from shapely.geometry import box

    land = coast_m.union_all()
    dom_box = box(*dom)
    z = {}
    z["coast_far"] = land.buffer(ZONE_COAST_FAR_M).simplify(200).intersection(dom_box)
    z["band_960"] = land.buffer(ZONE_COAST_FAR_M + BAND_CELLS * 960).simplify(200) \
        .intersection(dom_box)
    z["coast_near"] = land.buffer(ZONE_COAST_NEAR_M).simplify(50).intersection(dom_box)
    z["band_240"] = land.buffer(ZONE_COAST_NEAR_M + BAND_CELLS * 240).simplify(50) \
        .intersection(dom_box)
    basins, narrow, mouths = harbour_zones(coast_m)
    z["harbour"] = basins.buffer(HARBOUR_BUFFER_M).union(mouths.buffer(APPROACH_M))
    z["band_60"] = z["harbour"].buffer(BAND_CELLS * 60)
    z["narrow"] = narrow.buffer(NARROW_BUFFER_M).simplify(5)
    return z


def harbour_zones(coast_m):
    """Basin water, narrow channels and mouth lines of the two harbours, in UTM 33N.

    The water inside each harbour is separated from the sea by the outer section
    lines of estimate_basin_modes.py and taken as the component containing an
    interior point. A cell lies in a narrow channel when both the width of the
    nearest ridge of the distance transform and twice its own distance to land
    are below NARROW_WIDTH_M. The second condition bounds the width from below
    at the point itself, and excludes wide water whose nearest ridge belongs to
    a small jetty.
    """
    import geopandas as gpd
    from rasterio.features import rasterize, shapes
    from rasterio.transform import from_origin
    from scipy.ndimage import binary_dilation, distance_transform_edt, label, maximum_filter
    from shapely.geometry import LineString, shape
    from shapely.ops import unary_union

    import estimate_basin_modes as ebm

    corners = gpd.GeoSeries.from_xy([HARBOUR_BOX[0], HARBOUR_BOX[2]],
                                    [HARBOUR_BOX[1], HARBOUR_BOX[3]], crs=CRS).to_crs(METRIC)
    x0, x1 = float(corners.x.min()), float(corners.x.max())
    y0, y1 = float(corners.y.min()), float(corners.y.max())
    res = 5.0
    nx, ny = int((x1 - x0) / res), int((y1 - y0) / res)
    t = from_origin(x0, y1, res, res)
    land = rasterize(((g, 1) for g in coast_m.geometry), out_shape=(ny, nx), transform=t,
                     fill=0, dtype="uint8").astype(bool)

    lines = [gpd.GeoSeries([LineString(spec["mouths"]["outer"])], crs=CRS).to_crs(METRIC).iloc[0]
             for spec in ebm.BASINS.values()]
    cut = rasterize(((ln, 1) for ln in lines), out_shape=(ny, nx), transform=t, fill=0,
                    dtype="uint8", all_touched=True).astype(bool)
    cut = binary_dilation(cut, structure=np.ones((3, 3)))
    lab, _ = label(~land & ~cut, structure=np.ones((3, 3)))
    basin = np.zeros_like(land)
    for spec in ebm.BASINS.values():
        p = gpd.GeoSeries.from_xy([spec["interior"][0]], [spec["interior"][1]],
                                  crs=CRS).to_crs(METRIC)
        c, r = ~t * (float(p.x.iloc[0]), float(p.y.iloc[0]))
        basin |= lab == lab[int(r), int(c)]

    wet = ~land
    dt = distance_transform_edt(wet, sampling=res)
    ridge = wet & (dt >= maximum_filter(dt, size=3) - 1e-9) & (dt > res)
    _, (ri, ci) = distance_transform_edt(~ridge, return_indices=True)
    width = 2 * dt[ri, ci]
    narrow = basin & (width < NARROW_WIDTH_M) & (2 * dt < NARROW_WIDTH_M)

    def polygons(mask):
        return unary_union([shape(g) for g, v in
                            shapes(mask.astype("uint8"), mask=mask, transform=t) if v == 1])

    return polygons(basin), polygons(narrow), unary_union(lines)


def to_geometrylist(geom):
    """A (multi)polygon with its holes as a meshkernel GeometryList.

    Without the holes, a ring of narrow water around a wide area would refine
    the wide area as well.
    """
    import meshkernel as mk

    sep, inner = -999.0, -998.0
    xs, ys = [], []
    parts = list(geom.geoms) if geom.geom_type == "MultiPolygon" else [geom]
    for p in parts:
        if p.is_empty or p.area < 1.0:
            continue
        if xs:
            xs.append(sep)
            ys.append(sep)
        x, y = p.exterior.coords.xy
        xs.extend(x)
        ys.extend(y)
        for ring in p.interiors:
            xs.append(inner)
            ys.append(inner)
            x, y = ring.coords.xy
            xs.extend(x)
            ys.extend(y)
    return mk.GeometryList(x_coordinates=np.asarray(xs, dtype=float),
                           y_coordinates=np.asarray(ys, dtype=float),
                           geometry_separator=sep, inner_outer_separator=inner)


def refine(m, geom, target, last=False):
    """Refine inside a polygon to a target edge.

    Faces intersected by the polygon are refined as well, since otherwise a
    channel narrower than two cells, every face of which touches the shoreline
    of the polygon, is never refined. Hanging nodes are left unconnected
    between passes, so that a later pass refines quadrilaterals rather than the
    triangles a connection creates, and are connected on the last pass.
    """
    import meshkernel as mk

    par = mk.MeshRefinementParameters(min_edge_size=target, max_refinement_iterations=10,
                                      refine_intersected=True,
                                      connect_hanging_nodes=last, smoothing_iterations=2)
    m.mesh2d_refine_based_on_polygon(to_geometrylist(geom), par)


def delete_land(m, coast_m):
    import meshkernel as mk

    for g in coast_m.geometry:
        parts = list(g.geoms) if g.geom_type == "MultiPolygon" else [g]
        for p in parts:
            x, y = p.exterior.coords.xy
            gl = mk.GeometryList(x_coordinates=np.asarray(x, dtype=float),
                                 y_coordinates=np.asarray(y, dtype=float))
            m.mesh2d_delete(geometry_list=gl,
                            delete_option=mk.DeleteMeshOption.FACES_WITH_INCLUDED_CIRCUMCENTERS,
                            invert_deletion=False)


def to_wgs84_ugrid(m):
    """UGRID dataset of the mesh with its nodes transformed to WGS84.

    Only the node coordinates are transformed. The face-node connectivity of
    the UTM mesh is carried over unchanged, since rebuilding the faces from the
    edges on the sphere was found to return a slightly different set of faces.
    """
    import dfm_tools as dfmt
    import xugrid as xu
    from pyproj import Transformer

    projected = dfmt.meshkernel_to_UgridDataset(m, crs=METRIC).grid
    tr = Transformer.from_crs(METRIC, CRS, always_xy=True)
    lon, lat = tr.transform(projected.node_x, projected.node_y)
    grid = xu.Ugrid2d(node_x=np.asarray(lon, dtype=float), node_y=np.asarray(lat, dtype=float),
                      fill_value=-1, face_node_connectivity=projected.face_node_connectivity,
                      edge_node_connectivity=projected.edge_node_connectivity,
                      name="mesh2d", is_projected=False, crs=CRS)
    return xu.UgridDataset(grids=[grid]), projected


def spherical_orthogonality(grid):
    """Orthogonality of the interior edges, computed by meshkernel on the sphere."""
    import meshkernel as mk

    s = mk.MeshKernel(projection=mk.ProjectionType.SPHERICAL)
    s.mesh2d_set(mk.Mesh2d(node_x=grid.node_x.astype(float), node_y=grid.node_y.astype(float),
                           edge_nodes=grid.edge_node_connectivity.ravel().astype(np.int32)))
    v = s.mesh2d_get_orthogonality().values
    return np.abs(v[v > -998])


def sample_raster(path, lon, lat):
    """Bilinear sample of a geographic raster at points, NaN outside or on nodata."""
    import rasterio
    from scipy.interpolate import RegularGridInterpolator

    with rasterio.open(path) as src:
        z = src.read(1).astype(float)
        if src.nodata is not None:
            z[z == src.nodata] = np.nan
        t = src.transform
        xs = t.c + t.a * (np.arange(src.width) + 0.5)
        ys = t.f + t.e * (np.arange(src.height) + 0.5)
    if ys[0] > ys[-1]:
        ys, z = ys[::-1], z[::-1]
    f = RegularGridInterpolator((ys, xs), z, method="linear", bounds_error=False, fill_value=np.nan)
    return f(np.c_[lat, lon])


def node_bed_level(lon, lat):
    z = sample_raster(BATHY, lon, lat)
    shelf = sample_raster(SHELF, lon, lat)
    src = np.where(np.isfinite(z), 1, np.where(np.isfinite(shelf), 2, 0))
    return np.where(np.isfinite(z), z, shelf), src


def face_sizes(g):
    """Square root of face area, in the units of the node coordinates."""
    out = np.empty(g.nodes_per_face.size)
    k = 0
    for i, n in enumerate(g.nodes_per_face):
        idx = g.face_nodes[k:k + n]
        k += n
        x, y = g.node_x[idx], g.node_y[idx]
        out[i] = math.sqrt(abs(0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)))
    return out


def write_pli(path, dom):
    """The domain edge as one polyline in WGS84, a quarter of a base cell outside the mesh.

    The rectangle is densified before transformation, since a straight edge in
    UTM is not a straight line of constant longitude or latitude.
    """
    from pyproj import Transformer

    x0, y0, x1, y1 = dom
    e = BASE_M / 4
    x0, y0, x1, y1 = x0 - e, y0 - e, x1 + e, y1 + e
    step = BASE_M / 2
    def seg(xa, ya, xb, yb):
        n = max(2, int(math.hypot(xb - xa, yb - ya) / step))
        return list(zip(np.linspace(xa, xb, n, endpoint=False), np.linspace(ya, yb, n, endpoint=False)))
    pts = seg(x1, y0, x1, y1) + seg(x1, y1, x0, y1) + seg(x0, y1, x0, y0) + seg(x0, y0, x1, y0)
    pts.append(pts[0])
    tr = Transformer.from_crs(METRIC, CRS, always_xy=True)
    lon, lat = tr.transform([p[0] for p in pts], [p[1] for p in pts])
    with open(path, "w") as f:
        f.write(f"{NAME}_bnd\n    {len(pts)}    2\n")
        for x, y in zip(lon, lat):
            f.write(f"{x:.6f} {y:.6f}\n")
    return len(pts)


def main(argv=None) -> int:
    import dfm_tools as dfmt
    import geopandas as gpd

    ap = argparse.ArgumentParser()
    ap.add_argument("--figure", action="store_true")
    ap.add_argument("--figure-only", action="store_true",
                    help="redraw the figure from the written mesh")
    args = ap.parse_args(argv)
    if args.figure_only:
        plot_from_file()
        return 0
    for p in (BATHY, SHELF, COAST):
        if not p.exists():
            print(f"missing input: {p}", file=sys.stderr)
            return 1
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    dom = domain_metric()
    print(f"domain in UTM 33N {dom[0]:.0f} to {dom[2]:.0f} E, {dom[1]:.0f} to {dom[3]:.0f} N, "
          f"{(dom[2] - dom[0]) / 1e3:.1f} x {(dom[3] - dom[1]) / 1e3:.1f} km, base {BASE_M:.0f} m")
    coast_m = gpd.read_file(COAST).to_crs(METRIC)
    zones = zone_polygons(coast_m, dom)

    m = dfmt.make_basegrid(dom[0], dom[2], dom[1], dom[3], dx=BASE_M, dy=BASE_M, crs=METRIC)
    print(f"  base grid           {m.mesh2d_get().face_x.size:8d} faces")
    for i, (key, target) in enumerate(PASSES):
        refine(m, zones[key], target, last=i == len(PASSES) - 1)
        print(f"  refined {key:11s} {m.mesh2d_get().face_x.size:8d} faces (target {target:.0f} m)")
    delete_land(m, coast_m)
    gm = m.mesh2d_get()
    print(f"  after land deletion {gm.face_x.size:8d} faces, {gm.node_x.size} nodes "
          f"({time.time() - t0:.0f} s)")

    uds, projected = to_wgs84_ugrid(m)
    grid = uds.grid
    z, src = node_bed_level(grid.node_x, grid.node_y)
    if np.isnan(z).any():
        print(f"  {np.isnan(z).sum()} nodes without bed level, set to -150 m", file=sys.stderr)
        z = np.where(np.isnan(z), -150.0, z)
    uds["mesh2d_node_z"] = (grid.node_dimension, z)
    uds["mesh2d_node_z"].attrs.update(standard_name="altitude", long_name="bed level at nodes",
                                      units="m", mesh="mesh2d", location="node")
    net = OUT / f"{NAME}_net.nc"
    uds.ugrid.to_netcdf(net)
    n_pli = write_pli(OUT / f"{NAME}_bnd.pli", dom)

    # Quality report, sizes from the UTM mesh, orthogonality from the spherical one.
    sizes = face_sizes(gm)
    tri = gm.nodes_per_face == 3
    fn = grid.face_node_connectivity
    face_z = np.array([z[row[row >= 0]].mean() for row in fn])
    print(f"\nwritten {net}")
    print(f"written {OUT / f'{NAME}_bnd.pli'} ({n_pli} points, one polyline)")
    print(f"\nfaces {sizes.size}, of which {tri.sum()} triangles from hanging-node transitions")
    print("faces by size class, quadrilaterals")
    for sz in (15, 30, 60, 120, 240, 480, 960, 1920):
        sel = (~tri) & (sizes > sz / 1.41) & (sizes <= sz * 1.41)
        print(f"  {sz:5d} m  {sel.sum():7d}")
    print(f"node bed level from MEPA {np.mean(src == 1):.1%}, from EMODnet {np.mean(src == 2):.1%}")
    print(f"faces with mean node bed level at or above 0 m: {(face_z >= 0).sum()}")
    o = spherical_orthogonality(grid)
    print(f"orthogonality on the sphere, interior edges: median {np.median(o):.5f}, "
          f"p99 {np.percentile(o, 99):.5f}, max {o.max():.5f}, "
          f"above {FM_ORTHO_LIMIT}: {(o > FM_ORTHO_LIMIT).sum()}, above 0.01: {(o > 0.01).sum()}")
    print(f"total {time.time() - t0:.0f} s")

    if args.figure:
        plot(uds, sizes)
    return 0


def plot(uds, sizes):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    from matplotlib.colors import LogNorm

    grid = uds.grid
    fig, axes = plt.subplots(1, 2, figsize=(14, 6.5), gridspec_kw=dict(width_ratios=[1.35, 1]))
    xy = np.c_[grid.node_x, grid.node_y]
    segs = xy[grid.edge_node_connectivity]
    for ax, extent, lw in ((axes[0], None, 0.15), (axes[1], HARBOUR_BOX, 0.25)):
        ax.add_collection(LineCollection(segs, colors="#52514e", linewidths=lw))
        sc = ax.scatter(grid.face_x, grid.face_y, c=sizes, s=1 if extent is None else 3,
                        cmap="viridis_r", norm=LogNorm(15, 1920), linewidths=0)
        if extent is None:
            ax.set_xlim(grid.node_x.min(), grid.node_x.max())
            ax.set_ylim(grid.node_y.min(), grid.node_y.max())
            ax.set_title("Domain B, mesh v01, face size", fontsize=9, loc="left")
        else:
            ax.set_xlim(extent[0], extent[2])
            ax.set_ylim(extent[1], extent[3])
            ax.set_title("Valletta harbours", fontsize=9, loc="left")
        ax.set_aspect(1 / math.cos(math.radians(36.0)))
    fig.colorbar(sc, ax=axes, label="square root of face area, m", shrink=0.8)
    out = FIGURE
    try:
        fig.savefig(out, dpi=170, facecolor="#fcfcfb", bbox_inches="tight")
    except OSError:
        # A PNG open in an editor preview cannot be overwritten on Windows.
        out = FIGURE.with_suffix(".new.png")
        fig.savefig(out, dpi=170, facecolor="#fcfcfb", bbox_inches="tight")
    print(f"figure written to {out}")


def plot_from_file():
    """Redraw the figure from the written mesh, without rebuilding it."""
    import xugrid as xu

    uds = xu.open_dataset(OUT / f"{NAME}_net.nc")
    g = uds.grid
    fn = g.face_node_connectivity
    sizes = np.empty(g.n_face)
    for i, row in enumerate(fn):
        idx = row[row >= 0]
        x = g.node_x[idx] * 111320.0 * math.cos(math.radians(g.node_y[idx].mean()))
        y = g.node_y[idx] * 110574.0
        sizes[i] = math.sqrt(abs(0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)))
    plot(uds, sizes)


if __name__ == "__main__":
    sys.exit(main())

"""Build the synthetic long-wave pulse test of the open boundary condition.

The Valletta model is to carry a weakly reflective open boundary, since a
prescribed water level reflects outgoing long waves back into the domain and
contaminates the seiche signal while producing plausible output. This test
measures the reflection of the D-Flow FM Riemann boundary before any production
run relies on it.

A Gaussian hump of water level is released from rest and splits into outgoing
waves. Each configuration is run three times, with a Riemann boundary, with a
prescribed water level of zero, and in a reference domain large enough that no
reflection returns to the stations within the simulated window. Inside the
common area the reference differs from the test only by the absence of the
boundary, so the difference of the two records at a station is the reflected
signal itself, and incident and reflected waves need not be separated in time.

Two geometries are built on a flat bed at 150 m, the depth of the Malta Plateau
where the open boundary of domain B will lie, and at the 1500 m cell size
proposed there.

- A channel three cells wide, for normal incidence, with pulses whose time
  scale is 5 and 20 minutes. The Riemann formulation of FM is exact for normal
  incidence in the linear limit, so this case tests the implementation.
- Square basins 120 and 240 km across with the boundary on all four sides, for
  oblique incidence. FM considers only the velocity normal to the boundary, so
  first-order theory gives a reflection coefficient (1 - cos t)/(1 + cos t) at
  incidence angle t, and the stations sample 0 to 45 degrees.

Coriolis is disabled so that the boundary is tested in isolation. The FM
formulation also assumes a fluid initially at rest with no residual current,
Technical Reference Manual section 6.4.2.2, and a boundary crossed by a mean
flow is left to a later case.

Usage:
    python build_riemann_pulse_test.py
"""

from __future__ import annotations

import math
import shutil
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "model" / "tests" / "riemann_pulse"
FM_LAUNCHER = (r"C:\Program Files\Deltares\Delft3D FM Suite 2026.01 HMWQ\plugins"
               r"\DeltaShell.Dimr\kernels\x64\bin\run_dflowfm.bat")

G = 9.81
DEPTH = 150.0                   # m, Malta Plateau at the domain B boundary
DX = 1500.0                     # m, offshore cell size proposed for domain B
AMPLITUDE = 0.2                 # m, initial hump, split into two halves of 0.1 m
CELERITY = math.sqrt(G * DEPTH)

# Channel geometry, x along the channel, hump at x = 0. The west wall and the
# east end of the reference lie far enough that their reflections reach no
# station within the window, which main() verifies. Every extent is a whole
# number of cells.
CHANNEL = dict(width_cells=3, x_west=-400e3, x_east_test=200e3,
               x_east_ref=650e3, t_stop=4 * 3600.0,
               stations={"ch_100km": 100e3, "ch_180km": 180e3,
                         "ch_bnd": 200e3 - DX / 2})
CHANNEL_SIGMAS_MIN = (5.0, 20.0)

# Square basins, hump at the centre. Stations lie in the first cell inside the
# east boundary at the listed incidence angles, and at mid-radius. The larger
# basin doubles the distance from the source to the boundary, which halves the
# departure of a cylindrical front from the plane wave the Riemann condition
# assumes, and so separates that departure from a defect of the boundary.
BASINS = {
    "sq060": dict(half_test=60e3, half_ref=240e3, t_stop=2.5 * 3600.0),
    "sq120": dict(half_test=120e3, half_ref=300e3, t_stop=3.0 * 3600.0),
}
BASIN_SIGMA_MIN = 5.0
BASIN_ANGLES = (0.0, 22.5, 30.0, 45.0)

VARIANTS = ("riemann", "waterlevel", "reference")


def make_mesh(x0, x1, y0, y1, path: Path) -> int:
    """Uniform cartesian mesh with node bed levels, as FM with bedLevType=3 needs."""
    import dfm_tools as dfmt

    # A projected crs makes the grid cartesian, dfm_tools 0.45 derives it.
    mk = dfmt.make_basegrid(x0, x1, y0, y1, dx=DX, dy=DX, crs="EPSG:32633")
    uds = dfmt.meshkernel_to_UgridDataset(mk, crs="EPSG:32633")
    grid = uds.grid
    nnodes = grid.n_node
    node_z = np.full(nnodes, -DEPTH)
    uds["mesh2d_node_z"] = (grid.node_dimension, node_z)
    uds["mesh2d_node_z"].attrs.update(standard_name="altitude", units="m",
                                      mesh="mesh2d", location="node")
    uds.ugrid.to_netcdf(path)
    return int(grid.n_face)


def write_pli(path: Path, name: str, vertices) -> None:
    """A single polyline through all the vertices.

    FM 2026.01 reads only the first polyline of a .pli file and ignores the
    rest with no more than a warning, which in a first build of this test left
    three sides of the basin closed. A boundary spanning several sides is
    therefore written as one polyline turning the corners.
    """
    with open(path, "w") as f:
        f.write(f"{name}\n    {len(vertices)}    2\n")
        for x, y in vertices:
            f.write(f"{x:.3f} {y:.3f}\n")


def write_bc(path: Path, name: str, n_points: int, quantity: str, t_stop: float) -> None:
    """Zero forcing at every support point, as a two-row time series."""
    with open(path, "w") as f:
        f.write("[General]\nfileVersion = 1.01\nfileType    = boundConds\n\n")
        for p in range(1, n_points + 1):
            f.write("[Forcing]\n")
            f.write(f"name              = {name}_{p:04d}\n")
            f.write("function          = timeseries\n")
            f.write("timeInterpolation = linear\n")
            f.write("quantity          = time\n")
            f.write("unit              = seconds since 2026-01-01 00:00:00\n")
            f.write(f"quantity          = {quantity}\n")
            f.write("unit              = m\n")
            f.write(f"0.0 0.0\n{t_stop + 3600.0:.1f} 0.0\n\n")


def write_ext(path: Path, pli: str, bc: str, quantity: str | None) -> None:
    with open(path, "w") as f:
        f.write("[General]\nfileVersion = 2.01\nfileType    = extForce\n\n")
        if quantity is not None:
            f.write(f"[Boundary]\nquantity     = {quantity}\n"
                    f"locationFile = {pli}\nforcingFile  = {bc}\n")


def write_hump(path: Path, x0, x1, y0, y1, sigma_x: float, one_d: bool) -> None:
    """Initial water level as samples on the mesh spacing, zero at the boundary."""
    xs = np.arange(x0, x1 + DX / 2, DX / 2)
    ys = np.arange(y0, y1 + DX / 2, DX / 2)
    X, Y = np.meshgrid(xs, ys)
    r2 = X ** 2 if one_d else X ** 2 + Y ** 2
    eta = AMPLITUDE * np.exp(-r2 / (2 * sigma_x ** 2))
    keep = eta > 1e-6
    # Samples beyond the hump are written at zero along a coarse frame, so that
    # triangulation does not extrapolate the hump to the boundary.
    frame = (np.arange(X.size) % 97 == 0) & ~keep.ravel()
    sel = keep.ravel() | frame
    np.savetxt(path, np.column_stack([X.ravel()[sel], Y.ravel()[sel],
                                      np.where(keep, eta, 0.0).ravel()[sel]]),
               fmt="%.2f %.2f %.6e")


def write_inifield(path: Path, xyz: str) -> None:
    with open(path, "w") as f:
        f.write("[General]\nfileVersion = 2.00\nfileType    = iniField\n\n")
        f.write(f"[Initial]\nquantity            = initialWaterLevel\ndataFile            = {xyz}\n"
                "dataFileType        = sample\ninterpolationMethod = triangulation\n"
                "operand             = O\n")


def write_obs(path: Path, stations: dict) -> None:
    with open(path, "w") as f:
        for name, (x, y) in stations.items():
            f.write(f"{x:.2f} {y:.2f} '{name}'\n")


def write_mdu(path: Path, name: str, t_stop: float) -> None:
    text = f"""# Riemann boundary pulse test, case {name}. Written by build_riemann_pulse_test.py.
[General]
fileVersion           = 1.09
fileType              = modelDef
program               = D-Flow FM
autoStart             = 2
pathsRelativeToParent = 0

[Geometry]
netFile               = {name}_net.nc
iniFieldFile          = inifield.ini
bedLevType            = 3
waterLevIni           = 0.0
kmx                   = 0
angLat                = 0.0

[Numerics]
CFLMax                = 0.7
advecType             = 33
timeStepType          = 2
tlfSmo                = 0.0
teta0                 = 0.55

[Physics]
unifFrictCoef         = 0.023
unifFrictType         = 1
vicouv                = 0.0
dicouv                = 0.0
smagorinsky           = 0.0
ag                    = {G}
rhomean               = 1025.0

[Time]
refDate               = 20260101
tUnit                 = S
dtUser                = 30.0
dtMax                 = 15.0
dtInit                = 1.0
tStart                = 0.0
tStop                 = {t_stop:.1f}

[External Forcing]
extForceFile          =
extForceFileNew       = forcing.ext

[Output]
outputDir             = output
obsFile               = stations_obs.xyn
hisInterval           = 30.0
mapInterval           = 600.0
rstInterval           = 0.0
wrimap_velocity_vector = 0
wrimap_upward_velocity_component = 0
"""
    path.write_text(text)


def build_case(case: str, x0, x1, y0, y1, pli_vertices, stations, sigma_x,
               t_stop, variant, one_d) -> int:
    d = OUT / case
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    ncells = make_mesh(x0, x1, y0, y1, d / f"{case}_net.nc")
    write_hump(d / "hump.xyz", x0, x1, y0, y1, sigma_x, one_d)
    write_inifield(d / "inifield.ini", "hump.xyz")
    write_obs(d / "stations_obs.xyn", stations)
    if variant == "reference":
        write_ext(d / "forcing.ext", "", "", None)
    else:
        quantity = "riemannbnd" if variant == "riemann" else "waterlevelbnd"
        write_pli(d / "boundary.pli", "bnd", pli_vertices)
        write_bc(d / "boundary.bc", "bnd", len(pli_vertices), quantity, t_stop)
        write_ext(d / "forcing.ext", "boundary.pli", "boundary.bc", quantity)
    write_mdu(d / f"{case}.mdu", case, t_stop)
    return ncells


def write_runner(cases) -> None:
    """Serial launcher for every case, FM 2026.01 on Windows."""
    lines = ["@echo off", "rem Written by build_riemann_pulse_test.py", 'cd /d "%~dp0"',
             f'set dflowfm="{FM_LAUNCHER}"']
    for case in cases:
        lines += [f"pushd {case}",
                  f"call %dflowfm% --autostartstop {case}.mdu > run.log 2>&1",
                  f"echo {case} exit %ERRORLEVEL%", "popd"]
    (OUT / "run_all.bat").write_text("\r\n".join(lines) + "\r\n")


def check_windows() -> None:
    """No reflection from a far wall may reach a station within the window."""
    c, ch = CELERITY, CHANNEL
    hump_to_west_and_back = min(2 * abs(ch["x_west"]) + x for x in ch["stations"].values())
    hump_to_ref_east_and_back = min(2 * ch["x_east_ref"] - x for x in ch["stations"].values())
    for label, dist in (("channel west wall", hump_to_west_and_back),
                        ("channel reference east wall", hump_to_ref_east_and_back)):
        if dist / c < ch["t_stop"]:
            raise AssertionError(f"{label} reflection arrives at {dist / c / 3600:.2f} h")
    for name, b in BASINS.items():
        worst = 2 * b["half_ref"] - b["half_test"] * math.sqrt(2)
        if worst / c < b["t_stop"]:
            raise AssertionError(f"{name} reference wall reflection arrives at "
                                 f"{worst / c / 3600:.2f} h")


def main() -> int:
    check_windows()
    OUT.mkdir(parents=True, exist_ok=True)
    summary = []

    ch = CHANNEL
    w = ch["width_cells"] * DX
    stations = {k: (x, w / 2) for k, x in ch["stations"].items()}
    for sigma_min in CHANNEL_SIGMAS_MIN:
        sigma_x = CELERITY * sigma_min * 60
        for variant in VARIANTS:
            x_east = ch["x_east_ref"] if variant == "reference" else ch["x_east_test"]
            case = f"ch_s{sigma_min:02.0f}_{variant}"
            seg = [(x_east, -DX / 4), (x_east, w + DX / 4)]
            n = build_case(case, ch["x_west"], x_east, 0.0, w, seg, stations,
                           sigma_x, ch["t_stop"], variant, one_d=True)
            summary.append((case, n, sigma_x))

    sigma_x = CELERITY * BASIN_SIGMA_MIN * 60
    for name, b in BASINS.items():
        xs = b["half_test"] - DX / 2
        stations = {f"sq_{a:04.1f}deg": (xs, xs * math.tan(math.radians(a)))
                    for a in BASIN_ANGLES}
        stations["sq_mid_00deg"] = (b["half_test"] / 2, 0.0)
        for variant in VARIANTS:
            half = b["half_ref"] if variant == "reference" else b["half_test"]
            seg = [(half, -half), (half, half), (-half, half), (-half, -half), (half, -half)]
            case = f"{name}_s{BASIN_SIGMA_MIN:02.0f}_{variant}"
            n = build_case(case, -half, half, -half, half, seg, stations, sigma_x,
                           b["t_stop"], variant, one_d=False)
            summary.append((case, n, sigma_x))

    write_runner([case for case, _, _ in summary])
    print(f"depth {DEPTH:.0f} m, celerity {CELERITY:.2f} m/s, cell {DX:.0f} m\n")
    for case, n, sx in summary:
        print(f"  {case:24s} {n:8d} cells   hump sigma {sx / 1e3:6.1f} km")
    print(f"\nwritten under {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

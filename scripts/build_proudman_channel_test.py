"""Build the synthetic test of a moving pressure disturbance in a channel.

The sweep of the long wave imposes an atmospheric pressure disturbance that
travels over the domain, and it relies on two properties of D-Flow FM that no
earlier run of the project has exercised. The first is that a pressure field
varying in space and time, read from a netCDF file and interpolated linearly
between snapshots, drives the sea surface as the linear theory of Proudman
resonance predicts. The second is that the weakly reflective boundary remains
transparent when the disturbance and the wave bound to it cross it together.

A Gaussian pressure rise, uniform across the channel, is switched on over a
fluid at rest and travels along a flat-bed channel at speed U. In the linear
frictionless limit the response has a closed form, with eta_s the static
(inverse barometer) response and Fr = U / sqrt(g h),

    eta(x, t) = eta_s(x - U t) / (1 - Fr^2)
              - eta_s(x - c t) / (2 (1 - Fr))
              - eta_s(x + c t) / (2 (1 + Fr)),

a forced wave travelling with the disturbance and two free waves released by
the start from rest. At Fr = 1 the forced wave and the forward free wave merge
into a wave that grows linearly with the distance travelled. Each Froude number
is run three times:

- in a reference channel long enough that no wall is reached, to be compared
  with the closed form;
- in a channel closed at the east by a Riemann boundary which the disturbance
  crosses, with no pressure correction at the boundary;
- in the same channel with the average pressure at the boundary, pavBnd, set to
  the background pressure, which makes FM apply its inverse barometer
  correction there.

Inside the common reach the test channels differ from the reference only by the
boundary, so the difference of the records at a station is the signal the
boundary returns.

The bed is flat at 150 m and the cell is 1500 m, as in the pulse test of the
open boundary, whose mesh and boundary writers are reused.

Usage:
    python build_proudman_channel_test.py
"""

from __future__ import annotations

import math
import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_riemann_pulse_test as rp  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "model" / "tests" / "proudman_channel"

G = rp.G
DEPTH = rp.DEPTH                # m
DX = rp.DX                      # m
RHO = 1025.0                    # kg m-3, rhomean of the run
CELERITY = math.sqrt(G * DEPTH)

P_BACKGROUND = 101325.0         # Pa
P_RISE = 200.0                  # Pa, 2 hPa, static response of 2.0 cm
SIGMA_X = CELERITY * 5 * 60.0   # m, a passage of 5 min standard deviation at Fr = 1
FROUDE = (0.6, 0.9, 1.0, 1.1)

WIDTH_CELLS = 3
X_WEST = -400.5e3               # closed wall, a whole number of cells from zero
X_EAST_TEST = 351e3             # Riemann boundary of the test channels
X_EAST_REF = 951e3              # closed wall of the reference
# Long enough for the slowest disturbance to cross the Riemann boundary.
T_STOP = 5.5 * 3600.0
STATIONS = {"x100km": 100.5e3, "x200km": 200.25e3, "x300km": 300.75e3,
            "bnd": X_EAST_TEST - DX / 2}

# Snapshots of the pressure field. Linear interpolation in time between two
# positions of a Gaussian displaced by d lowers its peak by about d^2/(8 s^2),
# 0.2 per cent for the largest displacement used here.
PRESSURE_DT = 30.0              # s

# Two settings of the run bear on the comparison. The pressure is updated at
# every computational step, Wind_eachstep = 1, since the default updates it at
# the user step and moves the disturbance in stairs. The step is limited to 5 s,
# a Courant number of 0.13, since at 15 s the implicit weighting of the time
# integration, teta0 = 0.55, lowers the resonant peak by 5 per cent over 300 km.
# The production mesh runs near 3.7 s on cells of 1920 m offshore, a Courant
# number of 0.07, so the smaller step is also the representative one.
VARIANTS = ("reference", "riemann", "riemann_pav")


def check_windows() -> None:
    """No reflection from a closed wall may reach a station within the window."""
    x_max = max(STATIONS.values())
    west = (2 * abs(X_WEST) + min(STATIONS.values())) / CELERITY
    east = (2 * X_EAST_REF - x_max) / CELERITY
    front = max(FROUDE) * CELERITY * T_STOP + 5 * SIGMA_X
    if min(west, east) < T_STOP:
        raise AssertionError(f"wall reflection arrives at {min(west, east) / 3600:.2f} h")
    if front > X_EAST_REF:
        raise AssertionError("the disturbance reaches the east wall of the reference")


def write_pressure(path: Path, speed: float, x_east: float) -> None:
    """Pressure snapshots on a cartesian grid covering the channel, CF netCDF."""
    import xarray as xr

    x = np.arange(X_WEST - DX, x_east + 1.5 * DX, DX)
    y = np.array([-2 * DX, WIDTH_CELLS * DX / 2, (WIDTH_CELLS + 2) * DX])
    t = np.arange(0.0, T_STOP + 2 * PRESSURE_DT, PRESSURE_DT)
    xi = x[None, :] - speed * t[:, None]
    p = P_BACKGROUND + P_RISE * np.exp(-xi ** 2 / (2 * SIGMA_X ** 2))
    field = np.repeat(p[:, None, :], y.size, axis=1)
    ds = xr.Dataset(
        {"air_pressure": (("time", "y", "x"), field,
                          dict(standard_name="air_pressure", long_name="air pressure",
                               units="Pa"))},
        coords={"time": ("time", t, dict(standard_name="time",
                                          units="seconds since 2026-01-01 00:00:00",
                                          calendar="proleptic_gregorian")),
                "y": ("y", y, dict(standard_name="projection_y_coordinate", units="m",
                                   axis="Y")),
                "x": ("x", x, dict(standard_name="projection_x_coordinate", units="m",
                                   axis="X"))})
    ds.to_netcdf(path, format="NETCDF3_64BIT",
                 encoding={v: {"_FillValue": None} for v in ("air_pressure", "time", "x", "y")})


def write_ext(path: Path, boundary: bool) -> None:
    with open(path, "w") as f:
        f.write("[General]\nfileVersion = 2.01\nfileType    = extForce\n\n")
        if boundary:
            f.write("[Boundary]\nquantity     = riemannbnd\n"
                    "locationFile = boundary.pli\nforcingFile  = boundary.bc\n\n")
        f.write("[Meteo]\nquantity            = airpressure\n"
                "forcingFile         = pressure.nc\n"
                "forcingVariableName = air_pressure\n"
                "forcingFileType     = netcdf\n"
                "interpolationMethod = linearSpaceTime\n"
                "operand             = O\n")


def write_mdu(path: Path, name: str, pav_bnd: float) -> None:
    text = f"""# Moving pressure disturbance in a channel, case {name}. Written by build_proudman_channel_test.py.
[General]
fileVersion           = 1.09
fileType              = modelDef
program               = D-Flow FM
autoStart             = 2
pathsRelativeToParent = 0

[Geometry]
netFile               = {name}_net.nc
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
rhomean               = {RHO}

[Wind]
rhoAir                = 1.2
pavBnd                = {pav_bnd:.1f}
pavIni                = 0.0
Wind_eachstep         = 1

[Time]
refDate               = 20260101
tUnit                 = S
dtUser                = 30.0
dtMax                 = 5.0
dtInit                = 1.0
tStart                = 0.0
tStop                 = {T_STOP:.1f}

[External Forcing]
extForceFile          =
extForceFileNew       = forcing.ext

[Output]
outputDir             = output
obsFile               = stations_obs.xyn
hisInterval           = 30.0
mapInterval           = 1800.0
rstInterval           = 0.0
wrimap_velocity_vector = 0
wrimap_upward_velocity_component = 0
"""
    path.write_text(text)


def case_name(froude: float, variant: str) -> str:
    return f"fr{froude * 100:03.0f}_{variant}"


def build_case(froude: float, variant: str) -> int:
    case = case_name(froude, variant)
    d = OUT / case
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    width = WIDTH_CELLS * DX
    x_east = X_EAST_REF if variant == "reference" else X_EAST_TEST
    ncells = rp.make_mesh(X_WEST, x_east, 0.0, width, d / f"{case}_net.nc")
    write_pressure(d / "pressure.nc", froude * CELERITY, x_east)
    rp.write_obs(d / "stations_obs.xyn", {k: (x, width / 2) for k, x in STATIONS.items()})
    if variant != "reference":
        seg = [(x_east, -DX / 4), (x_east, width + DX / 4)]
        rp.write_pli(d / "boundary.pli", "bnd", seg)
        rp.write_bc(d / "boundary.bc", "bnd", len(seg), "riemannbnd", T_STOP)
    write_ext(d / "forcing.ext", boundary=variant != "reference")
    write_mdu(d / f"{case}.mdu", case, P_BACKGROUND if variant == "riemann_pav" else 0.0)
    return ncells


def write_runner(cases) -> None:
    lines = ["@echo off", "rem Written by build_proudman_channel_test.py", 'cd /d "%~dp0"',
             f'set dflowfm="{rp.FM_LAUNCHER}"']
    for case in cases:
        lines += [f"pushd {case}",
                  f"call %dflowfm% --autostartstop {case}.mdu > run.log 2>&1",
                  f"echo {case} exit %ERRORLEVEL%", "popd"]
    (OUT / "run_all.bat").write_text("\r\n".join(lines) + "\r\n")


def main() -> int:
    check_windows()
    OUT.mkdir(parents=True, exist_ok=True)
    cases = []
    for froude in FROUDE:
        for variant in VARIANTS:
            n = build_case(froude, variant)
            cases.append((case_name(froude, variant), n))
    write_runner([c for c, _ in cases])
    print(f"depth {DEPTH:.0f} m, celerity {CELERITY:.2f} m/s, cell {DX:.0f} m")
    print(f"pressure rise {P_RISE:.0f} Pa, static response "
          f"{P_RISE / (RHO * G) * 100:.2f} cm, sigma {SIGMA_X / 1e3:.1f} km, "
          f"snapshots every {PRESSURE_DT:.0f} s\n")
    for case, n in cases:
        print(f"  {case:22s} {n:6d} cells")
    print(f"\nwritten under {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

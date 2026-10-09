"""Build the test of a pressure band crossing a basin bounded by Riemann boundaries.

The channel test of build_proudman_channel_test.py measures a disturbance that
is raised inside the domain and leaves through one boundary. In the sweep of
the long wave a disturbance of realistic size is wider than the model domain,
so it enters through one side, leaves through the opposite one and cuts the two
lateral sides for the whole of its passage. This test measures what a domain of
the size of domain B retains of the response in that arrangement.

A pressure band, Gaussian along its path and uniform across it, starts from
rest 150 km west of the centre of a square basin 90 km across, on a flat bed at
150 m, and travels east. On an unbounded sea the response is the closed form of
the channel test, since the band is uniform across its path. Each Froude
number is run twice:

- with Riemann boundaries on the west and east sides and closed walls on the
  north and south, which keeps the band uniform across the basin and isolates
  the loss of the wave generated outside the domain;
- with Riemann boundaries on all four sides, as in domain B, which adds the
  effect of the lateral boundaries.

Usage:
    python build_proudman_basin_test.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_proudman_channel_test as bp  # noqa: E402
import build_riemann_pulse_test as rp  # noqa: E402

OUT = bp.ROOT / "model" / "tests" / "proudman_basin"

DX = bp.DX
HALF = 45e3                     # m, half side of the basin, 30 cells
X_START = -150e3                # m, position of the band at the start
FROUDE = (0.6, 1.0)
T_STOP = 3.5 * 3600.0
VARIANTS = ("west_east", "four_sides")
STATIONS = {"centre": (0.0, 0.0), "north": (0.0, 30e3), "east": (30e3, 0.0),
            "west": (-30e3, 0.0)}


def write_pressure(path: Path, speed: float) -> None:
    """Snapshots of the band on a cartesian grid covering the basin, CF netCDF."""
    import xarray as xr

    x = np.arange(-HALF - 2 * DX, HALF + 2.5 * DX, DX)
    y = np.array([-HALF - 2 * DX, 0.0, HALF + 2 * DX])
    t = np.arange(0.0, T_STOP + 2 * bp.PRESSURE_DT, bp.PRESSURE_DT)
    xi = x[None, :] - X_START - speed * t[:, None]
    p = bp.P_BACKGROUND + bp.P_RISE * np.exp(-xi ** 2 / (2 * bp.SIGMA_X ** 2))
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


def write_ext(path: Path, boundaries) -> None:
    with open(path, "w") as f:
        f.write("[General]\nfileVersion = 2.01\nfileType    = extForce\n\n")
        for name in boundaries:
            f.write(f"[Boundary]\nquantity     = riemannbnd\n"
                    f"locationFile = {name}.pli\nforcingFile  = {name}.bc\n\n")
        f.write("[Meteo]\nquantity            = airpressure\n"
                "forcingFile         = pressure.nc\n"
                "forcingVariableName = air_pressure\n"
                "forcingFileType     = netcdf\n"
                "interpolationMethod = linearSpaceTime\n"
                "operand             = O\n")


def case_name(froude: float, variant: str) -> str:
    return f"fr{froude * 100:03.0f}_{variant}"


def build_case(froude: float, variant: str) -> int:
    case = case_name(froude, variant)
    d = OUT / case
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    ncells = rp.make_mesh(-HALF, HALF, -HALF, HALF, d / f"{case}_net.nc")
    write_pressure(d / "pressure.nc", froude * bp.CELERITY)
    rp.write_obs(d / "stations_obs.xyn", STATIONS)
    e = DX / 4
    if variant == "four_sides":
        # One polyline turning the corners, since FM reads the first polyline alone.
        parts = {"bnd": [(HALF, -HALF), (HALF, HALF), (-HALF, HALF), (-HALF, -HALF),
                         (HALF, -HALF)]}
    else:
        parts = {"west": [(-HALF, -HALF - e), (-HALF, HALF + e)],
                 "east": [(HALF, -HALF - e), (HALF, HALF + e)]}
    for name, seg in parts.items():
        rp.write_pli(d / f"{name}.pli", name, seg)
        rp.write_bc(d / f"{name}.bc", name, len(seg), "riemannbnd", T_STOP)
    write_ext(d / "forcing.ext", parts)
    bp.write_mdu(d / f"{case}.mdu", case, 0.0, T_STOP)
    return ncells


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    print(f"basin {2 * HALF / 1e3:.0f} km across, band starting {abs(X_START) / 1e3:.0f} km "
          f"west of the centre\n")
    for froude in FROUDE:
        for variant in VARIANTS:
            n = build_case(froude, variant)
            print(f"  {case_name(froude, variant):18s} {n:6d} cells")
    print(f"\nwritten under {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

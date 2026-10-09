"""Build and run one scenario of the long-wave sweep, a moving pressure disturbance.

A pressure rise of Gaussian shape, P_RISE at its centre, travels at constant
speed along a straight track through the Valletta harbours. Its standard
deviation is SIGMA_ALONG along the track and SIGMA_ACROSS across it. The track
begins TRACK_HALF upstream of the harbours and ends the same distance beyond
them, and the amplitude is raised from zero over RAMP at the beginning and
lowered over RAMP at the end, so that the disturbance exists inside the domain
alone and does not cross an open boundary at full amplitude, which the test of
docs/moving_pressure_channel_test.md shows to send a free wave back.

The run is two-dimensional and barotropic, with a Riemann boundary forced by
zero on the edge of the domain and no forcing other than the pressure. The
tide-generating potential, which D-Flow FM applies by default on a spherical
mesh, is switched off, since over the outer domain it raises the level by 1 to
2 cm within the run, the size of the static response to the pressure rise. The
pressure is written as snapshots on a geographic grid and read by D-Flow FM
with linear interpolation in space and time, updated at every computational
step. Stations are placed at the nearest cell centres whose nodes all lie
at least MIN_STATION_DEPTH below zero, so that each is wet on either mesh.

Usage:
    python build_longwave_scenario.py --mesh outer01 --heading 180 --speed 31
    python build_longwave_scenario.py --mesh v02 --heading 180 --speed 31

The heading is the direction of travel in degrees clockwise from north, so
180 is a disturbance arriving from the north.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
FM_LAUNCHER = (r"C:\Program Files\Deltares\Delft3D FM Suite 2026.01 HMWQ\plugins"
               r"\DeltaShell.Dimr\kernels\x64\bin\run_dflowfm.bat")
OUT = ROOT / "model" / "tests" / "longwave_pilot"

CRS = "EPSG:4326"
METRIC = "EPSG:32633"
G = 9.81
RHO = 1025.0
P_BACKGROUND = 101325.0         # Pa
P_RISE = 200.0                  # Pa
SIGMA_ALONG = 15e3              # m
SIGMA_ACROSS = 50e3             # m
TRACK_HALF = 200e3              # m, from the start of the track to the harbours
RAMP = 3600.0                   # s
T_AFTER = 3 * 3600.0            # s, simulated after the disturbance is lowered
TARGET = (14.5141, 35.9000)     # lon, lat, the track passes here
PRESSURE_DT = 60.0              # s
PRESSURE_DDEG = 0.04            # degrees
DT_MAX = 5.0                    # s, largest computational step
MIN_STATION_DEPTH = 1.0         # m

# Points of interest, lon and lat. Each station is the nearest cell centre.
POINTS = {
    "shelf_60km_up": None,                  # on the track, set from the heading
    "shelf_30km_up": None,
    "offshore_4km": (14.548, 35.925),
    "gh_mouth": (14.5225, 35.9010),
    "senglea": (14.5141, 35.8893),
    "french_creek": (14.5150, 35.8830),
    "dockyard_creek": (14.5215, 35.8855),
    "marsa_head": (14.4975, 35.8795),
    "mx_mouth": (14.5150, 35.9045),
    "sliema_creek": (14.4990, 35.9050),
    "msida_head": (14.4915, 35.8962),
    "pieta_head": (14.4985, 35.8935),
}


def track(heading_deg: float):
    """Unit vector of travel in UTM 33N and the position of the target."""
    from pyproj import Transformer

    tr = Transformer.from_crs(CRS, METRIC, always_xy=True)
    x, y = tr.transform(*TARGET)
    a = math.radians(heading_deg)
    return (x, y), (math.sin(a), math.cos(a))


def pressure_times(speed: float):
    t_track = 2 * TRACK_HALF / speed
    t_stop = math.ceil((t_track + T_AFTER) / 600.0) * 600.0
    return t_track, t_stop


def amplitude(t, t_track: float):
    """Raised cosine over RAMP at either end of the track, zero afterwards."""
    up = np.clip(t / RAMP, 0.0, 1.0)
    down = np.clip((t_track - t) / RAMP, 0.0, 1.0)
    return 0.25 * (1 - np.cos(np.pi * up)) * (1 - np.cos(np.pi * down))


def write_pressure(path: Path, bounds, heading: float, speed: float) -> float:
    import xarray as xr
    from pyproj import Transformer

    lon0, lat0, lon1, lat1 = bounds
    lon = np.arange(lon0 - PRESSURE_DDEG, lon1 + 2 * PRESSURE_DDEG, PRESSURE_DDEG)
    lat = np.arange(lat0 - PRESSURE_DDEG, lat1 + 2 * PRESSURE_DDEG, PRESSURE_DDEG)
    tr = Transformer.from_crs(CRS, METRIC, always_xy=True)
    LON, LAT = np.meshgrid(lon, lat)
    X, Y = tr.transform(LON, LAT)
    (xt, yt), (ex, ey) = track(heading)
    along = (X - xt) * ex + (Y - yt) * ey + TRACK_HALF
    across = -(X - xt) * ey + (Y - yt) * ex
    lateral = np.exp(-across ** 2 / (2 * SIGMA_ACROSS ** 2))
    t_track, t_stop = pressure_times(speed)
    t = np.arange(0.0, t_stop + 2 * PRESSURE_DT, PRESSURE_DT)
    amp = amplitude(t, t_track)
    field = np.empty((t.size, lat.size, lon.size), dtype="float32")
    for k, tk in enumerate(t):
        field[k] = P_BACKGROUND + P_RISE * amp[k] * lateral * np.exp(
            -(along - speed * tk) ** 2 / (2 * SIGMA_ALONG ** 2))
    ds = xr.Dataset(
        {"air_pressure": (("time", "latitude", "longitude"), field,
                          dict(standard_name="air_pressure", long_name="air pressure",
                               units="Pa"))},
        coords={"time": ("time", t, dict(standard_name="time",
                                          units="seconds since 2026-01-01 00:00:00",
                                          calendar="proleptic_gregorian")),
                "latitude": ("latitude", lat, dict(standard_name="latitude",
                                                   units="degrees_north", axis="Y")),
                "longitude": ("longitude", lon, dict(standard_name="longitude",
                                                     units="degrees_east", axis="X"))})
    ds.to_netcdf(path, format="NETCDF3_64BIT",
                 encoding={v: {"_FillValue": None}
                           for v in ("air_pressure", "time", "latitude", "longitude")})
    return t_stop


def stations(net: Path, heading: float):
    """Nearest cell centre to each point of interest, with the distance moved."""
    import xugrid as xu
    from pyproj import Transformer

    uds = xu.open_dataset(net)
    grid = uds.grid
    # A station is placed in a cell whose nodes all lie below MIN_STATION_DEPTH,
    # since the cells at the heads of Msida and Pieta Creeks carry bed levels
    # above zero where the 10 m grid has gaps, and a station there stays dry.
    node_z = uds["mesh2d_node_z"].values
    fn = grid.face_node_connectivity
    wet = np.array([node_z[row[row >= 0]].max() < -MIN_STATION_DEPTH for row in fn])
    tr = Transformer.from_crs(CRS, METRIC, always_xy=True)
    back = Transformer.from_crs(METRIC, CRS, always_xy=True)
    fx, fy = tr.transform(grid.face_x, grid.face_y)
    (xt, yt), (ex, ey) = track(heading)
    pts = dict(POINTS)
    for name, d in (("shelf_60km_up", 60e3), ("shelf_30km_up", 30e3)):
        pts[name] = back.transform(xt - d * ex, yt - d * ey)
    out = {}
    for name, (lon, lat) in pts.items():
        x, y = tr.transform(lon, lat)
        k = int(np.argmin(np.where(wet, (fx - x) ** 2 + (fy - y) ** 2, np.inf)))
        out[name] = (float(grid.face_x[k]), float(grid.face_y[k]),
                     float(math.hypot(fx[k] - x, fy[k] - y)))
    return out, grid.bounds


def write_case(mesh: str, heading: float, speed: float, dt_max: float = DT_MAX,
               tag: str = "", map_interval: float = 600.0) -> tuple[Path, str, float]:
    name = f"malta_{mesh}"
    src = ROOT / "data" / "processed" / f"mesh_{mesh}"
    case = f"{mesh}_h{heading:03.0f}_u{speed:02.0f}{tag}"
    d = OUT / case
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    shutil.copy(src / f"{name}_net.nc", d)
    shutil.copy(src / f"{name}_bnd.pli", d)
    st, bounds = stations(d / f"{name}_net.nc", heading)
    with open(d / "stations_obs.xyn", "w") as f:
        for key, (lon, lat, moved) in st.items():
            f.write(f"{lon:.6f} {lat:.6f} '{key}'\n")
            print(f"  station {key:15s} {lon:.4f} E {lat:.4f} N, {moved:6.0f} m from the point")
    t_stop = write_pressure(d / "pressure.nc", bounds, heading, speed)
    (d / "scenario.json").write_text(json.dumps(dict(
        mesh=mesh, heading=heading, speed=speed, rise=P_RISE, ramp=RAMP,
        track_half=TRACK_HALF, sigma_along=SIGMA_ALONG, sigma_across=SIGMA_ACROSS,
        t_track=2 * TRACK_HALF / speed, t_stop=t_stop, dt_max=dt_max), indent=2))

    npts = int((d / f"{name}_bnd.pli").read_text().splitlines()[1].split()[0])
    with open(d / f"{name}_bnd.bc", "w") as f:
        f.write("[General]\nfileVersion = 1.01\nfileType    = boundConds\n\n")
        for p in range(1, npts + 1):
            f.write(f"[Forcing]\nname              = {name}_bnd_{p:04d}\n"
                    "function          = timeseries\ntimeInterpolation = linear\n"
                    "quantity          = time\nunit              = seconds since 2026-01-01 00:00:00\n"
                    "quantity          = riemannbnd\nunit              = m\n"
                    f"0.0 0.0\n{t_stop + 3600:.1f} 0.0\n\n")
    (d / "forcing.ext").write_text(
        "[General]\nfileVersion = 2.01\nfileType    = extForce\n\n"
        f"[Boundary]\nquantity     = riemannbnd\nlocationFile = {name}_bnd.pli\n"
        f"forcingFile  = {name}_bnd.bc\n\n"
        "[Meteo]\nquantity            = airpressure\nforcingFile         = pressure.nc\n"
        "forcingVariableName = air_pressure\nforcingFileType     = netcdf\n"
        "interpolationMethod = linearSpaceTime\noperand             = O\n")
    (d / f"{case}.mdu").write_text(f"""# Long-wave scenario {case}, written by build_longwave_scenario.py.
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
angLat                = 36.0

[Numerics]
CFLMax                = 0.7
advecType             = 33
timeStepType          = 2
tlfSmo                = 0.0

[Physics]
unifFrictCoef         = 0.023
unifFrictType         = 1
ag                    = {G}
rhomean               = {RHO}
tidalForcing          = 0

[Wind]
rhoAir                = 1.2
pavBnd                = 0.0
pavIni                = 0.0
Wind_eachstep         = 1

[Time]
refDate               = 20260101
tUnit                 = S
dtUser                = 30.0
dtMax                 = {dt_max:.1f}
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
mapInterval           = {map_interval:.1f}
wrimap_velocity_vector = 0
wrimap_upward_velocity_component = 0
wrimap_taucurrent     = 0
wrimap_chezy          = 0
rstInterval           = 0.0
""")
    return d, case, t_stop


def run(d: Path, case: str) -> int:
    with open(d / "run.log", "w") as log:
        rc = subprocess.call(["cmd", "/c", FM_LAUNCHER, "--autostartstop", f"{case}.mdu"],
                             cwd=d, stdout=log, stderr=subprocess.STDOUT)
    dia = d / "output" / f"{case}.dia"
    text = dia.read_text(errors="replace") if dia.exists() else ""
    for line in text.splitlines():
        low = line.lower()
        if any(k in low for k in ("** error", "opened", "total time in timeloop",
                                  "nr of timesteps")):
            print("  " + line.strip())
    return rc


def main(argv=None) -> int:
    global P_RISE, RAMP, TRACK_HALF
    ap = argparse.ArgumentParser()
    ap.add_argument("--mesh", default="outer01", help="outer01, outer02 or v02")
    ap.add_argument("--heading", type=float, default=180.0,
                    help="direction of travel, degrees clockwise from north")
    ap.add_argument("--speed", type=float, default=31.0, help="m/s")
    ap.add_argument("--dt-max", type=float, default=DT_MAX,
                    help="largest computational step, s")
    ap.add_argument("--tag", default="", help="suffix of the case name")
    ap.add_argument("--map-interval", type=float, default=600.0, help="s")
    ap.add_argument("--rise", type=float, default=P_RISE, help="pressure rise, Pa")
    ap.add_argument("--ramp", type=float, default=RAMP, help="s")
    ap.add_argument("--track-half", type=float, default=TRACK_HALF, help="m")
    ap.add_argument("--no-run", action="store_true")
    args = ap.parse_args(argv)
    P_RISE, RAMP, TRACK_HALF = args.rise, args.ramp, args.track_half
    t_track, t_stop = pressure_times(args.speed)
    print(f"static response {P_RISE / (RHO * G) * 100:.2f} cm, track of "
          f"{2 * TRACK_HALF / 1e3:.0f} km in {t_track / 3600:.2f} h, run of {t_stop / 3600:.2f} h")
    d, case, t_stop = write_case(args.mesh, args.heading, args.speed, args.dt_max, args.tag,
                                 args.map_interval)
    print(f"written {d}")
    if args.no_run:
        return 0
    rc = run(d, case)
    print(f"exit {rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())

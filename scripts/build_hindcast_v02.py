"""Build and run a hindcast on mesh v02 forced by CMEMS and ERA5.

The open boundary is weakly reflective (Riemann), forced by the CMEMS sea
surface height of the analysis-forecast product at 15 minutes, which carries the
tide. The sea surface height is interpolated to the nodes of the boundary
polyline and shifted by one uniform offset, its mean over the run along the
boundary, since the CMEMS height is referred to the state of rest of NEMO and
the bathymetry to a surface near mean sea level, and no tide gauge records the
window to fix the relation between the two. In three dimensions salinity and
temperature enter at the boundary from the daily CMEMS reanalysis and the
initial three-dimensional fields are those of the first day, read through the
nudging file with iniWithNudge = 2, which initialises without nudging.

The surface is forced by hourly ERA5, wind at 10 m and mean sea level pressure,
and in three dimensions dew point, air temperature, cloud cover, net solar and
downward thermal radiation for the composite heat flux model. The boundary
velocity is not prescribed, since dfm_tools.cmems_nc_to_bc fails on the vector
quantity against hydrolib-core 1.0.

Stations are the points of build_longwave_scenario.py inside domain B,
together with the BLUE buoy, each in the nearest cell whose nodes all lie below
MIN_STATION_DEPTH.

Usage:
    python build_hindcast_v02.py --kmx 0 --start 2025-07-22 --stop 2025-07-24 --tag tf0
    python build_hindcast_v02.py --kmx 20 --start 2025-07-22 --stop 2025-08-01
"""

from __future__ import annotations

try:
    import pip_system_certs.wrapt_requests  # noqa: F401
except ImportError:
    pass

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_longwave_scenario as bl  # noqa: E402

ROOT = bl.ROOT
MESH_VERSION = "v03"
MESH = ROOT / "data" / "processed" / f"mesh_{MESH_VERSION}"
NAME = f"malta_{MESH_VERSION}"
CMEMS = ROOT / "data" / "raw" / "cmems_2025-07"
ERA5 = ROOT / "data" / "raw" / "era5_2025-07"
OUT = ROOT / "model" / "hindcast"
REFDATE = pd.Timestamp("2025-07-01")
BLUE = (14.5388, 35.9294)
DROP_POINTS = ("shelf_60km_up", "shelf_30km_up", "sicily_coast")

# ERA5 short name, FM quantity, needed in 2D
METEO = [
    ("u10", "windx", True), ("v10", "windy", True), ("msl", "airpressure", True),
    ("d2m", "dewpoint", False), ("t2m", "airtemperature", False),
    ("tcc", "cloudiness", False), ("ssr", "solarradiation", False),
    ("strd", "longwaveradiation", False),
]


def sec(t: pd.Timestamp) -> float:
    return (t - REFDATE).total_seconds()


def write_riemann(d: Path, start: pd.Timestamp, stop: pd.Timestamp, factor: float = 0.5) -> float:
    """Riemann boundary from the CMEMS sea surface height; returns the offset removed."""
    pts = np.loadtxt(d / f"{NAME}_bnd.pli", skiprows=2)
    ds = xr.open_dataset(next(CMEMS.glob("cmems_zos_*.nc")))
    zos = ds.zos.sel(time=slice(start - pd.Timedelta(hours=1), stop + pd.Timedelta(hours=1)))
    # fill the land cells of the 4.2 km grid along each row and column before interpolating
    zos = zos.interpolate_na("longitude", fill_value="extrapolate").interpolate_na(
        "latitude", fill_value="extrapolate")
    zb = zos.interp(longitude=xr.DataArray(pts[:, 0], dims="p"),
                    latitude=xr.DataArray(pts[:, 1], dims="p")).load()
    if np.isnan(zb.values).any():
        raise RuntimeError("sea surface height missing at boundary nodes")
    offset = float(zb.sel(time=slice(start, stop)).mean())
    zb = factor * (zb - offset)
    minutes = (pd.to_datetime(zb.time.values) - REFDATE).total_seconds() / 60.0
    with open(d / f"{NAME}_bnd.bc", "w") as f:
        f.write("[General]\nfileVersion = 1.01\nfileType    = boundConds\n\n")
        for p in range(pts.shape[0]):
            f.write(f"[Forcing]\nname              = {NAME}_bnd_{p + 1:04d}\n"
                    "function          = timeseries\ntimeInterpolation = linear\n"
                    "quantity          = time\n"
                    f"unit              = minutes since {REFDATE:%Y-%m-%d %H:%M:%S}\n"
                    "quantity          = riemannbnd\nunit              = m\n")
            for t, v in zip(minutes, zb.values[:, p]):
                f.write(f"{t:.1f} {v:.4f}\n")
            f.write("\n")
    return offset


def write_ts_boundary(d: Path, start: pd.Timestamp, stop: pd.Timestamp) -> list[str]:
    """Salinity and temperature at the boundary through dfm_tools; returns ext blocks."""
    import dfm_tools as dfmt
    import hydrolib.core.dflowfm as hcdfm

    ext = hcdfm.ExtModel()
    dfmt.cmems_nc_to_bc(ext_new=ext, list_quantities=["salinitybnd", "temperaturebnd"],
                        tstart=start.floor("D"), tstop=stop.ceil("D"),
                        file_pli=str(d / f"{NAME}_bnd.pli"),
                        dir_pattern=str(CMEMS / "cmems_{ncvarname}_*.nc"), dir_output=str(d),
                        refdate_str=f"minutes since {REFDATE:%Y-%m-%d %H:%M:%S} +00:00")
    blocks = []
    for quantity in ("salinitybnd", "temperaturebnd"):
        bc = next(d.glob(f"{quantity}_*.bc"))
        if "nan" in bc.read_text().lower():
            raise RuntimeError(f"missing values in {bc.name}")
        blocks.append(f"[Boundary]\nquantity     = {quantity}\n"
                      f"locationFile = {NAME}_bnd.pli\nforcingFile  = {bc.name}\n")
    return blocks


def write_initial_ts(d: Path, start: pd.Timestamp) -> str:
    """Three-dimensional initial salinity and temperature, as in dfmt.cmems_nc_to_ini."""
    from dfm_tools.xarray_helpers import interpolate_na_multidim

    so = xr.open_dataset(next(CMEMS.glob("cmems_so_*.nc")))
    th = xr.open_dataset(next(CMEMS.glob("cmems_thetao_*.nc")))
    ds = so[["so"]].assign(thetao=th["thetao"])
    t0 = ds.time.sel(time=start, method="pad").values
    ds = ds.sel(time=slice(t0, None)).isel(time=slice(0, 2))
    for v in ds.data_vars:
        ds[v] = interpolate_na_multidim(ds[v], ["depth"])
        ds[v] = interpolate_na_multidim(ds[v], ["latitude", "longitude"])
    name = f"nudge_salinity_temperature_{start:%Y-%m-%d}.nc"
    ds.to_netcdf(d / name)
    return ("QUANTITY=nudge_salinity_temperature\n"
            f"FILENAME={name}\nFILETYPE=11\nMETHOD=3\nOPERAND=O\n")


def write_meteo(d: Path, start: pd.Timestamp, stop: pd.Timestamp, three_d: bool) -> list[str]:
    blocks = []
    window = slice(start - pd.Timedelta(hours=2), stop + pd.Timedelta(hours=2))
    for key, quantity, in_2d in METEO:
        if not (in_2d or three_d):
            continue
        files = sorted(ERA5.glob(f"era5_{key}_*.nc"))
        if not files:
            raise FileNotFoundError(f"no ERA5 file for {key}")
        ds = xr.open_mfdataset(files, combine="by_coords") if len(files) > 1 else xr.open_dataset(files[0])
        if "valid_time" in ds.dims:
            ds = ds.rename(valid_time="time")
        ds = ds.drop_vars([c for c in ("number", "expver") if c in ds.variables])
        ds = ds.sel(time=window).sortby("latitude")
        da = ds[key].load()
        if key in ("d2m", "t2m"):
            da, units = da - 273.15, "C"
        elif key == "tcc":
            da, units = da * 100.0, "%"
        elif key in ("ssr", "strd"):
            # hourly accumulation to a mean flux; net solar raised by the 6 per
            # cent that D-Flow FM subtracts for reflection, as dfm_tools does
            da, units = da / 3600.0, "W m-2"
            if key == "ssr":
                da = da / 0.94
        else:
            units = da.attrs.get("units", "")
        da.attrs = dict(long_name=ds[key].attrs.get("long_name", key), units=units)
        out = xr.Dataset({key: da.astype("float32")})
        out["time"].attrs.update(standard_name="time")
        out["latitude"].attrs.update(standard_name="latitude", units="degrees_north", axis="Y")
        out["longitude"].attrs.update(standard_name="longitude", units="degrees_east", axis="X")
        name = f"era5_{key}.nc"
        out.to_netcdf(d / name, encoding={"time": {"units": f"hours since {REFDATE:%Y-%m-%d %H:%M:%S}"},
                                          key: {"_FillValue": None}})
        blocks.append(f"[Meteo]\nquantity            = {quantity}\nforcingFile         = {name}\n"
                      f"forcingVariableName = {key}\nforcingFileType     = netcdf\n"
                      "interpolationMethod = linearSpaceTime\noperand             = O\n")
    return blocks


def write_stations(d: Path) -> dict:
    # stations() also places the two points on the track of a heading, dropped here
    saved = dict(bl.POINTS)
    bl.POINTS = {"blue_buoy": BLUE, **saved}
    try:
        st, _ = bl.stations(d / f"{NAME}_net.nc", 0.0)
    finally:
        bl.POINTS = saved
    for k in DROP_POINTS:
        st.pop(k, None)
    with open(d / "stations_obs.xyn", "w") as f:
        for key, (lon, lat, moved) in st.items():
            f.write(f"{lon:.6f} {lat:.6f} '{key}'\n")
            print(f"  station {key:15s} {lon:.4f} E {lat:.4f} N, {moved:6.0f} m from the point")
    return st


def write_mdu(d: Path, case: str, args, start, stop, three_d: bool, ext_old: bool) -> None:
    physics_3d = f"""salinity              = 1
temperature           = 5
iniWithNudge          = 2
backgroundSalinity    = 38.0
backgroundWaterTemperature = 25.0
secchiDepth           = {args.secchi:.1f}
idensform             = 2
""" if three_d else "salinity              = 0\ntemperature           = 0\n"
    numerics_3d = """turbulenceModel       = 3
turbulenceAdvection   = 3
vertAdvTypSal         = 4
vertAdvTypTem         = 4
""" if three_d else ""
    (d / f"{case}.mdu").write_text(f"""# Hindcast {case}, written by build_hindcast_v02.py.
[General]
fileVersion           = 1.09
fileType              = modelDef
program               = D-Flow FM
autoStart             = 2
pathsRelativeToParent = 0

[Geometry]
netFile               = {NAME}_net.nc
bedLevType            = 3
waterLevIni           = 0.0
kmx                   = {args.kmx}
layerType             = 1
angLat                = 36.0
angLon                = 14.5

[Numerics]
CFLMax                = 0.7
advecType             = 33
timeStepType          = 2
tlfSmo                = {args.tlfsmo:.1f}
{numerics_3d}
[Physics]
unifFrictCoef         = 0.023
unifFrictType         = 1
vicouv                = 0.1
dicouv                = 0.1
smagorinsky           = 0.2
rhomean               = 1025.0
ag                    = 9.81
tidalForcing          = {args.tidal_forcing}
{physics_3d}
[Wind]
iCdTyp                = 2
CdBreakpoints         = 0.00063 0.00723
windSpeedBreakpoints  = 0.0 100.0
rhoAir                = 1.2
pavBnd                = {args.pavbnd:.1f}
pavIni                = 0.0
Wind_eachstep         = 1

[Time]
refDate               = {REFDATE:%Y%m%d}
tUnit                 = S
dtUser                = 60.0
dtMax                 = {args.dt_max:.1f}
dtInit                = 1.0
tStart                = {sec(start):.1f}
tStop                 = {sec(stop):.1f}

[External Forcing]
extForceFile          = {"initial.ext" if ext_old else ""}
extForceFileNew       = forcing.ext

[Output]
outputDir             = output
obsFile               = stations_obs.xyn
hisInterval           = 60.0
mapInterval           = {args.map_interval:.1f}
wrimap_velocity_vector = 1
wrimap_upward_velocity_component = 0
wrimap_taucurrent     = 0
wrimap_chezy          = 0
# Fields on the edges and of turbulence make two thirds of a three-dimensional
# map and are not used by the analysis or the portal
wrimap_velocity_component_u0 = 0
wrimap_velocity_component_u1 = 0
wrimap_flow_flux_q1   = 0
wrimap_horizontal_viscosity_viu = 0
wrimap_horizontal_diffusivity_diu = 0
wrimap_turbulence     = 0
wrimap_velocity_magnitude = 0
wrimap_waterlevel_s0  = 0
wrimap_numlimdt       = 0
rstInterval           = 0.0
""")


def main(argv=None) -> int:
    global MESH_VERSION, MESH, NAME
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mesh", default=MESH_VERSION, help="v02 or v03")
    ap.add_argument("--kmx", type=int, default=0, help="number of sigma layers, 0 for 2D")
    ap.add_argument("--start", default="2025-07-22")
    ap.add_argument("--stop", default="2025-07-24")
    ap.add_argument("--tag", default="")
    ap.add_argument("--tidal-forcing", type=int, default=0)
    ap.add_argument("--riemann-factor", type=float, default=0.5,
                    help="factor on the CMEMS height prescribed as the incoming Riemann signal")
    ap.add_argument("--pavbnd", type=float, default=0.0,
                    help="reference pressure at the boundary, Pa, 0 for none")
    ap.add_argument("--tlfsmo", type=float, default=3600.0,
                    help="smoothing time of the boundary signal at the start, s")
    ap.add_argument("--dt-max", type=float, default=30.0)
    ap.add_argument("--map-interval", type=float, default=3600.0)
    ap.add_argument("--secchi", type=float, default=10.0, help="working value, m")
    ap.add_argument("--parallel", type=int, default=1, help="number of MPI domains")
    ap.add_argument("--no-run", action="store_true")
    args = ap.parse_args(argv)
    MESH_VERSION = args.mesh
    MESH = ROOT / "data" / "processed" / f"mesh_{MESH_VERSION}"
    NAME = f"malta_{MESH_VERSION}"

    start, stop = pd.Timestamp(args.start), pd.Timestamp(args.stop)
    three_d = args.kmx > 0
    case = f"{MESH_VERSION}_{'3d' if three_d else '2d'}{args.kmx if three_d else ''}_{start:%m%d}_{stop:%m%d}{args.tag}"
    d = OUT / case
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    for f in (f"{NAME}_net.nc", f"{NAME}_bnd.pli"):
        shutil.copy(MESH / f, d)

    offset = write_riemann(d, start, stop, args.riemann_factor)
    print(f"Riemann boundary from CMEMS zos, offset removed {offset:+.3f} m")
    blocks = [f"[Boundary]\nquantity     = riemannbnd\nlocationFile = {NAME}_bnd.pli\n"
              f"forcingFile  = {NAME}_bnd.bc\n"]
    if three_d:
        blocks += write_ts_boundary(d, start, stop)
        (d / "initial.ext").write_text(write_initial_ts(d, start))
    blocks += write_meteo(d, start, stop, three_d)
    (d / "forcing.ext").write_text("[General]\nfileVersion = 2.01\nfileType    = extForce\n\n"
                                   + "\n".join(blocks))
    st = write_stations(d)
    write_mdu(d, case, args, start, stop, three_d, three_d)
    (d / "case.json").write_text(json.dumps(dict(
        case=case, start=str(start), stop=str(stop), kmx=args.kmx, zos_offset=offset,
        tidal_forcing=args.tidal_forcing, pavbnd=args.pavbnd, riemann_factor=args.riemann_factor,
        refdate=str(REFDATE),
        stations={k: v[:2] for k, v in st.items()}), indent=2))
    print(f"written {d}")
    if args.no_run:
        return 0
    rc = run_parallel(d, case, args.parallel) if args.parallel > 1 else bl.run(d, case)
    print(f"exit {rc}")
    return rc


def run_parallel(d: Path, case: str, n: int) -> int:
    """Partition the mesh into n domains and run them through DIMR under MPI."""
    bindir = Path(bl.FM_LAUNCHER).parent
    with open(d / "run.log", "w") as log:
        rc = subprocess.call(["cmd", "/c", str(bindir / "run_dflowfm.bat"),
                              f"--partition:ndomains={n}:icgsolver=6", f"{case}.mdu"],
                             cwd=d, stdout=log, stderr=subprocess.STDOUT)
        if rc:
            return rc
        procs = " ".join(str(k) for k in range(n))
        (d / "dimr_config.xml").write_text(f"""<?xml version="1.0" encoding="utf-8"?>
<dimrConfig xmlns="http://schemas.deltares.nl/dimr">
  <documentation><fileVersion>1.3</fileVersion><createdBy>build_hindcast_v02.py</createdBy></documentation>
  <control><start name="DFlowFM"/></control>
  <component name="DFlowFM">
    <library>dflowfm</library>
    <process>{procs}</process>
    <workingDir>.</workingDir>
    <inputFile>{case}.mdu</inputFile>
    <mpiCommunicator>DFM_COMM_DFMWORLD</mpiCommunicator>
  </component>
</dimrConfig>
""")
        rc = subprocess.call(["cmd", "/c", str(bindir / "run_dimr_parallel.bat"), str(n),
                              "dimr_config.xml"], cwd=d, stdout=log, stderr=subprocess.STDOUT)
    for dia in sorted((d / "output").glob(f"{case}_0000.dia")):
        for line in dia.read_text(errors="replace").splitlines():
            if any(k in line.lower() for k in ("** error", "total time in timeloop",
                                               "average timestep")):
                print("  " + line.strip())
    return rc


if __name__ == "__main__":
    sys.exit(main())

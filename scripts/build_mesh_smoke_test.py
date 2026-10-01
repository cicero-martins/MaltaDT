"""Minimal D-Flow FM run on a mesh, to establish that FM accepts it.

FM 2026.01 rejected the StagnoneDT v05 mesh at initialisation as not
orthogonal although every topological check passed, so a mesh is not taken
as valid until FM has initialised and stepped on it. The run is two hours of
still water, two-dimensional, with a Riemann boundary forced by zero on the
domain rectangle and no other forcing. A sound mesh returns a water level that
stays near zero, and the diagnostic file reports the number of open boundary
cells and any rejection.

Usage:
    python build_mesh_smoke_test.py --version v02
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FM_LAUNCHER = (r"C:\Program Files\Deltares\Delft3D FM Suite 2026.01 HMWQ\plugins"
               r"\DeltaShell.Dimr\kernels\x64\bin\run_dflowfm.bat")
T_STOP = 7200.0
T_STOP_FORCED = 6 * 3600.0
FORCED_AMPLITUDE_M = 0.15
FORCED_PERIOD_S = 25 * 60.0


def forcing_rows(forced: bool, t_stop: float) -> str:
    """Riemann signal, zero, or a long wave of FORCED_AMPLITUDE_M at FORCED_PERIOD_S.

    The forced case drives the harbours near their own mode, so that the
    currents in the narrow channels, which set the advective time step, are
    those of a strong seiche rather than of still water.
    """
    import math

    if not forced:
        return f"0.0 0.0\n{t_stop + 3600:.1f} 0.0\n"
    rows = []
    for k in range(int((t_stop + 3600) / 60) + 1):
        t = 60.0 * k
        ramp = min(1.0, t / 3600.0)
        rows.append(f"{t:.1f} {FORCED_AMPLITUDE_M * ramp * math.sin(2 * math.pi * t / FORCED_PERIOD_S):.5f}")
    return "\n".join(rows) + "\n"


def split_east(pts):
    """Split the closed domain polyline into its eastern side and the other three.

    The polyline of build_mesh_v02.py starts at the south-east corner and runs
    north along the eastern side, so that side is the leading run of points
    sharing the largest UTM easting.
    """
    from pyproj import Transformer

    tr = Transformer.from_crs("EPSG:4326", "EPSG:32633", always_xy=True)
    x, _ = tr.transform([p[0] for p in pts], [p[1] for p in pts])
    xmax = max(x)
    k = 0
    while k < len(pts) and x[k] > xmax - 1.0:
        k += 1
    east = pts[:k]
    rest = pts[k + 1:-2]
    return east, rest


def write_case(version: str, forced: bool = False) -> Path:
    name = f"malta_{version}"
    src = ROOT / "data" / "processed" / f"mesh_{version}"
    d = ROOT / "model" / "tests" / f"mesh_{version}_{'forced' if forced else 'smoke'}"
    t_stop = T_STOP_FORCED if forced else T_STOP
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    shutil.copy(src / f"{name}_net.nc", d)
    lines = (src / f"{name}_bnd.pli").read_text().splitlines()
    pts = [tuple(map(float, ln.split()[:2])) for ln in lines[2:] if ln.strip()]
    if forced:
        # The long wave enters through the eastern side only, as in the event of
        # June 2019 reported from the east. The other three sides absorb with a
        # zero signal. FM reads one polyline per file, so the two parts are
        # written to separate files, each stopping one point short of the
        # shared corners so that no cell is claimed twice.
        east, rest = split_east(pts)
        parts = [("east", east, True), ("rest", rest, False)]
    else:
        parts = [("bnd", pts, False)]
    ext = "[General]\nfileVersion = 2.01\nfileType    = extForce\n\n"
    for label, ppts, wave in parts:
        pname = f"{name}_{label}"
        with open(d / f"{pname}.pli", "w") as f:
            f.write(f"{pname}\n    {len(ppts)}    2\n")
            f.writelines(f"{x:.6f} {y:.6f}\n" for x, y in ppts)
        with open(d / f"{pname}.bc", "w") as f:
            f.write("[General]\nfileVersion = 1.01\nfileType    = boundConds\n\n")
            for p in range(1, len(ppts) + 1):
                f.write(f"[Forcing]\nname              = {pname}_{p:04d}\n"
                        "function          = timeseries\ntimeInterpolation = linear\n"
                        "quantity          = time\nunit              = seconds since 2026-01-01 00:00:00\n"
                        "quantity          = riemannbnd\nunit              = m\n"
                        + forcing_rows(wave, t_stop) + "\n")
        ext += (f"[Boundary]\nquantity     = riemannbnd\nlocationFile = {pname}.pli\n"
                f"forcingFile  = {pname}.bc\n\n")
    (d / "forcing.ext").write_text(ext)
    (d / f"{name}.mdu").write_text(f"""# Mesh smoke test, written by build_mesh_smoke_test.py.
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
ag                    = 9.81
rhomean               = 1025.0

[Time]
refDate               = 20260101
tUnit                 = S
dtUser                = 60.0
dtMax                 = {60.0 if forced else 30.0}
dtInit                = 1.0
tStart                = 0.0
tStop                 = {t_stop:.1f}

[External Forcing]
extForceFile          =
extForceFileNew       = forcing.ext

[Output]
outputDir             = output
hisInterval           = 0.0
mapInterval           = {600.0 if forced else 3600.0}
rstInterval           = 0.0
""")
    return d


def run(d: Path, version: str) -> int:
    name = f"malta_{version}"
    with open(d / "run.log", "w") as log:
        rc = subprocess.call(["cmd", "/c", FM_LAUNCHER, "--autostartstop", f"{name}.mdu"],
                             cwd=d, stdout=log, stderr=subprocess.STDOUT)
    dia = d / "output" / f"{name}.dia"
    text = dia.read_text(errors="replace") if dia.exists() else (d / "run.log").read_text(errors="replace")
    keys = ("ERROR", "not orthogonal", "opened", "nr of open bndcells", "simulation period",
            "total time in timeloop", "Computation finished", "timesteps")
    for line in text.splitlines():
        if any(k.lower() in line.lower() for k in keys):
            print(line.strip())
    return rc


def cost_summary(d: Path, version: str, t_stop: float) -> None:
    """Mean time step and wall time per step and per simulated day, from the .dia."""
    import re

    text = (d / "output" / f"malta_{version}.dia").read_text(errors="replace")
    steps = float(re.findall(r"nr of timesteps\s+\(\s*\)\s*:\s*([\d.]+)", text)[-1])
    loop_h = float(re.findall(r"total time in timeloop \(h\)\s*:\s*([\d.]+)", text)[-1])
    wall = loop_h * 3600.0
    print(f"mean time step {t_stop / steps:.1f} s over {steps:.0f} steps, "
          f"{wall / steps * 1e3:.1f} ms per step, "
          f"{wall / (t_stop / 86400):.0f} s of wall time per simulated day, serial")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v02")
    ap.add_argument("--forced", action="store_true",
                    help="drive the harbours near their mode, to measure the time step")
    args = ap.parse_args(argv)
    d = write_case(args.version, args.forced)
    t_stop = T_STOP_FORCED if args.forced else T_STOP
    rc = run(d, args.version)
    out = d / "output" / f"malta_{args.version}_map.nc"
    if out.exists():
        import xarray as xr
        ds = xr.open_dataset(out)
        s1 = ds["mesh2d_s1"]
        print(f"water level over the run: min {float(s1.min()):+.4f} m, "
              f"max {float(s1.max()):+.4f} m, map times {s1.sizes['time']}")
        if "mesh2d_ucmag" in ds:
            import numpy as np
            u = np.nanmax(ds["mesh2d_ucmag"].values, axis=0)
            s = np.nanmax(np.abs(s1.values), axis=0)
            print(f"speed, maximum over time per face: p50 {np.nanpercentile(u, 50):.3f}, "
                  f"p99 {np.nanpercentile(u, 99):.3f}, max {np.nanmax(u):.2f} m/s")
            print(f"|level|, maximum over time per face: p50 {np.nanpercentile(s, 50):.3f}, "
                  f"p99 {np.nanpercentile(s, 99):.3f}, max {np.nanmax(s):.2f} m")
        cost_summary(d, args.version, t_stop)
    print(f"exit {rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())

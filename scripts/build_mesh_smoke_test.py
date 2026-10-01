"""Minimal D-Flow FM run on a mesh, to establish that FM accepts it.

FM 2026.01 rejected the StagnoneDT v05 mesh at initialisation as not
orthogonal although every topological check passed, so a mesh is not taken
as valid until FM has initialised and stepped on it. The run is two hours of
still water, two-dimensional, with a Riemann boundary forced by zero on the
domain rectangle and no other forcing. A sound mesh returns a water level that
stays near zero, and the diagnostic file reports the number of open boundary
cells and any rejection.

Usage:
    python build_mesh_smoke_test.py --version v01
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


def write_case(version: str) -> Path:
    name = f"malta_{version}"
    src = ROOT / "data" / "processed" / f"mesh_{version}"
    d = ROOT / "model" / "tests" / f"mesh_{version}_smoke"
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    shutil.copy(src / f"{name}_net.nc", d)
    shutil.copy(src / f"{name}_bnd.pli", d)
    npts = int((d / f"{name}_bnd.pli").read_text().splitlines()[1].split()[0])
    with open(d / "boundary.bc", "w") as f:
        f.write("[General]\nfileVersion = 1.01\nfileType    = boundConds\n\n")
        for p in range(1, npts + 1):
            f.write(f"[Forcing]\nname              = {name}_bnd_{p:04d}\n"
                    "function          = timeseries\ntimeInterpolation = linear\n"
                    "quantity          = time\nunit              = seconds since 2026-01-01 00:00:00\n"
                    "quantity          = riemannbnd\nunit              = m\n"
                    f"0.0 0.0\n{T_STOP + 3600:.1f} 0.0\n\n")
    (d / "forcing.ext").write_text(
        "[General]\nfileVersion = 2.01\nfileType    = extForce\n\n"
        f"[Boundary]\nquantity     = riemannbnd\nlocationFile = {name}_bnd.pli\n"
        "forcingFile  = boundary.bc\n")
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
dtMax                 = 30.0
dtInit                = 1.0
tStart                = 0.0
tStop                 = {T_STOP:.1f}

[External Forcing]
extForceFile          =
extForceFileNew       = forcing.ext

[Output]
outputDir             = output
hisInterval           = 0.0
mapInterval           = 3600.0
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", default="v01")
    args = ap.parse_args(argv)
    d = write_case(args.version)
    rc = run(d, args.version)
    out = d / "output" / f"malta_{args.version}_map.nc"
    if out.exists():
        import xarray as xr
        ds = xr.open_dataset(out)
        s1 = ds["mesh2d_s1"]
        print(f"water level over the run: min {float(s1.min()):+.4f} m, "
              f"max {float(s1.max()):+.4f} m, map times {s1.sizes['time']}")
    print(f"exit {rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())

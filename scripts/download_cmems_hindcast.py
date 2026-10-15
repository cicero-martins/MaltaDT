"""Download the CMEMS Mediterranean fields forcing a hindcast on domain B.

Sea surface height comes from the analysis-forecast product at 15 minutes,
which carries the tide (FES2014, eight constituents). Currents, salinity and
temperature come from the reanalysis at daily resolution, since the
three-dimensional analysis-forecast fields begin in October 2025. Dataset
identifiers and the split between the two products follow the StagnoneDT
hindcasts of July 2025.

Credentials are read from the .env of the StagnoneDT repository and are not
printed. Each variable is written to its own file, cmems_<var>_<start>_<end>.nc,
the naming that dfm_tools.cmems_nc_to_bc expects.

Usage:
    python download_cmems_hindcast.py --start 2025-07-21 --end 2025-08-02 \\
        --out data/raw/cmems_2025-07
"""

from __future__ import annotations

try:
    import pip_system_certs.wrapt_requests  # noqa: F401
except ImportError:
    pass

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT.parent / "StagnoneDT" / ".env"

# Domain B (14.05-15.00 E, 35.70-36.30 N) with a margin of more than one cell of 4.2 km
BOX = (13.90, 35.55, 15.15, 36.45)

DATASETS = [
    ("cmems_mod_med_phy-ssh_anfc_4.2km_PT15M-i", "zos"),
    ("cmems_mod_med_phy-cur_my_4.2km_P1D-m", "uo"),
    ("cmems_mod_med_phy-cur_my_4.2km_P1D-m", "vo"),
    ("cmems_mod_med_phy-sal_my_4.2km_P1D-m", "so"),
    ("cmems_mod_med_phy-temp_my_4.2km_P1D-m", "thetao"),
]


def load_env(path: Path) -> None:
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "raw" / "cmems_2025-07")
    ap.add_argument("--box", type=float, nargs=4, default=BOX,
                    metavar=("LON0", "LAT0", "LON1", "LAT1"))
    args = ap.parse_args()

    load_env(ENV)
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    import copernicusmarine

    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    lon0, lat0, lon1, lat1 = args.box
    for dataset, var in DATASETS:
        name = f"cmems_{var}_{args.start}_{args.end}.nc"
        if (out / name).exists():
            print(f"  {name} present, skipped")
            continue
        print(f"  {dataset} {var} -> {name}", flush=True)
        copernicusmarine.subset(
            dataset_id=dataset, variables=[var],
            start_datetime=f"{args.start}T00:00:00", end_datetime=f"{args.end}T00:00:00",
            minimum_longitude=lon0, maximum_longitude=lon1,
            minimum_latitude=lat0, maximum_latitude=lat1,
            output_directory=str(out), output_filename=name,
            username=os.environ["CMEMS_USERNAME"], password=os.environ["CMEMS_PASSWORD"],
        )
        print(f"    {(out / name).stat().st_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())

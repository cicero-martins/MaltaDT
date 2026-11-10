"""Download the CMEMS Mediterranean fields forcing a hindcast on domain B.

Sea surface height comes from the analysis-forecast product at 15 minutes,
which carries the tide (FES2014, eight constituents). Currents, salinity and
temperature are daily means, from the reanalysis (--product my) for windows
before October 2025, where the three-dimensional analysis-forecast fields do
not exist, and from the analysis-forecast product (--product anfc) in 2026,
which the reanalysis does not reach. Dataset identifiers and the split between
the two products follow the StagnoneDT hindcasts of July 2025. With
--surface-hourly the hourly surface currents of the analysis-forecast product
are added, the reference field against which the drifter tracks are scored,
and with --waves-hourly the hourly surface Stokes drift and the bulk wave
parameters of the Mediterranean wave analysis-forecast product.

Credentials are read from the .env of the StagnoneDT repository and are not
printed. Each variable is written to its own file, cmems_<var>_<start>_<end>.nc,
the naming that dfm_tools.cmems_nc_to_bc expects.

Usage:
    python download_cmems_hindcast.py --start 2025-07-21 --end 2025-08-02 \\
        --out data/raw/cmems_2025-07
    python download_cmems_hindcast.py --start 2026-05-16 --end 2026-05-23 \\
        --out data/raw/cmems_2026-05 --product anfc --surface-hourly
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

DATASETS = {
    "my": [
        ("cmems_mod_med_phy-ssh_anfc_4.2km_PT15M-i", "zos"),
        ("cmems_mod_med_phy-cur_my_4.2km_P1D-m", "uo"),
        ("cmems_mod_med_phy-cur_my_4.2km_P1D-m", "vo"),
        ("cmems_mod_med_phy-sal_my_4.2km_P1D-m", "so"),
        ("cmems_mod_med_phy-temp_my_4.2km_P1D-m", "thetao"),
    ],
    # temperature is "tem" in the analysis-forecast identifiers and "temp" in the reanalysis
    "anfc": [
        ("cmems_mod_med_phy-ssh_anfc_4.2km_PT15M-i", "zos"),
        ("cmems_mod_med_phy-cur_anfc_4.2km_P1D-m", "uo"),
        ("cmems_mod_med_phy-cur_anfc_4.2km_P1D-m", "vo"),
        ("cmems_mod_med_phy-sal_anfc_4.2km_P1D-m", "so"),
        ("cmems_mod_med_phy-tem_anfc_4.2km_P1D-m", "thetao"),
    ],
}
# hourly surface currents, written under a prefix the forcing chain does not read
SURFACE_HOURLY = ("cmems_mod_med_phy-cur_anfc_4.2km-2D_PT1H-m", ("uo", "vo"), "cmems-surface-1h")
# hourly surface Stokes drift and bulk wave parameters (MEDSEA_ANALYSISFORECAST_WAV_006_017)
WAVES_HOURLY = ("cmems_mod_med_wav_anfc_4.2km_PT1H-i",
                ("VSDX", "VSDY", "VHM0", "VTPK", "VMDR"), "cmems-waves-1h")


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
    ap.add_argument("--product", choices=tuple(DATASETS), default="my",
                    help="source of the daily three-dimensional fields")
    ap.add_argument("--surface-hourly", action="store_true",
                    help="add the hourly surface currents of the analysis-forecast product")
    ap.add_argument("--waves-hourly", action="store_true",
                    help="add the hourly Stokes drift and wave parameters of the wave product")
    args = ap.parse_args()

    load_env(ENV)
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    import copernicusmarine

    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    lon0, lat0, lon1, lat1 = args.box
    requests = [(dataset, [var], f"cmems_{var}_{args.start}_{args.end}.nc")
                for dataset, var in DATASETS[args.product]]
    if args.surface_hourly:
        dataset, variables, prefix = SURFACE_HOURLY
        requests.append((dataset, list(variables), f"{prefix}_{args.start}_{args.end}.nc"))
    if args.waves_hourly:
        dataset, variables, prefix = WAVES_HOURLY
        requests.append((dataset, list(variables), f"{prefix}_{args.start}_{args.end}.nc"))
    for dataset, variables, name in requests:
        if (out / name).exists():
            print(f"  {name} present, skipped")
            continue
        print(f"  {dataset} {' '.join(variables)} -> {name}", flush=True)
        copernicusmarine.subset(
            dataset_id=dataset, variables=variables,
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

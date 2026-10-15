"""Download hourly ERA5 single-level fields forcing a hindcast on domain B.

Wind at 10 m and mean sea level pressure drive the two-dimensional runs. Dew
point, air temperature, cloud cover, net solar and downward thermal radiation
feed the composite heat flux model of the three-dimensional runs. The request
is the one of dfm_tools.download_ERA5, one file per variable and month, made
here through cdsapi directly so that no ~/.cdsapirc is written. Credentials are
read from the .env of the StagnoneDT repository and are not printed.

Usage:
    python download_era5_hindcast.py --start 2025-07-21 --end 2025-08-02 \\
        --out data/raw/era5_2025-07
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

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT.parent / "StagnoneDT" / ".env"

# Domain B with a margin of two ERA5 cells of 0.25 degrees
BOX = (13.50, 35.25, 15.50, 36.75)

VARIABLES = {
    "u10": "10m_u_component_of_wind",
    "v10": "10m_v_component_of_wind",
    "msl": "mean_sea_level_pressure",
    "d2m": "2m_dewpoint_temperature",
    "t2m": "2m_temperature",
    "tcc": "total_cloud_cover",
    "ssr": "surface_net_solar_radiation",
    "strd": "surface_thermal_radiation_downwards",
}


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
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "raw" / "era5_2025-07")
    ap.add_argument("--vars", nargs="+", default=list(VARIABLES))
    args = ap.parse_args()

    load_env(ENV)
    import cdsapi
    client = cdsapi.Client(url=os.environ["CDSAPI_URL"], key=os.environ["CDSAPI_KEY"], quiet=True)

    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    lon0, lat0, lon1, lat1 = BOX
    for month in pd.period_range(args.start, args.end, freq="M"):
        for key in args.vars:
            target = out / f"era5_{key}_{month.strftime('%Y-%m')}.nc"
            if target.exists():
                print(f"  {target.name} present, skipped")
                continue
            print(f"  {key} {month} -> {target.name}", flush=True)
            client.retrieve("reanalysis-era5-single-levels", {
                "product_type": "reanalysis", "variable": VARIABLES[key],
                "year": month.strftime("%Y"), "month": month.strftime("%m"),
                "day": [f"{d:02d}" for d in range(1, 32)],
                "time": [f"{h:02d}:00" for h in range(24)],
                "area": [lat1, lon0, lat0, lon1],
                "data_format": "netcdf", "download_format": "unarchived",
            }).download(str(target))
    return 0


if __name__ == "__main__":
    sys.exit(main())

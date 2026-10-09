"""Download the EMODnet bathymetry of the Sicily Channel for the outer domain.

The outer domain of the long-wave sweep extends beyond the shelf grid held in
data/external/emodnet_shelf.tif, 13.9 to 15.3 E and 35.6 to 37.0 N. The EMODnet
Digital Bathymetry DTM is requested from the WCS of the portal in tiles of one
degree, since a single request for the whole box is refused by the server, and
the tiles are merged and averaged over blocks of DECIMATE cells. The native
cell of 1/16 arc-minute, some 115 m, then becomes 1/4 arc-minute, some 460 m,
which is finer than the cells of 2 to 4 km the outer domain carries.

Usage:
    python download_emodnet_channel.py
"""

from __future__ import annotations

import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "external" / "emodnet_channel.tif"
TILES = ROOT / "data" / "external" / "emodnet_channel_tiles"
OWS = "https://ows.emodnet-bathymetry.eu"
BOX = (12, 34, 18, 38)              # lon0, lat0, lon1, lat1, whole degrees
DECIMATE = 4
TIMEOUT = 300


def fetch_tile(lon: int, lat: int) -> Path:
    path = TILES / f"emodnet_{lon:02d}E_{lat:02d}N.tif"
    if path.exists() and path.stat().st_size > 10000:
        return path
    params = [("service", "WCS"), ("version", "2.0.1"), ("request", "GetCoverage"),
              ("coverageId", "emodnet__mean"), ("subset", f"Lat({lat},{lat + 1})"),
              ("subset", f"Long({lon},{lon + 1})"), ("format", "image/tiff")]
    url = f"{OWS}/wcs?{urllib.parse.urlencode(params)}"
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
                path.write_bytes(r.read())
            return path
        except OSError as err:
            print(f"  {path.name}: {err}, attempt {attempt + 1}", file=sys.stderr)
            time.sleep(5)
    raise RuntimeError(f"tile {lon} E {lat} N not retrieved")


def main(argv=None) -> int:
    import argparse

    import rasterio
    from rasterio.merge import merge
    from rasterio.transform import from_origin

    ap = argparse.ArgumentParser()
    ap.add_argument("--box", type=int, nargs=4, default=BOX,
                    metavar=("LON0", "LAT0", "LON1", "LAT1"), help="whole degrees")
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    out = Path(args.out)
    TILES.mkdir(parents=True, exist_ok=True)
    lon0, lat0, lon1, lat1 = args.box
    paths = []
    for lat in range(int(lat0), int(lat1)):
        for lon in range(int(lon0), int(lon1)):
            paths.append(fetch_tile(lon, lat))
    sources = [rasterio.open(p) for p in paths]
    z, transform = merge(sources, nodata=np.nan, dtype="float32")
    nodata = sources[0].nodata
    for s in sources:
        s.close()
    z = z[0]
    if nodata is not None:
        z[np.isclose(z, nodata)] = np.nan

    # Block mean, ignoring cells without data.
    ny, nx = (z.shape[0] // DECIMATE) * DECIMATE, (z.shape[1] // DECIMATE) * DECIMATE
    blocks = z[:ny, :nx].reshape(ny // DECIMATE, DECIMATE, nx // DECIMATE, DECIMATE)
    with np.errstate(invalid="ignore"):
        coarse = np.nanmean(blocks, axis=(1, 3)).astype("float32")
    t = from_origin(transform.c, transform.f, transform.a * DECIMATE, -transform.e * DECIMATE)
    with rasterio.open(out, "w", driver="GTiff", height=coarse.shape[0], width=coarse.shape[1],
                       count=1, dtype="float32", crs="EPSG:4326", transform=t,
                       nodata=np.nan, compress="deflate") as dst:
        dst.write(coarse, 1)
    print(f"written {out}, {coarse.shape[1]} x {coarse.shape[0]} cells of "
          f"{t.a * 60:.3f} arc-minute, elevation {np.nanmin(coarse):.0f} to "
          f"{np.nanmax(coarse):.0f} m, without data {np.isnan(coarse).mean():.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Publish the interactive maps of the long-wave scenarios to EDITO object storage.

The pages are static, an index and one directory for each scenario, so they are
served from the S3 bucket of the EDITO Datalab with no server, as the portal of
the Stagnone digital twin is. The credentials, the check of the session token
and the calls to the MinIO client are those of
StagnoneDT/scripts/publish_wetwise_edito.py, reused here.

The credentials are read from the .env of this repository when it exists and
otherwise from that of the Stagnone repository, both being outside version
control. The EDITO session token lasts about a day and limits the upload alone,
so pages already published remain reachable after it lapses.

Usage:
    python publish_longwave_portal.py --check     reports the token and the size, uploads nothing
    python publish_longwave_portal.py
    python publish_longwave_portal.py --portal outputs/hindcast_portal/v03_3d20_0722_0801 \
        --prefix malta-hindcast
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STAGNONE = ROOT.parent / "StagnoneDT"
PORTAL = ROOT / "outputs" / "longwave_portal"
BUCKET = "oidc-cmartinsjr"
PREFIX = "malta-longwave"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="report the state of the token and the size of the upload, and stop")
    ap.add_argument("--portal", type=Path, default=PORTAL, help="directory holding index.html")
    ap.add_argument("--prefix", default=PREFIX, help="path of the pages in the bucket")
    args = ap.parse_args(argv)
    portal = args.portal if args.portal.is_absolute() else ROOT / args.portal
    prefix = args.prefix

    sys.path.insert(0, str(STAGNONE / "scripts"))
    import publish_wetwise_edito as pw

    if (ROOT / ".env").exists():
        pw.ROOT = ROOT
    print(f"credentials from {pw.ROOT / '.env'}")
    if not (portal / "index.html").exists():
        print(f"no index page at {portal}, run build_longwave_portal_set.py", file=sys.stderr)
        return 1
    files = [p for p in portal.rglob("*") if p.is_file() and p.suffix != ".nc"]
    size = sum(p.stat().st_size for p in files) / 1e6
    scenarios = sorted(p.parent.name for p in portal.glob("*/index.html"))
    print(f"{len(scenarios)} scenarios, {len(files)} files, {size:.0f} MB")

    env = pw.load_env()
    exp = pw.token_expiry(env["AWS_SESSION_TOKEN"])
    left = (exp - time.time()) / 3600 if exp else None
    if left is not None:
        when = time.strftime("%Y-%m-%d %H:%M", time.localtime(exp))
        print(f"session token expires {when}, {left:+.1f} h from now")
    url = "{}/{}/{}/index.html".format(env["AWS_S3_ENDPOINT"].rstrip("/"), BUCKET, prefix)
    if args.check:
        print(f"would publish to {url}")
        return 0
    if left is not None and left <= 0:
        print("the EDITO session token has expired, refresh the AWS_* values in the .env",
              file=sys.stderr)
        return 1

    environ = pw.mc_env(env)
    dest = f"{pw.ALIAS}/{BUCKET}/{prefix}"
    # mirror and not cp --recursive, which appends the name of the source
    # directory to the destination. The regridded caches are left out.
    pw.run(["mirror", "--overwrite", "--quiet", "--exclude", "*.nc", str(portal), dest],
           environ, check=True)
    pw.run(["anonymous", "set", "download", dest], environ, check=True)
    print(f"public URL:\n  {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

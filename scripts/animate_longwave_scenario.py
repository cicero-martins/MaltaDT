"""Animation of one scenario of the long-wave sweep.

Reads the map and history output of a scenario run by
build_longwave_scenario.py with map output, and writes a video with four
views that share one clock:

- the water level over the shelf between Malta and Sicily, with the track of
  the pressure disturbance and its footprint at one standard deviation, drawn
  thicker as its amplitude rises;
- the water level inside the Valletta harbours;
- the current speed inside the harbours;
- the records of level at three stations, with a cursor at the current time.

Levels are in units of the static response to the pressure rise. Cells with
less than MIN_DEPTH of water are left blank.

Usage:
    python animate_longwave_scenario.py outer01_h225_u36_s15 --root model/tests/longwave_video
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_longwave_scenario as bl  # noqa: E402

OUT_DIR = bl.ROOT / "figures" / "videos"
SHELF_BOX = (13.5, 35.25, 15.9, 37.3)
HARBOUR_BOX = (14.488, 35.872, 14.535, 35.912)
MIN_DEPTH = 0.05                # m
FPS = 12
STATIONS = (("offshore_4km", "4 km off the harbours", "#52514e"),
            ("senglea", "Senglea", "#2a78d6"), ("msida_head", "Msida Creek, head", "#eb6834"))
FROM = {0: "south", 45: "southwest", 90: "west", 135: "northwest", 180: "north",
        225: "northeast", 270: "east", 315: "southeast"}


def main(argv=None) -> int:
    import imageio_ffmpeg
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import xarray as xr
    import xugrid as xu
    from matplotlib.animation import FFMpegWriter
    from matplotlib.collections import PolyCollection
    from pyproj import Transformer

    ap = argparse.ArgumentParser()
    ap.add_argument("case")
    ap.add_argument("--root", default=str(bl.OUT), help="directory holding the case")
    ap.add_argument("--stride", type=int, default=1, help="use every n-th map time")
    args = ap.parse_args(argv)
    root = Path(args.root)
    if not root.is_absolute():
        root = bl.ROOT / root
    d = root / args.case
    sc = json.loads((d / "scenario.json").read_text())
    es = sc["rise"] / (bl.RHO * bl.G)

    ds = xu.open_dataset(d / "output" / f"{args.case}_map.nc")
    grid = ds.grid
    t = (ds["time"].values - ds["time"].values[0]) / np.timedelta64(1, "s")
    fx, fy = grid.face_x, grid.face_y
    xy = np.c_[grid.node_x, grid.node_y]
    fn = grid.face_node_connectivity

    def inside(box):
        return (fx > box[0]) & (fx < box[2]) & (fy > box[1]) & (fy < box[3])

    sel_s, sel_h = inside(SHELF_BOX), inside(HARBOUR_BOX)
    wet = ds["mesh2d_waterdepth"].isel(time=0).values > MIN_DEPTH
    level_s = ds["mesh2d_s1"].values[:, sel_s] / es
    level_h = np.where(wet[sel_h], ds["mesh2d_s1"].values[:, sel_h] / es, np.nan)
    speed_h = np.where(wet[sel_h], ds["mesh2d_ucmag"].values[:, sel_h] * 100.0, np.nan)
    level_s = np.where(wet[sel_s], level_s, np.nan)
    # The shelf scale leaves out the harbours and the cells near the coast of
    # Malta, where the level is several times that of the open shelf.
    open_shelf = ~inside((14.1, 35.75, 14.65, 36.15))[sel_s]
    lim_s = float(np.nanpercentile(np.abs(level_s[:, open_shelf]), 99.5))
    lim_h = float(np.nanpercentile(np.abs(level_h), 99.5))
    lim_u = float(np.nanpercentile(speed_h, 99.9))

    hs = xr.open_dataset(d / "output" / f"{args.case}_his.nc")
    names = [s.strip() for s in hs["station_name"].values.astype(str)]
    th = (hs["time"].values - hs["time"].values[0]) / np.timedelta64(1, "s")
    wl = {n: hs["waterlevel"].values[:, i] / es for i, n in enumerate(names)}

    # Track and footprint of the disturbance, as in build_longwave_scenario.py.
    bl.TRACK_HALF, bl.RAMP = sc["track_half"], sc["ramp"]
    (xt, yt), (ex, ey) = bl.track(sc["heading"])
    back = Transformer.from_crs(bl.METRIC, bl.CRS, always_xy=True)
    ang = np.linspace(0, 2 * math.pi, 121)

    def footprint(time_s):
        s = sc["speed"] * time_s - sc["track_half"]
        along = sc["sigma_along"] * np.cos(ang)
        across = sc["sigma_across"] * np.sin(ang)
        return back.transform(xt + (s + along) * ex - across * ey,
                              yt + (s + along) * ey + across * ex)

    track_lon, track_lat = back.transform(
        [xt - sc["track_half"] * ex, xt + sc["track_half"] * ex],
        [yt - sc["track_half"] * ey, yt + sc["track_half"] * ey])

    plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#8a8984",
                         "xtick.color": "#52514e", "ytick.color": "#52514e"})
    fig = plt.figure(figsize=(12.8, 7.2), dpi=100, facecolor="#fcfcfb")
    gs = fig.add_gridspec(3, 3, height_ratios=[1, 1, 0.62], width_ratios=[1.25, 1, 1],
                          left=0.05, right=0.97, top=0.9, bottom=0.08, hspace=0.42, wspace=0.28)
    aspect = 1 / math.cos(math.radians(36.0))

    def polys(sel):
        return [xy[row[row >= 0]] for row in fn[sel]]

    ax_s = fig.add_subplot(gs[:2, 0])
    pc_s = PolyCollection(polys(sel_s), array=level_s[0], cmap="RdBu_r", linewidths=0)
    pc_s.set_clim(-lim_s, lim_s)
    ax_s.add_collection(pc_s)
    ax_s.plot(track_lon, track_lat, color="#0b0b0b", lw=0.8, ls="--")
    (foot,) = ax_s.plot([], [], color="#0b0b0b", lw=1.5)
    ax_s.plot(*bl.TARGET, "o", color="#0b0b0b", ms=4, mec="#fcfcfb", mew=1)
    ax_s.set_xlim(SHELF_BOX[0], SHELF_BOX[2])
    ax_s.set_ylim(SHELF_BOX[1], SHELF_BOX[3])
    ax_s.set_title("Water level over the shelf, with the pressure disturbance", fontsize=9,
                   loc="left")
    fig.colorbar(pc_s, ax=ax_s, label="level / static response", shrink=0.75, pad=0.02)

    ax_h = fig.add_subplot(gs[:2, 1])
    pc_h = PolyCollection(polys(sel_h), array=level_h[0], cmap="RdBu_r", linewidths=0)
    pc_h.set_clim(-lim_h, lim_h)
    ax_h.add_collection(pc_h)
    ax_h.set_title("Water level in the harbours", fontsize=9, loc="left")
    fig.colorbar(pc_h, ax=ax_h, label="level / static response", shrink=0.75, pad=0.02,
                 location="bottom")

    ax_u = fig.add_subplot(gs[:2, 2])
    pc_u = PolyCollection(polys(sel_h), array=speed_h[0], cmap="viridis", linewidths=0)
    pc_u.set_clim(0, lim_u)
    ax_u.add_collection(pc_u)
    ax_u.set_title(f"Current speed in the harbours, for a rise of {sc['rise'] / 100:.0f} hPa",
                   fontsize=9, loc="left")
    fig.colorbar(pc_u, ax=ax_u, label="cm/s", shrink=0.75, pad=0.02, location="bottom")

    for ax in (ax_h, ax_u):
        ax.set_xlim(HARBOUR_BOX[0], HARBOUR_BOX[2])
        ax.set_ylim(HARBOUR_BOX[1], HARBOUR_BOX[3])
        ax.set_xticks([])
        ax.set_yticks([])
    for ax in (ax_s, ax_h, ax_u):
        ax.set_aspect(aspect)
        ax.set_facecolor("#d6d5d0")

    ax_t = fig.add_subplot(gs[2, :])
    for name, label, colour in STATIONS:
        ax_t.plot(th / 3600, wl[name], color=colour, lw=1.2, label=label)
    cursor = ax_t.axvline(0, color="#0b0b0b", lw=1)
    ax_t.set_xlim(0, t[-1] / 3600)
    ax_t.set_xlabel("time from the start, h")
    ax_t.set_ylabel("level / static response")
    ax_t.grid(color="#e8e7e3", lw=0.6)
    ax_t.legend(frameon=False, fontsize=8, ncol=3, loc="upper left")
    for side in ("top", "right"):
        ax_t.spines[side].set_visible(False)

    title = fig.text(0.05, 0.95, "", fontsize=11, ha="left")
    head = (f"Pressure rise of {sc['rise'] / 100:.0f} hPa arriving from the "
            f"{FROM.get(int(sc['heading']), '')} at {sc['speed'] * 3.6:.0f} km/h, "
            f"{sc['sigma_along'] / 1e3:.0f} km long")

    matplotlib.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{args.case}.mp4"
    writer = FFMpegWriter(fps=FPS, bitrate=2500, codec="libx264",
                          extra_args=["-pix_fmt", "yuv420p"])
    frames = range(0, t.size, args.stride)
    with writer.saving(fig, str(out), dpi=100):
        for k in frames:
            pc_s.set_array(level_s[k])
            pc_h.set_array(level_h[k])
            pc_u.set_array(speed_h[k])
            a = float(bl.amplitude(np.array([t[k]]), sc["t_track"])[0])
            if a > 0.01:
                foot.set_data(*footprint(t[k]))
                foot.set_linewidth(0.5 + 2.0 * a)
            else:
                foot.set_data([], [])
            cursor.set_xdata([t[k] / 3600, t[k] / 3600])
            title.set_text(f"{head}    t = {int(t[k] // 3600):d} h {int(t[k] % 3600 // 60):02d} min")
            writer.grab_frame()
    print(f"{len(frames)} frames at {FPS} per second, written to {out} "
          f"({out.stat().st_size / 1e6:.1f} MB)")
    print(f"colour limits: shelf {lim_s:.1f}, harbours {lim_h:.1f} of the static response, "
          f"speed {lim_u:.0f} cm/s")
    # A still frame near the passage over the harbours, for inspection.
    k = int(np.argmin(np.abs(t - sc["track_half"] / sc["speed"] - 900)))
    pc_s.set_array(level_s[k])
    pc_h.set_array(level_h[k])
    pc_u.set_array(speed_h[k])
    foot.set_data(*footprint(t[k]))
    cursor.set_xdata([t[k] / 3600, t[k] / 3600])
    title.set_text(f"{head}    t = {int(t[k] // 3600):d} h {int(t[k] % 3600 // 60):02d} min")
    fig.savefig(out.with_suffix(".png"), dpi=100)
    return 0


if __name__ == "__main__":
    sys.exit(main())

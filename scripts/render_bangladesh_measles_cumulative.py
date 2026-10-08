import json
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import imageio_ffmpeg
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter

matplotlib.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()


REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_JSON = REPO_ROOT / "public" / "assets" / "measles" / "national_timeseries.json"
OUT_DIR = REPO_ROOT / "public" / "assets" / "measles"
OUT_MP4 = OUT_DIR / "bangladesh_measles_cumulative_1080p.mp4"
OUT_POSTER = OUT_DIR / "bangladesh_measles_cumulative_still_1080p.png"

WIDTH = 1920
HEIGHT = 1080
FPS = 24
DRAW_SECONDS = 14
HOLD_SECONDS = 3

BG = "#FFFFFF"
FG = "#1F2937"
MUTED = "#64748B"
GRID = "#E5E7EB"
BLUE = "#6366F1"
ORANGE = "#F59E0B"
SOFT_ORANGE = "#FCD59B"
SOFT_BLUE = "#C7D2FE"


def display_date(date, long=False):
    month = date.strftime("%B" if long else "%b")
    return f"{month} {date.day}, {date.year}" if long else f"{month} {date.day}"


def read_rows():
    source = json.loads(DATA_JSON.read_text(encoding="utf-8"))
    rows = []
    for index, row in enumerate(source):
        suspected = int(row["suspected"])
        confirmed = int(row["confirmed"])
        rows.append(
            {
                "index": index,
                "date": datetime.strptime(row["date"], "%Y-%m-%d"),
                "suspected": suspected,
                "confirmed": confirmed,
                "daily_total": suspected + confirmed,
            }
        )
    return rows


def moving_average(rows, key, window=7):
    out = []
    for index, _row in enumerate(rows):
        start = max(0, index - window + 1)
        values = [item[key] for item in rows[start:index + 1]]
        out.append(sum(values) / len(values))
    return out


def style_axis(ax):
    ax.set_facecolor(BG)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.tick_params(axis="both", colors=MUTED, labelsize=26, length=0, width=0)
    ax.grid(axis="y", color=GRID, linewidth=1.35)
    ax.grid(axis="x", visible=False)


def draw_frame(fig, rows, position):
    fig.clear()
    ax = fig.subplots()
    completed_rows = [row for row in rows if row["index"] <= position]
    max_index = rows[-1]["index"]
    tick_indexes = [0, 24, 51, 82, 113, 144, max_index]
    tick_indexes = [tick for tick in tick_indexes if tick <= max_index]

    style_axis(ax)
    ax.set_xlim(-1, max_index + 1)
    ax.set_ylim(0, 1800)
    ax.set_yticks([300, 600, 900, 1200, 1500, 1800])
    ax.set_xticks(tick_indexes)
    ax.set_xticklabels([display_date(rows[tick]["date"]) for tick in tick_indexes])
    ax.set_ylabel("Daily reported cases", color=FG, fontsize=30, labelpad=30)
    ax.set_xlabel("Report date", color=FG, fontsize=30, labelpad=24)

    bar_x = [row["index"] for row in completed_rows]
    suspected = [row["suspected"] for row in completed_rows]
    confirmed = [row["confirmed"] for row in completed_rows]
    daily_total = [row["daily_total"] for row in completed_rows]
    ma = moving_average(completed_rows, "daily_total") if completed_rows else []

    ax.bar(bar_x, suspected, width=0.9, color=SOFT_ORANGE, edgecolor="none", label="Suspected")
    ax.bar(bar_x, confirmed, width=0.9, bottom=suspected, color=SOFT_BLUE, edgecolor="none", label="Confirmed")
    if ma:
        ax.plot(bar_x, ma, color=ORANGE, linewidth=6.5, solid_capstyle="round", label="7-day average")

    if daily_total:
        latest = completed_rows[-1]
        latest_x = latest["index"]
        latest_y = latest["daily_total"]
        label_x = latest_x + 3.5
        label_ha = "left"
        if latest_x > max_index - 30:
            label_x = max_index - 3
            label_ha = "right"
        label_y = 1580
        ax.text(
            label_x,
            label_y,
            f"{latest_y:,} reported cases",
            color=FG,
            fontsize=36,
            ha=label_ha,
            va="center",
            weight="bold",
        )
        ax.text(
            label_x,
            label_y - 130,
            display_date(latest["date"], long=True),
            color=MUTED,
            fontsize=27,
            ha=label_ha,
            va="top",
        )

    ax.legend(
        loc="upper left",
        frameon=False,
        ncol=3,
        bbox_to_anchor=(0, 1.02),
        fontsize=25,
        handlelength=2.2,
        labelcolor=FG,
    )

    fig.text(
        0.095,
        0.94,
        "Bangladesh measles: daily reported cases",
        color=FG,
        fontsize=46,
        weight="bold",
        ha="left",
        va="center",
    )
    fig.subplots_adjust(left=0.115, right=0.965, top=0.82, bottom=0.16)


def main():
    rows = read_rows()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(WIDTH / 100, HEIGHT / 100), dpi=100, facecolor=BG)

    draw_frames = FPS * DRAW_SECONDS
    hold_frames = FPS * HOLD_SECONDS
    frames = draw_frames + hold_frames
    max_position = rows[-1]["index"]

    writer = FFMpegWriter(
        fps=FPS,
        codec="libx264",
        bitrate=12000,
        extra_args=["-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.2", "-an"],
    )

    with writer.saving(fig, str(OUT_MP4), dpi=100):
        for frame in range(frames):
            if frame < draw_frames:
                progress = frame / (draw_frames - 1)
                position = max_position * progress
            else:
                position = max_position
            draw_frame(fig, rows, position)
            writer.grab_frame(facecolor=BG)

    draw_frame(fig, rows, max_position)
    fig.savefig(OUT_POSTER, dpi=100, facecolor=BG)
    plt.close(fig)
    print(OUT_MP4)
    print(OUT_POSTER)


if __name__ == "__main__":
    main()

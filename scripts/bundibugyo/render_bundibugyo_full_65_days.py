import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import imageio_ffmpeg
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter

matplotlib.rcParams["animation.ffmpeg_path"] = imageio_ffmpeg.get_ffmpeg_exe()


REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_ASSETS = REPO_ROOT / "public" / "assets" / "bundibugyo"
DATA_CSV = PUBLIC_ASSETS / "sitrep_cumulative_cases_nyt_scale_extended.csv"
HISTORICAL_CSV = Path(__file__).resolve().parent / "historical_comparison_points.csv"
OUT_MP4 = PUBLIC_ASSETS / "bundibugyo_full_65_days_1080p.mp4"

WIDTH = 1920
HEIGHT = 1080
FPS = 30
DRAW_SECONDS = 18
HOLD_SECONDS = 5
X_MAX = 100
VIEW_HEIGHT = 800
START_PAN_DAY = 25

BG = "#F6F3EE"
FG = "#171717"
RED = "#D63A2E"
MUTED = "#5A5A5A"
GRID = "#D8D3CC"
COMPARE = "#7B7B7B"


def read_current():
    rows = []
    with DATA_CSV.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            day = int(row["days_after_declaration"])
            if day < 0:
                continue
            rows.append(
                {
                    "day": day,
                    "cases": int(row["cumulative_confirmed_cases"]),
                    "date": row["report_date"],
                    "sitrep": row["sitrep"],
                }
            )
    return rows


def read_comparisons():
    comparisons = {}
    with HISTORICAL_CSV.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            outbreak = row["outbreak"]
            comparisons.setdefault(outbreak, []).append(
                (int(row["days_after_declaration"]), int(row["cumulative_cases"]))
            )
    return {name: sorted(points) for name, points in comparisons.items()}


def interp(points, day):
    if day <= points[0]["day"]:
        return points[0]["cases"]
    for left, right in zip(points, points[1:]):
        if day <= right["day"]:
            span = right["day"] - left["day"]
            if span <= 0:
                return right["cases"]
            t = (day - left["day"]) / span
            return left["cases"] + (right["cases"] - left["cases"]) * t
    return points[-1]["cases"]


def trim_points(points, day):
    out = [p for p in points if p["day"] <= day]
    if not out or out[-1]["day"] < day:
        out.append({"day": day, "cases": interp(points, day), "date": "", "sitrep": ""})
    return out


def ease_in_out(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def y_window(day, cases):
    if day <= START_PAN_DAY:
        return 0, VIEW_HEIGHT

    desired_top = max(VIEW_HEIGHT, cases + 115)
    desired_bottom = desired_top - VIEW_HEIGHT
    pan_progress = ease_in_out((day - START_PAN_DAY) / max(latest_day - START_PAN_DAY, 1))
    bottom = desired_bottom * pan_progress
    return bottom, bottom + VIEW_HEIGHT


def draw_custom_axes(ax, y_min, y_max):
    for spine in ax.spines.values():
        spine.set_visible(False)

    tick_color = FG
    axis_lw = 1.5
    ax.vlines(0, y_min, y_max, color=tick_color, linewidth=axis_lw, clip_on=True, zorder=3)
    if y_min <= 0 <= y_max:
        ax.hlines(0, 0, X_MAX, color=tick_color, linewidth=axis_lw, clip_on=True, zorder=3)


def main():
    current = read_current()
    if not current:
        raise RuntimeError("No current outbreak data found")
    global latest_day
    latest_day = current[-1]["day"]

    comparisons = read_comparisons()

    draw_frames = FPS * DRAW_SECONDS
    hold_frames = FPS * HOLD_SECONDS
    frames = draw_frames + hold_frames
    fig, ax = plt.subplots(figsize=(WIDTH / 100, HEIGHT / 100), dpi=100)
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(BG)

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
                day = latest_day * progress
            else:
                day = latest_day

            shown = trim_points(current, day)
            x = [p["day"] for p in shown]
            y = [p["cases"] for p in shown]
            cases = y[-1]
            y_min, y_max = y_window(day, cases)

            ax.clear()
            fig.texts.clear()
            ax.set_facecolor(BG)
            ax.set_xlim(0, X_MAX)
            ax.set_ylim(y_min, y_max)
            ax.set_xticks([0, 25, 50, 75, 100])
            y_tick_start = int((y_min // 200) * 200)
            ax.set_yticks([v for v in range(y_tick_start, int(y_max) + 201, 200) if y_min <= v <= y_max])
            ax.tick_params(axis="both", colors=FG, labelsize=24, length=0, width=0)
            ax.tick_params(axis="x", labelbottom=(y_min <= 0))
            ax.grid(axis="y", color=GRID, linewidth=1.2)
            ax.grid(axis="x", visible=False)
            draw_custom_axes(ax, y_min, y_max)

            for label, pts in comparisons.items():
                cx = [p[0] for p in pts]
                cy = [p[1] for p in pts]
                ax.plot(cx, cy, color=COMPARE, linewidth=2.3, alpha=0.55)
                visible = [p for p in pts if p[0] <= X_MAX and y_min <= p[1] <= y_max]
                if visible:
                    label_x, label_y = visible[-1]
                    if label == "2014 West Africa outbreak":
                        ax.text(
                            86,
                            690,
                            "2014 West Africa outbreak",
                            color=MUTED,
                            fontsize=23,
                            ha="right",
                            va="top",
                        )
                    else:
                        ax.text(
                            min(label_x + 2, 99),
                            label_y - 120,
                            "2018 Congo outbreak",
                            color=MUTED,
                            fontsize=23,
                            ha="right",
                            va="top",
                        )

            ax.plot(x, y, color=RED, linewidth=6.5, solid_capstyle="round", solid_joinstyle="round")
            ax.scatter([x[-1]], [y[-1]], s=175, color=RED, zorder=5)

            label_x = min(x[-1] + 3.0, 78)
            label_y = min(cases + 58, y_max - 55)
            ax.text(
                label_x,
                label_y,
                f"{round(cases):,} confirmed cases",
                color=RED,
                fontsize=31,
                ha="left",
                va="center",
                weight="medium",
            )
            ax.text(
                label_x,
                label_y - 45,
                f"Day {round(day)} after declaration",
                color=MUTED,
                fontsize=24,
                ha="left",
                va="top",
            )

            ax.set_ylabel("Cumulative Ebola cases", color=FG, fontsize=26, labelpad=28)
            if y_min <= 0:
                ax.set_xlabel("Days after outbreak declared", color=FG, fontsize=26, labelpad=22)
            else:
                ax.set_xlabel("")
            fig.subplots_adjust(left=0.095, right=0.965, top=0.89, bottom=0.18)
            writer.grab_frame(facecolor=BG)

    print(OUT_MP4)


if __name__ == "__main__":
    main()

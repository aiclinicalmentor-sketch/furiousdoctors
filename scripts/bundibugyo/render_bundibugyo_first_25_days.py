import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter


REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_ASSETS = REPO_ROOT / "public" / "assets" / "bundibugyo"
DATA_CSV = PUBLIC_ASSETS / "sitrep_cumulative_cases_nyt_scale_extended.csv"
OUT_MP4 = PUBLIC_ASSETS / "bundibugyo_first_25_days_1080p.mp4"

WIDTH = 1920
HEIGHT = 1080
FPS = 30
DURATION_SECONDS = 8
END_DAY = 25
X_MAX = 100
Y_MAX = 800

BG = "#111111"
FG = "#F2F2F2"
MUTED = "#858585"
GRID = "#343434"
COMPARE = "#5F5F5F"


def read_current():
    rows = []
    with DATA_CSV.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            day = int(row["days_after_declaration"])
            if day < 0 or day > END_DAY:
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


def main():
    current = read_current()
    if not current:
        raise RuntimeError("No current outbreak data found")

    comparisons = {
        "2014 West Africa": [(0, 49), (9, 130), (23, 176), (40, 239), (51, 260), (66, 309), (87, 528), (100, 759)],
        "2018 DRC Kivu": [(0, 26), (2, 76), (4, 74), (9, 100), (11, 115), (16, 103), (19, 111), (23, 117), (25, 121), (30, 128), (37, 145), (95, 361), (100, 389)],
    }

    frames = FPS * DURATION_SECONDS
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
            progress = frame / (frames - 1)
            day = END_DAY * progress
            shown = trim_points(current, day)
            x = [p["day"] for p in shown]
            y = [p["cases"] for p in shown]
            cases = y[-1]

            ax.clear()
            ax.set_facecolor(BG)
            for spine in ax.spines.values():
                spine.set_color(FG)
                spine.set_linewidth(1.3)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.set_xlim(0, X_MAX)
            ax.set_ylim(0, Y_MAX)
            ax.set_xticks([0, 25, 50, 75, 100])
            ax.set_yticks([0, 200, 400, 600, 800])
            ax.tick_params(axis="both", colors=FG, labelsize=24, length=7, width=1.2)
            ax.grid(axis="y", color=GRID, linewidth=1.2)
            ax.grid(axis="x", visible=False)

            for label, pts in comparisons.items():
                cx = [p[0] for p in pts]
                cy = [p[1] for p in pts]
                ax.plot(cx, cy, color=COMPARE, linewidth=2.3, alpha=0.6)
                if label == "2014 West Africa":
                    ax.text(99, cy[-1] + 18, label, color=MUTED, fontsize=23, ha="right", va="bottom")
                else:
                    ax.text(99, cy[-1] - 16, label, color=MUTED, fontsize=23, ha="right", va="top")

            ax.plot(x, y, color=FG, linewidth=5.5, solid_capstyle="round", solid_joinstyle="round")
            ax.scatter([x[-1]], [y[-1]], s=155, color=FG, zorder=5)
            ax.text(
                min(x[-1] + 3.0, 84),
                min(cases + 34, Y_MAX - 30),
                f"{round(cases):,} confirmed cases",
                color=FG,
                fontsize=30,
                ha="left",
                va="center",
                weight="medium",
            )
            ax.text(
                min(x[-1] + 3.0, 84),
                max(min(cases - 2, Y_MAX - 70), 38),
                f"Day {round(day)} after declaration",
                color=MUTED,
                fontsize=24,
                ha="left",
                va="top",
            )
            ax.set_xlabel("Days after outbreak declared", color=FG, fontsize=26, labelpad=22)
            ax.set_ylabel("Cumulative Ebola cases", color=FG, fontsize=26, labelpad=22)
            ax.set_title(
                "DRC Ebola Bundibugyo outbreak: first 25 days",
                color=FG,
                fontsize=34,
                loc="left",
                pad=22,
                weight="medium",
            )
            ax.text(
                0,
                -0.18,
                "Source: DRC/INSP SitRep PDFs. Comparison curves use historical WHO-derived outbreak tabulations.",
                transform=ax.transAxes,
                color=MUTED,
                fontsize=19,
                ha="left",
                va="top",
            )
            fig.subplots_adjust(left=0.095, right=0.965, top=0.89, bottom=0.18)
            writer.grab_frame(facecolor=BG)

    print(OUT_MP4)


if __name__ == "__main__":
    main()

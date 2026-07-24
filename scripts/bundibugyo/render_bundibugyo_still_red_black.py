import csv
import math
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[2]
PUBLIC_ASSETS = REPO_ROOT / "public" / "assets" / "bundibugyo"
DATA_CSV = PUBLIC_ASSETS / "sitrep_cumulative_cases_nyt_scale_extended.csv"
HISTORICAL_CSV = Path(__file__).resolve().parent / "historical_comparison_points.csv"
OUT_PNG = PUBLIC_ASSETS / "bundibugyo_still_red_black_1080p.png"

WIDTH = 1920
HEIGHT = 1080
X_MAX = 200

BG = "#F6F3EE"
RED = "#D63A2E"
FG = "#171717"
MUTED = "#5A5A5A"
GRID = "#D8D3CC"
COMPARE = "#7B7B7B"


def read_current():
    rows = []
    with DATA_CSV.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            day = int(row["days_after_declaration"])
            if 0 <= day:
                rows.append((day, int(row["cumulative_confirmed_cases"])))
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


def main():
    current = read_current()
    if not current:
        raise RuntimeError("No current outbreak data found")
    comparisons = read_comparisons()

    fig = plt.figure(figsize=(WIDTH / 100, HEIGHT / 100), dpi=100, facecolor=BG)
    ax = fig.add_axes([0.125, 0.20, 0.60, 0.72], facecolor=BG)

    for spine in ax.spines.values():
        spine.set_color(FG)
        spine.set_linewidth(1.5)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    ax.set_xlim(0, X_MAX)
    ax.set_xticks([0, 50, 100, 150, 200])
    ax.tick_params(axis="both", colors=FG, labelsize=24, length=7, width=1.2)
    ax.grid(axis="y", color=GRID, linewidth=1.2)
    ax.grid(axis="x", visible=False)

    for label, pts in comparisons.items():
        cx = [p[0] for p in pts]
        cy = [p[1] for p in pts]
        ax.plot(cx, cy, color=COMPARE, linewidth=2.6, alpha=0.72)
        if label == "2014 West Africa outbreak":
            ax.text(158, 2180, "2014 West Africa outbreak", color=MUTED, fontsize=24, ha="left", va="top", linespacing=1.35)
        else:
            ax.text(158, 430, "2018 Congo outbreak", color=MUTED, fontsize=24, ha="left", va="top", linespacing=1.35)

    x = [p[0] for p in current]
    y = [p[1] for p in current]
    y_max = max(2600, int(math.ceil(max(y) / 400) * 400))

    ax.set_ylim(0, y_max)
    ax.set_yticks(range(0, y_max + 1, 400))
    ax.plot(x, y, color=RED, linewidth=8.5, solid_capstyle="round", solid_joinstyle="round")
    ax.scatter([x[-1]], [y[-1]], s=175, color=RED, zorder=6)
    label_x = min(x[-1] + 8, X_MAX - 70)
    label_y = min(y[-1] + 130, y_max - 150)
    ax.text(
        label_x,
        label_y,
        f"{y[-1]:,} confirmed cases",
        color=RED,
        fontsize=29,
        ha="left",
        va="center",
        weight="medium",
    )
    ax.text(
        label_x,
        label_y - 92,
        f"Day {x[-1]} after declaration",
        color=MUTED,
        fontsize=23,
        ha="left",
        va="top",
    )

    ax.set_xlabel("Days after outbreak declared", color=FG, fontsize=25, labelpad=22)
    ax.set_ylabel("Cumulative Ebola cases", color=FG, fontsize=25, labelpad=28)

    fig.savefig(OUT_PNG, dpi=100, facecolor=BG)
    print(OUT_PNG)


if __name__ == "__main__":
    main()

import csv
import math
from datetime import date, datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[2]
WORK_DIR = REPO_ROOT / ".bundibugyo_work"
PUBLIC_ASSETS = REPO_ROOT / "public" / "assets" / "bundibugyo"
IN_CSV = WORK_DIR / "sitrep_cumulative_cases_by_date.csv"
OUT_PNG = WORK_DIR / "sitrep_cumulative_cases_nyt_scale_extended.png"
OUT_CSV = PUBLIC_ASSETS / "sitrep_cumulative_cases_nyt_scale_extended.csv"

DECLARATION_DATE = date(2026, 5, 15)


def read_rows():
    rows = []
    with IN_CSV.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            report_date = datetime.fromisoformat(row["report_date"]).date()
            rows.append(
                {
                    "report_date": report_date,
                    "days_after_declaration": (report_date - DECLARATION_DATE).days,
                    "sitrep": row["sitrep"],
                    "cases": int(row["cumulative_confirmed_cases"]),
                    "source_file": row["source_file"],
                }
            )
    return rows


def write_csv(rows):
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "report_date",
                "days_after_declaration",
                "sitrep",
                "cumulative_confirmed_cases",
                "source_file",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "report_date": row["report_date"].isoformat(),
                    "days_after_declaration": row["days_after_declaration"],
                    "sitrep": row["sitrep"],
                    "cumulative_confirmed_cases": row["cases"],
                    "source_file": row["source_file"],
                }
            )


def plot(rows):
    x = [row["days_after_declaration"] for row in rows]
    y = [row["cases"] for row in rows]
    june8 = next(row for row in rows if row["report_date"] == date(2026, 6, 8))
    last = rows[-1]
    y_max = int(math.ceil(max(y) / 200) * 200)

    # Preserve the original 100-day by 800-case scale density from the square chart.
    fig_width = 10.8
    fig_height = fig_width * (y_max / 800)
    fig, ax = plt.subplots(figsize=(fig_width, fig_height), dpi=180)

    ax.plot(x, y, color="#c63b24", linewidth=3.0)
    ax.scatter(x, y, color="#c63b24", s=30, zorder=3)
    ax.scatter(
        [june8["days_after_declaration"]],
        [june8["cases"]],
        color="#111111",
        s=78,
        zorder=4,
    )
    ax.annotate(
        "598 confirmed cases\nDRC SitRep, June 8",
        xy=(june8["days_after_declaration"], june8["cases"]),
        xytext=(31, 645),
        ha="left",
        va="center",
        arrowprops={"arrowstyle": "-", "color": "#333333", "lw": 1.5},
        fontsize=12,
        color="#111111",
    )
    ax.scatter(
        [last["days_after_declaration"]],
        [last["cases"]],
        color="#111111",
        s=78,
        zorder=4,
    )
    last_date_label = f"{last['report_date'].strftime('%b')} {last['report_date'].day}"
    ax.annotate(
        f"{last['cases']:,} confirmed cases\nDRC SitRep, {last_date_label}",
        xy=(last["days_after_declaration"], last["cases"]),
        xytext=(last["days_after_declaration"] + 5, last["cases"] - 110),
        ha="left",
        va="center",
        arrowprops={"arrowstyle": "-", "color": "#333333", "lw": 1.5},
        fontsize=12,
        color="#111111",
    )

    ax.set_xlim(0, 102)
    ax.set_ylim(0, y_max + 20)
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_yticks(list(range(0, y_max + 1, 200)))
    ax.set_xlabel("Days after outbreak declared", labelpad=18)
    ax.set_ylabel("Cumulative confirmed Ebola cases")
    ax.grid(True, axis="y", color="#dddddd", linewidth=0.9)
    ax.grid(False, axis="x")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.set_title(
        "DRC Ebola Bundibugyo confirmed cases on NYT-style 100-day scale",
        loc="left",
        pad=14,
    )
    ax.text(
        0,
        -0.06,
        "Day 0 is DRC outbreak declaration date, May 15, 2026. Source: DRC/INSP SitRep PDFs.",
        transform=ax.transAxes,
        fontsize=9,
        color="#555555",
    )
    fig.tight_layout()
    fig.savefig(OUT_PNG, bbox_inches="tight")


def main():
    rows = read_rows()
    write_csv(rows)
    plot(rows)
    print(f"rows={len(rows)} png={OUT_PNG} csv={OUT_CSV}")


if __name__ == "__main__":
    main()

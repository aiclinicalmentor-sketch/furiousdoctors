import csv
from datetime import date, datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt


REPO_ROOT = Path(__file__).resolve().parents[2]
WORK_DIR = REPO_ROOT / ".bundibugyo_work"
IN_CSV = WORK_DIR / "sitrep_cumulative_cases.csv"
OUT_CSV = WORK_DIR / "sitrep_cumulative_cases_by_date.csv"
OUT_PNG = WORK_DIR / "sitrep_cumulative_cases_by_date.png"


def read_rows():
    rows = []
    with IN_CSV.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if not row["report_date"] or not row["cumulative_confirmed_cases"]:
                continue
            rows.append(
                {
                    "report_date": datetime.fromisoformat(row["report_date"]).date(),
                    "sitrep": int(row["sitrep"]) if row["sitrep"] else -1,
                    "cases": int(row["cumulative_confirmed_cases"]),
                    "file": row["file"],
                    "method": row["method"],
                }
            )
    return rows


def dedupe_by_date(rows):
    selected = {}
    for row in rows:
        key = row["report_date"]
        current = selected.get(key)
        if current is None:
            selected[key] = row
            continue
        if (row["sitrep"], row["cases"], row["file"]) > (current["sitrep"], current["cases"], current["file"]):
            selected[key] = row
    return [selected[key] for key in sorted(selected)]


def write_csv(rows):
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["report_date", "sitrep", "cumulative_confirmed_cases", "source_file", "method"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "report_date": row["report_date"].isoformat(),
                    "sitrep": row["sitrep"] if row["sitrep"] >= 0 else "",
                    "cumulative_confirmed_cases": row["cases"],
                    "source_file": row["file"],
                    "method": row["method"],
                }
            )


def plot(rows):
    dates = [row["report_date"] for row in rows]
    cases = [row["cases"] for row in rows]
    june8 = date(2026, 6, 8)
    june8_cases = next(row["cases"] for row in rows if row["report_date"] == june8)

    fig, ax = plt.subplots(figsize=(11, 6.2), dpi=180)
    ax.plot(dates, cases, color="#c33a22", linewidth=2.7)
    ax.scatter(dates, cases, s=24, color="#c33a22", zorder=3)
    ax.scatter([june8], [june8_cases], s=76, color="#111111", zorder=4)
    ax.annotate(
        "June 8 SitRep: 598 confirmed cases",
        xy=(june8, june8_cases),
        xytext=(date(2026, 6, 13), june8_cases - 170),
        arrowprops={"arrowstyle": "->", "color": "#333333", "lw": 1.0},
        fontsize=10,
        color="#111111",
    )

    ax.set_title("DRC Ebola Bundibugyo outbreak: cumulative confirmed cases by SitRep report date", loc="left")
    ax.set_ylabel("Cumulative confirmed cases")
    ax.set_xlabel("Report date")
    ax.grid(True, axis="y", color="#dddddd", linewidth=0.8)
    ax.grid(False, axis="x")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %d"))
    fig.autofmt_xdate(rotation=0, ha="center")
    ax.set_ylim(0, max(cases) * 1.08)
    ax.text(
        0.01,
        -0.17,
        "Source: DRC/INSP SitRep PDFs in Bundibugyo/DRC SitReps. Duplicate dates use the highest SitRep number.",
        transform=ax.transAxes,
        fontsize=8.5,
        color="#555555",
    )
    fig.tight_layout()
    fig.savefig(OUT_PNG, bbox_inches="tight")


def main():
    rows = dedupe_by_date(read_rows())
    write_csv(rows)
    plot(rows)
    print(f"rows={len(rows)} csv={OUT_CSV} png={OUT_PNG}")
    for row in rows:
        print(row["report_date"].isoformat(), row["sitrep"], row["cases"])


if __name__ == "__main__":
    main()

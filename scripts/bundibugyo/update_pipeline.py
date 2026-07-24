import csv
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
PUBLIC_ASSETS = REPO_ROOT / "public" / "assets" / "bundibugyo"
SUMMARY_JSON = PUBLIC_ASSETS / "latest_bundibugyo_summary.json"

STEPS = [
    "download_insp_sitreps.py",
    "extract_sitrep_cases.py",
    "build_sitrep_case_chart.py",
    "build_sitrep_nyt_scale_extended_chart.py",
    "render_bundibugyo_first_25_days.py",
    "render_bundibugyo_full_65_days.py",
    "render_bundibugyo_day25_to_65_fast.py",
    "render_bundibugyo_still_red_black.py",
]


def run_step(script_name):
    script = SCRIPT_DIR / script_name
    print(f"running {script.name}")
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    if result.stdout:
        print(result.stdout.strip())
    if result.stderr:
        print(result.stderr.strip(), file=sys.stderr)
    if result.returncode != 0:
        raise RuntimeError(f"{script.name} failed with exit code {result.returncode}")


def latest_row():
    path = PUBLIC_ASSETS / "sitrep_cumulative_cases_nyt_scale_extended.csv"
    rows = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["report_date"] and row["cumulative_confirmed_cases"]:
                rows.append(row)
    if not rows:
        raise RuntimeError(f"No parsed rows found in {path}")
    rows.sort(key=lambda row: (row["report_date"], int(row["days_after_declaration"])))
    return rows[-1]


def update_website_index(latest):
    index_path = REPO_ROOT / "index.html"
    text = index_path.read_text(encoding="utf-8")
    sitrep = latest["sitrep"] or "NA"
    report_date = latest["report_date"]
    version = f"{report_date.replace('-', '')}-sitrep{sitrep}"
    cases = int(latest["cumulative_confirmed_cases"])

    updated = re.sub(
        r"(bundibugyo_still_red_black_1080p\.png\?v=)[^\"']+",
        rf"\g<1>{version}",
        text,
    )
    updated = re.sub(
        r"(bundibugyo_full_65_days_1080p\.mp4\?v=)[^\"']+",
        rf"\g<1>{version}",
        updated,
    )
    updated = re.sub(
        r"Latest local extraction: SitRep [^,]+, [^,]+, [0-9,]+ confirmed DRC cases\.",
        f"Latest local extraction: SitRep {sitrep}, {report_date}, {cases:,} confirmed DRC cases.",
        updated,
    )

    if updated == text:
        return False

    index_path.write_text(updated, encoding="utf-8", newline="\n")
    return True


def main():
    PUBLIC_ASSETS.mkdir(parents=True, exist_ok=True)
    for step in STEPS:
        run_step(step)

    latest = latest_row()
    index_updated = update_website_index(latest)
    summary = {
        "updated_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "latest_report_date": latest["report_date"],
        "latest_days_after_declaration": int(latest["days_after_declaration"]),
        "latest_sitrep": latest["sitrep"],
        "latest_cumulative_confirmed_cases": int(latest["cumulative_confirmed_cases"]),
        "latest_source_file": latest["source_file"],
        "website_index_updated": index_updated,
    }
    SUMMARY_JSON.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(
        "latest "
        f"date={summary['latest_report_date']} "
        f"sitrep={summary['latest_sitrep']} "
        f"cases={summary['latest_cumulative_confirmed_cases']:,} "
        f"day={summary['latest_days_after_declaration']}"
    )
    print(f"website_index_updated={index_updated}")
    print(f"summary={SUMMARY_JSON}")


if __name__ == "__main__":
    main()

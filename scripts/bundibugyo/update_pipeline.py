import csv
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_DIR = Path(__file__).resolve().parent
PUBLIC_ASSETS = REPO_ROOT / "public" / "assets" / "bundibugyo"
SUMMARY_JSON = PUBLIC_ASSETS / "latest_bundibugyo_summary.json"

DATA_STEPS = [
    "extract_sitrep_cases.py",
    "build_sitrep_case_chart.py",
    "build_sitrep_nyt_scale_extended_chart.py",
]

RENDER_STEPS = [
    "render_bundibugyo_first_25_days.py",
    "render_bundibugyo_full_65_days.py",
    "render_bundibugyo_day25_to_65_fast.py",
    "render_bundibugyo_still_red_black.py",
]


def run_step(script_name, extra_env=None):
    script = SCRIPT_DIR / script_name
    print(f"running {script.name}")
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(REPO_ROOT),
        env=env,
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


def latest_existing_sitrep():
    path = PUBLIC_ASSETS / "sitrep_cumulative_cases_nyt_scale_extended.csv"
    if not path.exists():
        return 0
    latest = 0
    with path.open("r", encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("sitrep"):
                latest = max(latest, int(row["sitrep"]))
    return latest


def sitrep_number(value):
    match = re.search(r"(?:sitrep|^|[_\-\s])n?[°º]?\s*0*([0-9]{1,3})(?:\D|$)", value, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def manifest_has_newer_records(after_sitrep):
    manifest_path = REPO_ROOT / ".bundibugyo_work" / "downloaded_sitreps_manifest.json"
    if not manifest_path.exists():
        return True
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    records = manifest.get("downloaded", []) + manifest.get("skipped_existing", [])
    for record in records:
        number = sitrep_number(record.get("file", "")) or sitrep_number(record.get("title", ""))
        if number is None or number > after_sitrep:
            return True
    return bool(manifest.get("failed"))


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
    sitrep = latest["sitrep"] or "NA"
    report_date = latest["report_date"]
    report_date_dt = datetime.strptime(report_date, "%Y-%m-%d")
    report_date_label = f"{report_date_dt.strftime('%B')} {report_date_dt.day}, {report_date_dt.year}"
    version = f"{report_date.replace('-', '')}-sitrep{sitrep}"
    cases = int(latest["cumulative_confirmed_cases"])

    changed = False
    for page_name in ["index.html", "drc-ebola.html"]:
        page_path = REPO_ROOT / page_name
        if not page_path.exists():
            continue
        text = page_path.read_text(encoding="utf-8")
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
            r"Latest local extraction: SitRep [^,]+, .*?, [0-9,]+ confirmed DRC cases\.",
            f"Latest local extraction: SitRep {sitrep}, {report_date_label}, {cases:,} confirmed DRC cases.",
            updated,
        )
        if updated != text:
            page_path.write_text(updated, encoding="utf-8", newline="\n")
            changed = True
    return changed


def main():
    PUBLIC_ASSETS.mkdir(parents=True, exist_ok=True)
    after_sitrep = latest_existing_sitrep()
    run_step("download_insp_sitreps.py", {"BUNDIBUGYO_AFTER_SITREP": str(after_sitrep)})
    if after_sitrep and not manifest_has_newer_records(after_sitrep):
        print(f"No SitReps newer than {after_sitrep}; skipping extraction and rendering.")
        return

    for step in DATA_STEPS:
        run_step(step)

    latest = latest_row()
    latest_sitrep = int(latest["sitrep"]) if latest["sitrep"] else 0
    if after_sitrep and latest_sitrep <= after_sitrep:
        print(
            f"No parsed SitRep newer than {after_sitrep}; "
            "skipping rendering and summary update."
        )
        return

    for step in RENDER_STEPS:
        run_step(step)

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

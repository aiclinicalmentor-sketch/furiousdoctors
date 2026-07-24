import csv
import re
from datetime import datetime
from pathlib import Path

import pdfplumber


REPO_ROOT = Path(__file__).resolve().parents[2]
WORK_DIR = REPO_ROOT / ".bundibugyo_work"
PDF_DIR = WORK_DIR / "DRC SitReps"
OUT_CSV = WORK_DIR / "sitrep_cumulative_cases.csv"

MONTHS_FR = {
    "janvier": 1,
    "fevrier": 2,
    "février": 2,
    "mars": 3,
    "avril": 4,
    "mai": 5,
    "juin": 6,
    "juillet": 7,
    "aout": 8,
    "août": 8,
    "septembre": 9,
    "octobre": 10,
    "novembre": 11,
    "decembre": 12,
    "décembre": 12,
}


def parse_french_date(value: str):
    value = re.sub(r"\s+", " ", value.strip().lower())
    match = re.search(r"(\d{1,2})\s+([a-zéûîôàèùç]+)\s+(\d{4})", value)
    if not match:
        return None
    day, month_name, year = match.groups()
    month = MONTHS_FR.get(month_name)
    if not month:
        return None
    return datetime(int(year), month, int(day)).date()


def parse_filename_date(name: str):
    patterns = [
        r"(\d{2})_(\d{2})_(\d{4})",
        r"(\d{2})-(\d{2})-(\d{4})",
        r"(\d{2})(\d{2})(\d{4})",
        r"(\d{4})(\d{2})(\d{2})",
    ]
    for pattern in patterns:
        match = re.search(pattern, name)
        if not match:
            continue
        parts = match.groups()
        try:
            if len(parts[0]) == 4:
                return datetime(int(parts[0]), int(parts[1]), int(parts[2])).date()
            return datetime(int(parts[2]), int(parts[1]), int(parts[0])).date()
        except ValueError:
            pass
    return None


def extract_text(path: Path) -> str:
    with pdfplumber.open(str(path)) as pdf:
        return "\n".join((page.extract_text() or "") for page in pdf.pages[:3])


def top_summary_cases(top_block: str, sitrep):
    if not top_block:
        return None

    if sitrep == 1:
        nums = [int(n) for n in re.findall(r"\b[0-9]+\b", top_block)]
        return nums[1] if len(nums) > 1 else None
    if sitrep == 2:
        nums = [int(n) for n in re.findall(r"\b[0-9]+\b", top_block)]
        return nums[2] if len(nums) > 2 else None

    before_cumul = re.split(r"Cumul\s+cas|Cas\s+Décès", top_block, flags=re.IGNORECASE)[0]
    candidate_lines = []
    for line in before_cumul.splitlines():
        stripped = line.strip()
        nums = re.findall(r"\b[0-9]+(?:\s[0-9]{3})?\b", stripped)
        if len(nums) >= 2 and re.match(r"^[0-9]", stripped):
            candidate_lines.append(nums)

    if candidate_lines:
        return int(candidate_lines[-1][0].replace(" ", ""))

    nums = [int(n) for n in re.findall(r"\b[0-9]+\b", top_block)]
    return nums[0] if nums else None


def parse_record(path: Path):
    text = extract_text(path)
    normalized = re.sub(r"[ \t]+", " ", text)

    sitrep = None
    sitrep_match = re.search(r"SitRep(?:\s+MVE)?\s*N[°º]?\s*([0-9]{1,3})", normalized, re.IGNORECASE)
    if sitrep_match:
        sitrep = int(sitrep_match.group(1))

    report_date = None
    date_match = re.search(r"Date de rapportage\s+([0-9]{1,2}\s+\w+\s+[0-9]{4})", normalized, re.IGNORECASE)
    if date_match:
        report_date = parse_french_date(date_match.group(1))
    if report_date is None:
        report_date = parse_filename_date(path.name)

    cases = None
    method = ""
    number_pattern = r"(?:[0-9]{1,3}(?:\s[0-9]{3})*|[0-9]+)"
    total_matches = re.findall(
        rf"(?m)^Total\s+({number_pattern})\s+{number_pattern}\s+[0-9,\.]+\s*%",
        normalized,
    )
    if total_matches:
        cases = int(re.sub(r"\s+", "", total_matches[-1]))
        method = "epidemiology_table_total"
    else:
        total_inline = re.findall(rf"Total\s+({number_pattern})\s+{number_pattern}\s+[0-9,\.]+\s*%", normalized)
        if total_inline:
            cases = int(re.sub(r"\s+", "", total_inline[-1]))
            method = "inline_total"

    if cases is None:
        key_indicator = re.search(
            r"CAS\s+CONFIRM[ÉE]S\s+[—-]\s+[0-9]\s+PROVINCES.*?\n\s*([0-9]+(?:\s+[0-9]{3})*)\s*\*?",
            text,
            re.IGNORECASE | re.DOTALL,
        )
        if key_indicator:
            cases = int(re.sub(r"\s+", "", key_indicator.group(1)))
            method = "key_indicators_confirmed_cases"

    top_block = ""
    top_block_match = re.search(
        r"Date de publication\s+[0-9]{1,2}\s+\w+\s+[0-9]{4}\s+(.*?)\s+(?:0\.|1\.|I\.|POINT|FAITS)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if top_block_match:
        top_block = top_block_match.group(1)

    if sitrep == 4:
        total_simple = re.findall(r"(?m)^Total\s+([0-9]{1,4})\s+", normalized)
        if total_simple:
            cases = int(total_simple[0])
            method = "early_simple_total"

    if cases is None:
        top_cases = top_summary_cases(top_block, sitrep)
        if top_cases is not None:
            cases = top_cases
            method = "top_summary"

    return {
        "file": path.name,
        "sitrep": sitrep,
        "report_date": report_date.isoformat() if report_date else "",
        "cumulative_confirmed_cases": cases if cases is not None else "",
        "method": method,
    }


def main():
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    for path in sorted(PDF_DIR.glob("*.pdf")):
        try:
            rows.append(parse_record(path))
        except Exception as exc:
            rows.append(
                {
                    "file": path.name,
                    "sitrep": "",
                    "report_date": "",
                    "cumulative_confirmed_cases": "",
                    "method": "",
                    "error": str(exc),
                }
            )

    for row in rows:
        row.setdefault("error", "")
        row.setdefault("method", "")

    with OUT_CSV.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["report_date", "sitrep", "cumulative_confirmed_cases", "method", "file", "error"],
        )
        writer.writeheader()
        writer.writerows(rows)

    parsed = [r for r in rows if r["report_date"] and r["cumulative_confirmed_cases"] != ""]
    print(f"parsed={len(parsed)} total_pdfs={len(rows)} csv={OUT_CSV}")
    for row in sorted(parsed, key=lambda r: (r["report_date"], r["sitrep"] or 0, r["file"])):
        print(f"{row['report_date']} sitrep={row['sitrep']} cases={row['cumulative_confirmed_cases']} file={row['file']}")


if __name__ == "__main__":
    main()

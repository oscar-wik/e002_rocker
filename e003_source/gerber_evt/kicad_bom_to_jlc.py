#!/usr/bin/env python3
from __future__ import annotations

import csv
import sys
from pathlib import Path


JLC_HEADERS = ["Comment", "Designator", "Footprint", "JLCPCB Part #（optional）"]


def is_truthy(s: str | None) -> bool:
    return bool(s and s.strip())


def norm(s: str | None) -> str:
    return (s or "").strip()


def strip_footprint(fp: str) -> str:
    """
    KiCad often outputs 'lib:FootprintName'. JLC typically wants just the footprint name.
    Example: 'smv_footprints:C_0805_2012Metric' -> 'C_0805_2012Metric'
    """
    fp = norm(fp)
    if ":" in fp:
        return fp.split(":", 1)[1].strip()
    return fp


def pick_jlc_part_number(row: dict[str, str]) -> str:
    """
    Try common column names people use for LCSC/JLC part numbers.
    If not present, return ''.
    """
    candidates = [
        "JLCPCB Part #（optional）",
        "JLCPCB Part #",
        "JLC Part #",
        "JLC",
        "LCSC",
        "LCSC Part",
        "LCSC Part #",
        "Part #",
        "PartNumber",
    ]
    for k in candidates:
        if k in row and is_truthy(row.get(k)):
            return norm(row.get(k))
    return ""


def make_comment(row: dict[str, str]) -> str:
    """
    Your rule:
    - Generic parts: use VALUE (Value column)
    - Non-generic: use MANF + MPN together
    """
    manf = norm(row.get("manf"))
    mpn = norm(row.get("mpn"))
    value = norm(row.get("Value"))

    # Treat missing manf as generic (since you said "non generic parts" use manf+mpn)
    is_generic = (not is_truthy(manf)) or (manf.lower() == "generic")

    if is_generic:
        return value

    # Non-generic: combine MANF + MPN (in that order)
    if is_truthy(manf) and is_truthy(mpn):
        return f"{manf} {mpn}"
    return manf or mpn


def should_skip(row: dict[str, str]) -> bool:
    """
    Optional: skip DNP rows if DNP column is set.
    Your BOM has "DNP" column, currently empty in your sample.
    """
    dnp = norm(row.get("DNP"))
    return is_truthy(dnp) and dnp not in ("0", "false", "no", "n")


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python kicad_bom_to_jlc.py <input_bom.csv> <output_jlc_bom.tsv>", file=sys.stderr)
        return 2

    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])

    if not in_path.exists():
        print(f"Input file not found: {in_path}", file=sys.stderr)
        return 2

    with in_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            print("Could not read CSV header.", file=sys.stderr)
            return 1

        rows_out: list[dict[str, str]] = []

        for row in reader:
            # Skip DNP if set
            if should_skip(row):
                continue

            designator = norm(row.get("Reference"))
            if not is_truthy(designator):
                continue

            footprint = strip_footprint(row.get("Footprint") or "")
            comment = make_comment(row)
            jlc_pn = pick_jlc_part_number(row)

            rows_out.append(
                {
                    "Comment": comment,
                    "Designator": designator,
                    "Footprint": footprint,
                    "JLCPCB Part #（optional）": jlc_pn,
                }
            )

    # Write as TSV (tab-separated) to match what JLC often accepts nicely
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=JLC_HEADERS, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows_out)

    print(f"Wrote {len(rows_out)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

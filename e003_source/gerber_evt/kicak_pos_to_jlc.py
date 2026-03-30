#!/usr/bin/env python3
"""
Convert KiCad footprint position file (space-aligned text with comments)
to JLCPCB pick-and-place CSV format:

Designator,Mid X,Mid Y,Layer,Rotation
C1,95.0518mm,22.6822mm,Top,270
...

Usage:
  python kicad_pos_to_jlc.py input.pos output.csv
"""

from __future__ import annotations

import csv
import re
import sys
from pathlib import Path


def normalize_rotation(rot_deg: float) -> int:
    """Normalize rotation to [0, 360) and return as int degrees."""
    # KiCad may emit -90.0000; JLC commonly accepts 270.
    r = rot_deg % 360.0
    # Round to nearest int (KiCad writes with .0000, but be tolerant)
    return int(round(r)) % 360


def parse_kicad_pos_lines(lines: list[str]) -> list[dict[str, str]]:
    """
    Parse KiCad pos text. Expected columns (in header):
      Ref Val Package PosX PosY Rot Side
    We'll use Ref, PosX, PosY, Rot, Side.
    """
    rows: list[dict[str, str]] = []

    # Split on 2+ spaces OR tabs (KiCad file is typically aligned with spaces)
    splitter = re.compile(r"(?:\t+| {2,})")

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("##") or line.startswith("###"):
            continue

        parts = splitter.split(line)
        # Typical parts: [Ref, Val, Package, PosX, PosY, Rot, Side]
        if len(parts) < 7:
            # Not a data line, skip
            continue

        ref = parts[0].strip()
        posx = parts[-4].strip()
        posy = parts[-3].strip()
        rot = parts[-2].strip()
        side = parts[-1].strip().lower()

        layer = "Top" if side == "top" else "Bottom" if side == "bottom" else side.capitalize()

        try:
            x = float(posx)
            y = float(posy)
            r = float(rot)
        except ValueError:
            # If any numeric parse fails, skip the row
            continue

        rows.append(
            {
                "Designator": ref,
                "Mid X": f"{x:.4f}mm",
                "Mid Y": f"{y:.4f}mm",
                "Layer": layer,
                "Rotation": str(normalize_rotation(r)),
            }
        )

    return rows


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python kicad_pos_to_jlc.py <input.pos> <output.csv>", file=sys.stderr)
        return 2

    in_path = Path(sys.argv[1])
    out_path = Path(sys.argv[2])

    if not in_path.exists():
        print(f"Input file not found: {in_path}", file=sys.stderr)
        return 2

    lines = in_path.read_text(encoding="utf-8", errors="replace").splitlines()
    rows = parse_kicad_pos_lines(lines)

    if not rows:
        print("No rows parsed. Are you sure this is a KiCad footprint positions file?", file=sys.stderr)
        return 1

    # Write JLC CSV
    fieldnames = ["Designator", "Mid X", "Mid Y", "Layer", "Rotation"]
    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

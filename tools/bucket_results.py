#!/usr/bin/env python3
"""Bucket evaluated candidates into proceed/human_review/dismiss CSVs.

Usage:
  python tools/bucket_results.py path/to/evaluated.csv --outdir path/to/output

Assumptions:
- Input contains a column named `overall_decision` with values:
  PROCEED | HUMAN_REVIEW | DISMISS

This is intentionally simple and operator-friendly.
"""

import argparse
import csv
from pathlib import Path


def read_rows(path: Path):
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        return reader.fieldnames or [], rows


def write_rows(path: Path, fieldnames, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("evaluated_csv")
    ap.add_argument("--outdir", default="output")
    args = ap.parse_args()

    in_path = Path(args.evaluated_csv)
    outdir = Path(args.outdir)

    fieldnames, rows = read_rows(in_path)
    if not rows:
        raise SystemExit(f"No rows found in {in_path}")

    if "overall_decision" not in fieldnames:
        raise SystemExit("Missing required column: overall_decision")

    proceed = [r for r in rows if (r.get("overall_decision") or "").strip().upper() == "PROCEED"]
    human = [r for r in rows if (r.get("overall_decision") or "").strip().upper() == "HUMAN_REVIEW"]
    dismiss = [r for r in rows if (r.get("overall_decision") or "").strip().upper() == "DISMISS"]

    write_rows(outdir / "proceed.csv", fieldnames, proceed)
    write_rows(outdir / "human_review.csv", fieldnames, human)
    write_rows(outdir / "dismiss.csv", fieldnames, dismiss)

    print(f"[OK] proceed: {len(proceed)}")
    print(f"[OK] human_review: {len(human)}")
    print(f"[OK] dismiss: {len(dismiss)}")


if __name__ == "__main__":
    main()

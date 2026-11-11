#!/usr/bin/env python3
"""
anonymize_prolific_ids.py

Anonymize Prolific IDs in a CSV by replacing them with stable pseudonyms (P000001, P000002, ...).

This version OVERWRITES the ID column IN PLACE so the anonymized column name stays the same
(e.g., "ProlificID" stays "ProlificID", but values become P000001, P000002, ...).

- Detects the Prolific ID column automatically (if possible) or you can specify it.
- Writes:
  1) an anonymized CSV (with the same ID column name, but anonymized values)
  2) a mapping CSV (original_id -> anon_id) so you can reproduce / reverse if you keep it private.

Example:
  python anonymize_prolific_ids.py --input "/path/to/survey1_results.csv"

If the script can't detect the column:
  python anonymize_prolific_ids.py --input "/path/to/file.csv" --id-col "ProlificID"
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Optional, List

import pandas as pd


DEFAULT_CANDIDATES = [
    "prolific_id",
    "prolificid",
    "prolific id",
    "participant_id",
    "participantid",
    "participant id",
    "subject_id",
    "subjectid",
    "subject id",
    "respondent_id",
    "respondentid",
    "respondent id",
    "id",
]


def _normalize(s: str) -> str:
    return "".join(ch.lower() for ch in s.strip() if ch.isalnum() or ch.isspace()).replace(" ", "")


def guess_id_column(columns: List[str]) -> Optional[str]:
    """
    Try to find the most likely Prolific ID column.
    Priority:
      1) any column containing 'prolific'
      2) exact-ish matches to common candidate names
    """
    # 1) contains 'prolific'
    for c in columns:
        if "prolific" in c.lower():
            return c

    # 2) normalized matching
    norm_to_col = {_normalize(c): c for c in columns}
    for cand in DEFAULT_CANDIDATES:
        if _normalize(cand) in norm_to_col:
            return norm_to_col[_normalize(cand)]

    return None


def make_pseudonyms(series: pd.Series, prefix: str = "P"):
    """
    Create stable pseudonyms based on unique original values.
    Returns:
      - anon series aligned to original rows
      - mapping dataframe [original_id, anon_id]
    """

    # ---- Python 3.7 / older pandas friendly ----
    # Keep NaN as NaN, cast non-null values to str.
    original = series.where(series.isna(), series.astype(str))

    # ---- Newer pandas alternative (comment only) ----
    # original = series.astype("string")  # pandas "StringDtype" available in newer pandas versions

    uniques = pd.unique(original.dropna())

    width = max(6, len(str(len(uniques))))
    anon_ids = [f"{prefix}{i:0{width}d}" for i in range(1, len(uniques) + 1)]
    mapping = pd.DataFrame({"original_id": uniques, "anon_id": anon_ids})

    map_dict = dict(zip(mapping["original_id"], mapping["anon_id"]))
    anon_col = original.map(map_dict)

    return anon_col, mapping


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", "-i", required=True, help="Path to input CSV")
    ap.add_argument("--output", "-o", default=None, help="Path to output anonymized CSV")
    ap.add_argument("--mapping", "-m", default=None, help="Path to output mapping CSV (KEEP PRIVATE)")
    ap.add_argument("--id-col", default=None, help="Name of the column containing Prolific IDs")
    ap.add_argument("--prefix", default="P", help="Prefix for pseudonyms (default: P)")
    args = ap.parse_args()

    in_path = args.input
    if not os.path.exists(in_path):
        print(f"ERROR: Input file not found: {in_path}", file=sys.stderr)
        sys.exit(1)

    df = pd.read_csv(in_path)

    # Determine ID column
    id_col = args.id_col
    if id_col is None:
        id_col = guess_id_column(list(df.columns))

    if id_col is None or id_col not in df.columns:
        print("ERROR: Could not determine the Prolific ID column.", file=sys.stderr)
        print("Available columns:", list(df.columns), file=sys.stderr)
        print("Re-run with: --id-col \"<exact column name>\"", file=sys.stderr)
        sys.exit(1)

    # Create anonymized IDs + mapping
    anon_series, mapping = make_pseudonyms(df[id_col], prefix=args.prefix)

    # ---- KEY CHANGE: overwrite the original column so the name stays the same ----
    df[id_col] = anon_series

    # ---- Previous (older) behavior (comment only) ----
    # df[args.anon_col] = anon_series
    # if args.drop_original:
    #     df = df.drop(columns=[id_col])

    # Default outputs
    base, ext = os.path.splitext(in_path)
    out_path = args.output or f"{base}.anonymized.csv"
    map_path = args.mapping or f"{base}.id_mapping.csv"

    # Write
    df.to_csv(out_path, index=False)
    mapping.to_csv(map_path, index=False)

    print("✅ Done.")
    print(f"Anonymized CSV: {out_path}")
    print(f"Mapping CSV (keep private): {map_path}")
    print(f"ID column anonymized in-place: {id_col}")


if __name__ == "__main__":
    main()

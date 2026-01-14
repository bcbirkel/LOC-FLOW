#!/usr/bin/env python3
"""
Update the 1D model block inside a hypoDD RELOC.INP-style file.

Given:
  1) an input .inp file that contains a "*--- 1D model:" block with:
       * NLAY  RATIO
         <nlay> <ratio>
       * TOP
         <tops...>
       * VEL
         <vels...>
  2) a model table (depth, Vp, Vs, ...)

This script:
  - Computes average Vp/Vs ratio from the model table (simple arithmetic mean).
  - Sets NLAY = number of rows in the model table.
  - Sets TOP = the list of depths from the model table (first column).
  - Sets VEL = the list of Vp values from the model table (second column).
  - Leaves ALL other content in the .inp file unchanged.
  - Rewrites only the numeric content under NLAY/RATIO, TOP, VEL in that block.

Usage:
  python update_hypodd_inp.py \
      --inp hypoDD_orig.inp \
      --model_table ../lower_model/model_files/lowered_hypoDD_inp_model.nd \
      --out hypoDD.inp

Notes:
  - Formatting: TOP and VEL are written with a fixed count per line (default 8).
  - RATIO is written with 2 decimals by default (change via --ratio_decimals).
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import List, Tuple


FLOAT_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


def parse_model_table(text: str) -> List[Tuple[float, float, float]]:
    """
    Parse a whitespace-separated table where the first three columns are:
      depth_km, vp_kms, vs_kms
    Ignores blank lines and comment lines starting with '*' or '#'.
    """
    rows: List[Tuple[float, float, float]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("*") or line.startswith("#"):
            continue
        parts = line.split()
        if len(parts) < 3:
            continue
        try:
            depth = float(parts[0])
            vp = float(parts[1])
            vs = float(parts[2])
        except ValueError:
            continue
        rows.append((depth, vp, vs))

    if not rows:
        raise ValueError("No valid rows found in model table (need >=1 row with 3 numeric columns).")

    # Ensure depths are non-decreasing (common expectation for TOP list)
    # If not sorted, sort by depth.
    if any(rows[i][0] > rows[i + 1][0] for i in range(len(rows) - 1)):
        rows = sorted(rows, key=lambda r: r[0])

    return rows


def mean_vp_vs_ratio(rows: List[Tuple[float, float, float]]) -> float:
    ratios = [vp / vs for _, vp, vs in rows if vs != 0.0]
    if not ratios:
        raise ValueError("All Vs values are zero; cannot compute Vp/Vs ratio.")
    return sum(ratios) / len(ratios)


def format_numbers(nums: List[float], per_line: int, fmt: str) -> str:
    """
    Format a list of floats into multiple lines with `per_line` values each.
    """
    lines = []
    for i in range(0, len(nums), per_line):
        chunk = nums[i : i + per_line]
        lines.append(" ".join(fmt.format(x) for x in chunk))
    return "\n".join(lines)


def update_1d_model_block(inp_text: str,
                          tops: List[float],
                          vels: List[float],
                          ratio: float,
                          nlay: int,
                          per_line: int = 8,
                          ratio_decimals: int = 2) -> str:
    """
    Replace only the numeric content for NLAY/RATIO, TOP, and VEL inside the "*--- 1D model:" block.
    Keeps all other lines (comments, other sections) the same.
    """

    # We find the 1D model block by anchoring on "*--- 1D model:" and then locating
    # the sections:
    #   * NLAY  RATIO
    #     <numbers>
    #   * TOP
    #     <numbers...>
    #   * VEL
    #     <numbers...>
    #
    # We then replace the numeric lines for those parts only.
    #
    # This is intentionally tolerant to extra whitespace and line breaks.

    # Helper: consume numeric lines after a header line until a non-numeric-ish line
    def is_numeric_line(s: str) -> bool:
        st = s.strip()
        if not st:
            return False
        if st.startswith("*"):
            return False
        # must contain at least one float and only be floats/whitespace
        tokens = st.split()
        if not tokens:
            return False
        return all(FLOAT_RE.fullmatch(tok) for tok in tokens)

    lines = inp_text.splitlines()
    out_lines = lines[:]  # copy

    # Locate "*--- 1D model:" line index
    try:
        model_start = next(i for i, ln in enumerate(lines) if ln.strip().startswith("*--- 1D model:"))
    except StopIteration:
        raise ValueError('Could not find a line starting with "*--- 1D model:" in the input file.')

    # From model_start onward, find the key header lines
    def find_from(start_idx: int, predicate) -> int:
        for i in range(start_idx, len(lines)):
            if predicate(lines[i]):
                return i
        return -1

    nlay_hdr = find_from(model_start, lambda s: s.strip().startswith("* NLAY") and "RATIO" in s)
    if nlay_hdr == -1:
        raise ValueError('Could not find "* NLAY  RATIO" line inside the 1D model block.')

    # The numeric line with nlay and ratio should be after header (skip any comment/blank lines)
    i = nlay_hdr + 1
    while i < len(lines) and (lines[i].strip() == "" or lines[i].strip().startswith("*")):
        i += 1
    if i >= len(lines) or not is_numeric_line(lines[i]):
        raise ValueError("Could not find numeric NLAY/RATIO line after '* NLAY  RATIO'.")

    nlay_ratio_line_idx = i

    top_hdr = find_from(nlay_ratio_line_idx + 1, lambda s: s.strip().startswith("* TOP"))
    if top_hdr == -1:
        raise ValueError('Could not find "* TOP" line after NLAY/RATIO.')

    vel_hdr = find_from(top_hdr + 1, lambda s: s.strip().startswith("* VEL"))
    if vel_hdr == -1:
        raise ValueError('Could not find "* VEL" line after TOP.')

    # Determine the span of numeric lines under TOP (from first numeric after * TOP up to just before * VEL)
    top_data_start = top_hdr + 1
    while top_data_start < len(lines) and (lines[top_data_start].strip() == "" or lines[top_data_start].strip().startswith("*")):
        top_data_start += 1

    top_data_end = top_data_start
    while top_data_end < len(lines) and is_numeric_line(lines[top_data_end]):
        top_data_end += 1
    # top numeric lines are [top_data_start, top_data_end)

    # Determine the span of numeric lines under VEL (from first numeric after * VEL until next '*' section or EOF)
    vel_data_start = vel_hdr + 1
    while vel_data_start < len(lines) and (lines[vel_data_start].strip() == "" or lines[vel_data_start].strip().startswith("*")):
        vel_data_start += 1

    vel_data_end = vel_data_start
    while vel_data_end < len(lines) and is_numeric_line(lines[vel_data_end]):
        vel_data_end += 1
    # vel numeric lines are [vel_data_start, vel_data_end)

    # Build replacement text
    ratio_fmt = f"{{:.{ratio_decimals}f}}"
    # Keep the original spacing style roughly: nlay as int, ratio with decimals
    out_lines[nlay_ratio_line_idx] = f"{nlay:5d}     {ratio_fmt.format(ratio)}"

    top_block = format_numbers(tops, per_line=per_line, fmt="{:.2f}")
    vel_block = format_numbers(vels, per_line=per_line, fmt="{:.2f}")

    # Replace TOP numeric lines
    top_block_lines = top_block.splitlines()
    out_lines[top_data_start:top_data_end] = top_block_lines

    # Adjust indices if TOP replacement changed line count
    delta_top = len(top_block_lines) - (top_data_end - top_data_start)
    vel_hdr_new = vel_hdr + delta_top
    vel_data_start_new = vel_data_start + delta_top
    vel_data_end_new = vel_data_end + delta_top

    # Replace VEL numeric lines
    vel_block_lines = vel_block.splitlines()
    out_lines[vel_data_start_new:vel_data_end_new] = vel_block_lines

    return "\n".join(out_lines) + ("\n" if inp_text.endswith("\n") else "")


def main():
    ap = argparse.ArgumentParser(description="Update the 1D model block (NLAY/RATIO/TOP/VEL) inside RELOC.INP.")
    ap.add_argument("--inp", required=True, help="Path to input RELOC.INP (or similar) file.")
    ap.add_argument("--model_table", required=True, help="Path to model table text file (depth vp vs ...).")
    ap.add_argument("--out", required=True, help="Path to write updated INP.")
    ap.add_argument("--per_line", type=int, default=8, help="How many numbers per line for TOP and VEL (default: 8).")
    ap.add_argument("--ratio_decimals", type=int, default=2, help="Decimals for RATIO (default: 2).")
    args = ap.parse_args()

    inp_path = Path(args.inp)
    model_path = Path(args.model_table)
    out_path = Path(args.out)

    inp_text = inp_path.read_text()
    model_text = model_path.read_text()

    rows = parse_model_table(model_text)
    tops = [d for d, _, _ in rows]
    vels = [vp for _, vp, _ in rows]
    ratio = mean_vp_vs_ratio(rows)
    nlay = len(rows)

    updated = update_1d_model_block(
        inp_text,
        tops=tops,
        vels=vels,
        ratio=ratio,
        nlay=nlay,
        per_line=args.per_line,
        ratio_decimals=args.ratio_decimals,
    )

    out_path.write_text(updated)
    print(f"Wrote updated file: {out_path}")
    print(f"NLAY={nlay}, RATIO={ratio:.{args.ratio_decimals}f}")


if __name__ == "__main__":
    main()

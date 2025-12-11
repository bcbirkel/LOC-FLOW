#!/usr/bin/env python3
"""
make_mod_incr.py

Read a VELEST .mod file, smooth away low-velocity zones into a
monotonic profile (non-decreasing with depth) with small layer-to-layer
increases, then write a new file velest_incr.mod in the same directory
with rows:

depth  Vp  Vs  density  Qp  Qs

Also produces quick before/after plots for Vp and Vs.

Rules:
  - Use isotonic-like smoothing so LVZs become nearly constant segments.
  - Add tiny increments so velocities are strictly increasing with depth.
  - Ensure the first layer has lower velocity than the second layer
    (if not, make it slightly lower).

python make_mod_incr.py velest.mod

"""

import argparse
from pathlib import Path

import matplotlib.pyplot as plt

DENSITY = 2.60000
QP = 1456.0
QS = 600.0
EPS = 0.001  # small increment in km/s for strict increase


def isotonic_non_decreasing(values):
    """
    Classic Pool Adjacent Violators (PAV) isotonic regression:
    Find the non-decreasing sequence that is closest (L2) to 'values'.

    Returns a list of same length with non-decreasing values.
    """
    n = len(values)
    if n == 0:
        return []

    # Each block has an average value (v) and length (len)
    v = []
    w = []  # weights (all 1 here, but kept for completeness)
    lens = []

    for x in values:
        v.append(x)
        w.append(1.0)
        lens.append(1)
        j = len(v) - 1
        # Merge backwards while monotonicity violated
        while j > 0 and v[j - 1] > v[j]:
            total_w = w[j - 1] + w[j]
            new_v = (w[j - 1] * v[j - 1] + w[j] * v[j]) / total_w
            v[j - 1] = new_v
            w[j - 1] = total_w
            lens[j - 1] += lens[j]

            del v[j]
            del w[j]
            del lens[j]
            j -= 1

    # Expand block means back to full length
    result = []
    for val, ln in zip(v, lens):
        result.extend([val] * ln)
    return result


def smooth_velocity_profile(vels):
    """
    Take a velocity profile (list of floats) and:
      - Smooth LVZs into an isotonic (non-decreasing) profile.
      - Add tiny increments to make it strictly increasing.
      - Ensure v[0] < v[1] by a small margin.

    Returns a new list of velocities.
    """
    if len(vels) <= 1:
        return list(vels)

    # Step 1: isotonic (non-decreasing) smoothing
    sm = isotonic_non_decreasing(vels)

    # Step 2: enforce strictly increasing with small epsilon increments
    sm_strict = [sm[0]]
    for i in range(1, len(sm)):
        vi = sm[i]
        if vi <= sm_strict[i - 1]:
            vi = sm_strict[i - 1] + EPS
        sm_strict.append(vi)

    # Step 3: ensure first layer is lower than second
    if len(sm_strict) >= 2 and sm_strict[0] >= sm_strict[1]:
        sm_strict[0] = max(sm_strict[1] - EPS, 0.10)

    return sm_strict


def is_layer_count_line(line):
    """
    Heuristic: a 'layer count' line starts with an integer (e.g. '20')
    and may have comments following it.
    """
    stripped = line.strip()
    if not stripped:
        return False
    first = stripped.split()[0]
    return first.isdigit()


def parse_model_block(lines):
    """
    Parse a model block (list of strings) into velocities and depths.

    Each line is assumed to be: vel depth vdamp [comment...]
    """
    vels = []
    depths = []
    for line in lines:
        parts = line.strip().split()
        if len(parts) < 2:
            raise ValueError(f"Malformed model line: {line!r}")
        v = float(parts[0])
        d = float(parts[1])
        vels.append(v)
        depths.append(d)
    return vels, depths


def extract_p_s_models(lines):
    """
    From the full list of lines of a VELEST .mod file, extract
    the first two model blocks (P and S) as:

      (vp_list, depth_list), (vs_list, depth_list)

    Assumes VELEST-style:
      <header>
      layer_count_line_for_P
      <layer_count> lines of P model
      layer_count_line_for_S
      <layer_count> lines of S model
    """
    blocks = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]
        if is_layer_count_line(line):
            first = line.strip().split()[0]
            try:
                n_layers = int(first)
            except ValueError:
                i += 1
                continue

            start = i + 1
            end = start + n_layers
            if end > n:
                raise ValueError("Incomplete model block at end of file.")

            block_lines = lines[start:end]
            blocks.append(block_lines)
            i = end
        else:
            i += 1

    if len(blocks) < 2:
        raise ValueError("Could not find two model blocks (P and S) in the file.")

    # First block -> P, second -> S (standard VELEST layout)
    p_lines = blocks[0]
    s_lines = blocks[1]

    vp, depths_p = parse_model_block(p_lines)
    vs, depths_s = parse_model_block(s_lines)

    if len(depths_p) != len(depths_s) or any(
        dp != ds for dp, ds in zip(depths_p, depths_s)
    ):
        raise ValueError("P and S models have different depth grids; cannot combine safely.")

    return (vp, depths_p), (vs, depths_s)


def parse_args():
    ap = argparse.ArgumentParser(
        description="Create velest_incr.mod with smoothed monotonic Vp and Vs and quick plots."
    )
    ap.add_argument("input", help="Input VELEST .mod file (e.g., velest.mod)")
    return ap.parse_args()


def main():
    args = parse_args()
    in_path = Path(args.input)
    lines = in_path.read_text().splitlines(keepends=False)

    # Extract P and S models
    (vp_orig, depths), (vs_orig, depths_s) = extract_p_s_models(lines)

    # Smooth P and S profiles
    vp_smooth = smooth_velocity_profile(vp_orig)
    vs_smooth = smooth_velocity_profile(vs_orig)

    # Output file: velest_incr.mod in same directory
    out_path = in_path.with_name("velest_incr.mod")

    with out_path.open("w") as f:
        for d, vpv, vsv in zip(depths, vp_smooth, vs_smooth):
            # depth, Vp, Vs, density, Qp, Qs
            line = (
                f"{d:6.2f}   "
                f"{vpv:8.5f}   "
                f"{vsv:8.5f}   "
                f"{DENSITY:8.5f}   "
                f"{QP:7.1f}   "
                f"{QS:7.1f}\n"
            )
            f.write(line)

    print(f"Wrote smoothed combined model to {out_path}")

    # ---- Quick plots: Vp and Vs before vs after ----
    out_dir = in_path.parent
    vp_plot = out_dir / "velest_incr_Vp.png"
    vs_plot = out_dir / "velest_incr_Vs.png"

    # Vp plot
    plt.figure()
    plt.plot(vp_orig, depths, "o-", label="Vp original")
    plt.plot(vp_smooth, depths, "s-", label="Vp smoothed")
    plt.gca().invert_yaxis()
    plt.xlabel("Vp (km/s)")
    plt.ylabel("Depth (km)")
    plt.title("Vp model: original vs smoothed")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(vp_plot, dpi=150)
    plt.close()
    print(f"Saved Vp comparison plot to {vp_plot}")

    # Vs plot
    plt.figure()
    plt.plot(vs_orig, depths, "o-", label="Vs original")
    plt.plot(vs_smooth, depths, "s-", label="Vs smoothed")
    plt.gca().invert_yaxis()
    plt.xlabel("Vs (km/s)")
    plt.ylabel("Depth (km)")
    plt.title("Vs model: original vs smoothed")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(vs_plot, dpi=150)
    plt.close()
    print(f"Saved Vs comparison plot to {vs_plot}")


if __name__ == "__main__":
    main()

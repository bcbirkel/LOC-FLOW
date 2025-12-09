#!/usr/bin/env python3
"""
Plot travel time versus hypocenter distance from t_dist.dat, with
non-parametric travel-time curves (binned medians) for P and S, and
optional velocity table.

Expected t_dist.dat format (new AWK script):
    eventID  station  time  dist  phase_code

- eventID:    string
- station:    string
- time:       float (s)  [travel time]
- dist:       float (km) [hypocentral distance]
- phase_code: 1 for P, 2 for S
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path


def compute_limits(series, margin_frac=0.05):
    """Compute axis limits from data with a small margin."""
    s = series.dropna()
    if s.empty:
        return 0.0, 1.0
    vmin = s.min()
    vmax = s.max()
    if vmin == vmax:
        return vmin - 1.0, vmax + 1.0
    span = vmax - vmin
    margin = span * margin_frac
    return vmin - margin, vmax + margin


def binned_curve(df, bins):
    """
    Compute a non-parametric travel-time curve using common bins:
    - bins: array of bin edges of length nbins+1
    - Returns:
        centers: (nbins,) bin centers
        medians: (nbins,) median time (NaN if no data)
        q25:     (nbins,) 25% quantile (NaN if no data)
        q75:     (nbins,) 75% quantile (NaN if no data)
    """
    if df.empty:
        nbins = len(bins) - 1
        centers = 0.5 * (bins[:-1] + bins[1:])
        medians = np.full(nbins, np.nan)
        q25 = np.full(nbins, np.nan)
        q75 = np.full(nbins, np.nan)
        return centers, medians, q25, q75

    dist = df["dist"].values
    time = df["time"].values

    nbins = len(bins) - 1
    centers = 0.5 * (bins[:-1] + bins[1:])
    medians = np.full(nbins, np.nan)
    q25 = np.full(nbins, np.nan)
    q75 = np.full(nbins, np.nan)

    bin_idx = np.digitize(dist, bins) - 1  # 0..nbins-1

    for k in range(nbins):
        mask = bin_idx == k
        if not np.any(mask):
            continue
        t_bin = time[mask]
        medians[k] = np.median(t_bin)
        q25[k] = np.percentile(t_bin, 25)
        q75[k] = np.percentile(t_bin, 75)

    return centers, medians, q25, q75


def main(
    fname="t_dist.dat",
    outname="t_dist.png",
    nbins=20,
    include_table=True,
):
    fname = Path(fname)

    # Read space-delimited file with 5 columns
    df = pd.read_csv(
        fname,
        delim_whitespace=True,
        header=None,
        names=["event", "station", "time", "dist", "phase"],
    )

    df_P = df[df["phase"] == 1].copy()
    df_S = df[df["phase"] == 2].copy()

    print(f"Loaded {len(df)} picks from {fname}")
    print(f"P picks: {len(df_P)}, S picks: {len(df_S)}")

    # Print data ranges to sanity check
    for label, dsub in [("P", df_P), ("S", df_S)]:
        if dsub.empty:
            print(f"{label}: no data")
            continue
        print(
            f"{label}: dist in [{dsub['dist'].min():.3f}, {dsub['dist'].max():.3f}] km, "
            f"time in [{dsub['time'].min():.3f}, {dsub['time'].max():.3f}] s"
        )

    # Common distance bins across all data for comparability
    dist_all = df["dist"].dropna()
    if dist_all.empty:
        raise ValueError("No distance data in t_dist.dat")

    dmin, dmax = dist_all.min(), dist_all.max()
    if dmin == dmax:
        # Degenerate case: single distance
        dmin -= 0.5
        dmax += 0.5

    bins = np.linspace(dmin, dmax, nbins + 1)

    # Binned curves for P and S
    centers, med_P, q25_P, q75_P = binned_curve(df_P, bins)
    _, med_S, q25_S, q75_S = binned_curve(df_S, bins)

    # Velocities in each bin: v = r / t (km/s), using median t
    # Avoid division by zero / NaN
    vP = np.where(np.isfinite(med_P) & (med_P > 0), centers / med_P, np.nan)
    vS = np.where(np.isfinite(med_S) & (med_S > 0), centers / med_S, np.nan)

    # Axis limits from data
    dist_min_P, dist_max_P = compute_limits(df_P["dist"]) if not df_P.empty else (dmin, dmax)
    dist_min_S, dist_max_S = compute_limits(df_S["dist"]) if not df_S.empty else (dmin, dmax)
    time_min_P, time_max_P = compute_limits(df_P["time"]) if not df_P.empty else (0, 1)
    time_min_S, time_max_S = compute_limits(df_S["time"]) if not df_S.empty else (0, 1)

    dist_min = min(dist_min_P, dist_min_S)
    dist_max = max(dist_max_P, dist_max_S)
    time_min = min(time_min_P, time_min_S)
    time_max = max(time_max_P, time_max_S)

    if dist_min > 0:
        dist_min = 0.0
    if time_min > 0:
        time_min = 0.0

    # Figure layout: 1x2 or 1x3 depending on include_table
    ncols = 3 if include_table else 2
    fig, axes = plt.subplots(1, ncols, figsize=(5.5 * ncols, 5), sharey=True if ncols > 1 else False)

    # If only 2 columns, axes is length-2; if 3 columns, length-3
    axP = axes[0]
    axS = axes[1]

    # -------- P-wave subplot --------
    if not df_P.empty:
        axP.plot(df_P["dist"], df_P["time"], ".", markersize=2, alpha=0.4, label="P picks")

        maskP = np.isfinite(med_P)
        if np.any(maskP):
            xcP = centers[maskP]
            tmP = med_P[maskP]
            q25P = q25_P[maskP]
            q75P = q75_P[maskP]
            axP.fill_between(xcP, q25P, q75P, alpha=0.2, label="P 25–75%")
            axP.plot(xcP, tmP, "-", linewidth=2, label="P median curve")

    axP.set_xlim(dist_min, dist_max)
    axP.set_ylim(time_min, time_max)
    axP.set_title("t–dist curve of P")
    axP.set_xlabel("Hypocenter Distance (km)")
    axP.set_ylabel("Travel Time (s)")
    axP.legend(loc="best", fontsize=8)

    # -------- S-wave subplot --------
    if not df_S.empty:
        axS.plot(df_S["dist"], df_S["time"], ".", markersize=2, alpha=0.4, label="S picks")

        maskS = np.isfinite(med_S)
        if np.any(maskS):
            xcS = centers[maskS]
            tmS = med_S[maskS]
            q25S = q25_S[maskS]
            q75S = q75_S[maskS]
            axS.fill_between(xcS, q25S, q75S, alpha=0.2, label="S 25–75%")
            axS.plot(xcS, tmS, "-", linewidth=2, label="S median curve")

    axS.set_xlim(dist_min, dist_max)
    axS.set_ylim(time_min, time_max)
    axS.set_title("t–dist curve of S")
    axS.set_xlabel("Hypocenter Distance (km)")
    axS.legend(loc="best", fontsize=8)

    # -------- Table subplot (optional) --------
    if include_table:
        axT = axes[2]
        axT.axis("off")

        # Build table data as a pandas DataFrame for cleanliness
        table_df = pd.DataFrame(
            {
                "Bin center (km)": centers,
                "vP (km/s)": vP,
                "vS (km/s)": vS,
            }
        )

        # Round for nicer display
        table_df = table_df.round({"Bin center (km)": 1, "vP (km/s)": 2, "vS (km/s)": 2})

        # Optionally drop rows where both velocities are NaN (no data in that bin at all)
        mask_any = table_df[["vP (km/s)", "vS (km/s)"]].notna().any(axis=1)
        table_df = table_df[mask_any]

        cell_text = table_df.values.tolist()
        col_labels = list(table_df.columns)

        table = axT.table(
            cellText=cell_text,
            colLabels=col_labels,
            loc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.2)
        axT.set_title("Average velocities per bin")

    fig.tight_layout()
    fig.savefig(outname, dpi=200)
    print(f"Saved figure to {outname}")


if __name__ == "__main__":
    # Example usage:
    #   python plot_t_dist.py
    #
    # You can tweak nbins or disable table if it gets too tall:
    #   main(nbins=15, include_table=False)
    main(include_table=False)

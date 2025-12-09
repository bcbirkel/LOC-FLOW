import sys

# Here we didn't consider depth above the sea level to avoid negative depth
# velocity model is relative to the average of station elevation

def model_format(modelin):
    # Read all non-empty lines
    with open(modelin, "r") as f:
        raw_lines = [ln.strip() for ln in f if ln.strip()]

    crust_rows = []     # lines before 'mantle'
    mantle_row = None   # 'mantle' line itself (if it has numbers)
    mantle_next_row = None  # line after 'mantle' (if it has numbers)

    # Parse lines into tokens
    for idx, line in enumerate(raw_lines):
        parts = line.split()
        if not parts:
            continue

        # Look for the mantle marker
        if parts[0].lower() == "mantle":
            # If the 'mantle' line itself has depth, vp, vs
            if len(parts) >= 3:
                mantle_row = parts

            # If the next line has depth, vp, vs, use that preferentially
            if idx + 1 < len(raw_lines):
                next_parts = raw_lines[idx + 1].split()
                if len(next_parts) >= 3:
                    mantle_next_row = next_parts
            break
        else:
            crust_rows.append(parts)

    if not crust_rows:
        raise ValueError(f"No crustal layers found in {modelin} (no numeric lines before 'mantle').")

    # Choose which row to use for the upper mantle layer
    if mantle_next_row is not None:
        src = mantle_next_row
    elif mantle_row is not None:
        src = mantle_row
    else:
        # Fallback: use the last crustal layer
        src = crust_rows[-1]

    if len(src) < 3:
        raise ValueError(
            f"Cannot find a mantle line with depth/vp/vs in {modelin}. "
            f"Got: {src}"
        )

    dep_1 = float(src[0]) + 0.1  # HYPOINVERSE doesn't like same depth
    vp_1 = float(src[1])
    vs_1 = float(src[2])

    # --------- Write Vp model --------- #
    with open("vel_model_P.crh", "w") as gg:
        gg.write("MODEL Vp from REAL\n")
        for row in crust_rows:
            if len(row) < 2:
                continue
            dep = float(row[0])
            vp = float(row[1])
            gg.write("{:4.2f}  {:5.2f}\n".format(vp, dep))
        # include the upper mantle layer
        gg.write("{:4.2f}  {:5.2f}\n".format(vp_1, dep_1))

    # --------- Write Vs model --------- #
    with open("vel_model_S.crh", "w") as gg:
        gg.write("MODEL Vs from REAL\n")
        for row in crust_rows:
            if len(row) < 3:
                continue
            dep = float(row[0])
            vs = float(row[2])
            gg.write("{:4.2f}  {:5.2f}\n".format(vs, dep))
        # include the upper mantle layer
        gg.write("{:4.2f}  {:5.2f}\n".format(vs_1, dep_1))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("mk_velmodel.py modelfile")
        sys.exit(1)
    model_format(sys.argv[1])

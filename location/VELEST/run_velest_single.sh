#!/bin/bash
# input 1: location alone
#       0: location + model + sta. corr.
((!$#)) && echo bash $0 0,1 && exit 1
######################## step 1 (cookbook 3.2, 3a) ##################
# change parameters as needed
lat=28 # reference latitude
lon=85.6 # reference longitude 
distmax=100 # largest distance (stations with larger distance will be neglected) 
mode=$1 # 1: update locations alone (fast, usually good enough for your study) 
           # 0: first udpate locations and velocitiy using high-quanlity events and picks
           #    second relocate all events (slow, only for specific analysis), 

station=../../Data/station_all.dat # station direcotry
vel=../../REAL/tt_db/mymodel_welev.nd # velocity model directory
# vel=low_near_surface.nd # velocity model directory

# phasein_best=../../REAL/phase_best_allday.txt # use the SA locations (for mode = 0 only)
# phasein=../../REAL/phase_allday.txt # use the relocated SA locations
picker="STALTA" #("STALTA" "PhaseNet" "QMigrate")

echo "=============================="
echo " Running VELEST for $picker"
echo "=============================="

phasein_best=../../REAL/runs/$picker/phase_best_allday.txt
phasein=../../REAL/runs/$picker/phase_allday.txt

####################### step 2 (cookbook 3.2, 3b)#####################
# run velest with different options
if (($mode == 1))
then
    # location alone
    # prepare the required phase file, velocity file, station file, and velest control file following VELEST's format
    perl convertformat_updated.pl $lat $lon $distmax $mode $station $vel $phasein
    echo perl convertformat_updated.pl $lat $lon $distmax $mode $station $vel $phasein
    # run velest
    velest
elif (($mode == 0))
then
    # 1. update location, velocity, station correction using high-quanlity events and picks
    # please go to convertformat.pl and change the vel and sta. corr. damping following the VELEST manual
    perl convertformat_updated.pl $lat $lon $distmax $mode $station $vel $phasein_best
    # run velest, adjust parameters in covertformat.pl following velest's manual
    velest

    # Convert velout.mod to model1.nd
    infile="velout.mod"
    outfile="model1.nd"
    echo "Converting VELEST output model $infile to $outfile"
    # Constants for the last 3 columns
    DENSITY=2.6
    QP=1456.0
    QS=600.0
    awk -v dens="$DENSITY" -v qp="$QP" -v qs="$QS" '
    BEGIN { state = 0; }
    /Output model:/ { state = 1; next }
    state == 1 && NF == 1 { num_p_layers = $1; p_count = 0; state = 2; next }
    state == 2 && NF >= 2 {
        vp[$2] = $1
        p_count++
        if (p_count == num_p_layers) { state = 3 }
        next
    }
    state == 3 && NF == 1 { num_s_layers = $1; s_count = 0; state = 4; next }
    state == 4 && NF >= 2 {
        vs[$2] = $1
        s_count++
        if (s_count == num_s_layers) { state = 5 }
        next
    }
    END {
        n = 0
        for (d_str in vp) {
            if (d_str in vs) { depth_list[++n] = d_str }
        }
        for (i = 1; i <= n; i++) {
            for (j = i + 1; j <= n; j++) {
                if (depth_list[i]+0 > depth_list[j]+0) {
                    tmp = depth_list[i]; depth_list[i] = depth_list[j]; depth_list[j] = tmp
                }
            }
        }
        for (i = 1; i <= n; i++) {
            d = depth_list[i]
            printf "%5.2f %10.5f %10.5f %10.5f %9.1f %9.1f\n", d, vp[d], vs[d], dens, qp, qs
        }
    }' "$infile" > "$outfile"
    echo "Wrote converted model to: $outfile"

    # 2. run velest to locate all events using updated velocity model and station corrections
    perl convertformat_updated.pl $lat $lon $distmax 1 $station $outfile $phasein

    mv sta.COR velest.sta # use updated station corrections

    # run velest
    velest
elif (($mode == 2))
then
    if [[ $# -lt 3 ]]; then
        echo "Usage for mode 2: $0 2 input_model.nd max_iterations" >&2
        exit 1
    fi
    vel_iter_initial=$2
    max_iter=$3

    echo "Running VELEST iterative model update for up to $max_iter iterations."
    echo "Initial model: $vel_iter_initial"

    cp "$vel_iter_initial" "model0.nd"
    declare -a changes
    final_model="model0.nd"

    for (( i=1; i<=$max_iter; i++ )); do
        vel_iter="model$((i-1)).nd"
        outfile="model$i.nd"

        echo "========================================="
        echo " Running VELEST iteration $i / $max_iter"
        echo " Input: $vel_iter, Output: $outfile"
        echo "========================================="

        # 1. run velest to update velocity model
        perl convertformat_updated.pl $lat $lon $distmax 0 $station "$vel_iter" $phasein_best
        velest

        # Convert velout.mod to next iteration model file
        infile="velout.mod"
        echo "Converting VELEST output model $infile to $outfile"
        # Constants for the last 3 columns
        DENSITY=2.6
        QP=1456.0
        QS=600.0
        awk -v dens="$DENSITY" -v qp="$QP" -v qs="$QS" '
        BEGIN { state = 0; }
        /Output model:/ { state = 1; next }
        state == 1 && NF == 1 { num_p_layers = $1; p_count = 0; state = 2; next }
        state == 2 && NF >= 2 {
            vp[$2] = $1
            p_count++
            if (p_count == num_p_layers) { state = 3 }
            next
        }
        state == 3 && NF == 1 { num_s_layers = $1; s_count = 0; state = 4; next }
        state == 4 && NF >= 2 {
            vs[$2] = $1
            s_count++
            if (s_count == num_s_layers) { state = 5 }
            next
        }
        END {
            n = 0
            for (d_str in vp) {
                if (d_str in vs) { depth_list[++n] = d_str }
            }
            for (i = 1; i <= n; i++) {
                for (j = i + 1; j <= n; j++) {
                    if (depth_list[i]+0 > depth_list[j]+0) {
                        tmp = depth_list[i]; depth_list[i] = depth_list[j]; depth_list[j] = tmp
                    }
                }
            }
            for (i = 1; i <= n; i++) {
                d = depth_list[i]
                printf "%5.2f %10.5f %10.5f %10.5f %9.1f %9.1f\n", d, vp[d], vs[d], dens, qp, qs
            }
        }' "$infile" > "$outfile"
        echo "Wrote converted model to: $outfile"

        # Calculate sum of absolute changes from previous model
        read dVp dVs <<< $(awk '
            FNR==NR { vp_prev[FNR]=$2; vs_prev[FNR]=$3; next }
            FNR > length(vp_prev) { exit } # Stop if layer counts differ
            {
                vp_abs_diff = $2 - vp_prev[FNR]; if (vp_abs_diff < 0) vp_abs_diff = -vp_abs_diff;
                vs_abs_diff = $3 - vs_prev[FNR]; if (vs_abs_diff < 0) vs_abs_diff = -vs_abs_diff;
                total_vp_diff += vp_abs_diff
                total_vs_diff += vs_abs_diff
            }
            END { print total_vp_diff, total_vs_diff }
        ' "$vel_iter" "$outfile")

        if [[ -z "$dVp" || -z "$dVs" ]]; then
            echo "Warning: Could not calculate velocity change, possibly due to mismatched layers. Stopping iteration."
            final_model="$vel_iter"
            break
        else
            total_change=$(echo "$dVp + $dVs" | bc)
        fi
        changes+=($total_change)
        echo "Iteration $i: Sum of absolute changes (Vp+Vs) = $total_change"

        final_model="$outfile" # Update final model each iteration

        # Check for convergence after at least 3 iterations
        if [[ $i -ge 3 ]]; then
            idx=$i-1 # index in changes array
            c1=${changes[$idx-2]}
            c2=${changes[$idx-1]}
            c3=${changes[$idx]}

            is_stable=0
            if (( $(echo "$c1 == 0" | bc -l) )) || (( $(echo "$c2 == 0" | bc -l) )); then
                is_stable=0
            else
                cond1=$(echo "scale=4; val=(($c3 - $c2) / $c2); val < 0.05 && val > -0.05" | bc -l)
                cond2=$(echo "scale=4; val=(($c2 - $c1) / $c1); val < 0.05 && val > -0.05" | bc -l)
                if [[ $cond1 -eq 1 && $cond2 -eq 1 ]]; then is_stable=1; fi
            fi

            if [[ $is_stable -eq 1 ]]; then
                echo "Convergence reached after $i iterations. Model has stabilized."
                break
            fi
        fi

        if [[ $i -eq $max_iter ]]; then
            echo "Maximum number of iterations ($max_iter) reached."
        fi

        echo "Relocating all events with model: $final_model"
        perl convertformat_updated.pl $lat $lon $distmax 1 $station "$final_model" $phasein
        mv sta.COR velest.sta # use updated station corrections
        velest
    done

    # 2. run velest to relocate all events using the final model
    echo "Relocating all events with the final model: $final_model"
    perl convertformat_updated.pl $lat $lon $distmax 1 $station "$final_model" $phasein
    mv sta.COR velest.sta # use updated station corrections
    velest
else
    echo 'please choose your location mode 0, 1 or 2'
    echo 'Usage:'
    echo "  bash $0 0"
    echo "  bash $0 1"
    echo "  bash $0 2 input_model.nd max_iterations"
    exit
fi

####################### step 3 (cookbook 3.2, 3c)###################
# result format conversion and reselection
stationgap=300 # events with station gap larger than this will be discarded
resmax=2.0 # events with travel time residual larger than this will be discarded
relocatalog=new.cat # kept relocations
deletedcatalog=dele.cat # discarded relocations
# convert output location format
perl convertoutput.pl $stationgap $resmax $relocatalog $deletedcatalog
#Format: date, hh, mm, ss, lat, lon, dep, mag, station gap, res, num

wc -l initial.cat | awk '{ printf "before selection: %d events\n",$1}'
wc -l new.cat | awk '{ printf "after selection: %d events\n",$1}'

mkdir -p "$picker" && mv model*.nd *.cat *.sta *.OUT *.CHECK *.pha *.mod *.cmn *.CNV "$picker"/ 2>/dev/null

echo "Finished picker: $picker"
echo

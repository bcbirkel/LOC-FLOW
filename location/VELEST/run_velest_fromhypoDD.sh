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
pickers=("STALTA" "PhaseNet" "QMigrate")

for picker in "${pickers[@]}"; do
    echo "=============================="
    echo " Running VELEST for $picker"
    echo "=============================="

    phasein_best=../../hypoDD_dtct/$picker/hypoDD_best.pha
    phasein=../../hypoDD_dtct/$picker/hypoDD.pha

    ####################### step 2 (cookbook 3.2, 3b)#####################
    # run velest with different options
    if (($mode == 1))
    then
        # location alone
        # prepare the required phase file, velocity file, station file, and velest control file following VELEST's format
        perl convertformat_hypoDD.pl $lat $lon $distmax $mode $station $vel $phasein
        echo perl convertformat_hypoDD.pl $lat $lon $distmax $mode $station $vel $phasein
        # run velest
        velest
    elif (($mode == 0))
    then
        # 1. update location, velocity, station correction using high-quanlity events and picks
        # please go to convertformat.pl and change the vel and sta. corr. damping following the VELEST manual
        perl convertformat_hypoDD.pl $lat $lon $distmax $mode $station $vel $phasein_best
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
        perl convertformat_hypoDD.pl $lat $lon $distmax 1 $station $outfile $phasein

        mv sta.COR velest.sta # use updated station corrections

        # run velest
        velest
    elif (($mode == 2))
    then
        if [[ $# -lt 2 ]]; then
            echo "Usage for mode 2: $0 2 input_model.nd" >&2
            exit 1
        fi
        vel_iter=$2

        # Determine output file name
        if [[ $vel_iter =~ model([0-9]+)\.nd$ ]]; then
            num=${BASH_REMATCH[1]}
            outfile="model$((num + 1)).nd"
        else
            # if input is not modelN.nd, e.g. mymodel.nd, create model1.nd
            outfile="model1.nd"
        fi

        echo "Running VELEST iteration with input model $vel_iter, output will be $outfile"
        # 1. update location, velocity, station correction using high-quanlity events and picks
        perl convertformat_hypoDD.pl $lat $lon $distmax 0 $station "$vel_iter" $phasein_best
        # run velest
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

        # 2. run velest to relocate all events using the newly created model and station corrections
        echo "Relocating all events with the new model: $outfile"
        perl convertformat_hypoDD.pl $lat $lon $distmax 1 $station "$outfile" $phasein
        mv sta.COR velest.sta # use updated station corrections
        velest
    else
    echo 'please choose your location mode 0, 1 or 2'
    echo 'bash run_velest.sh 0, 1 or 2'
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

    mkdir -p "$picker" && mv *.cat velest.sta velout.mod *.OUT *.CHECK *.pha *.mod *.cmn *.CNV "$picker"/ 2>/dev/null

    echo "Finished picker: $picker"
    echo
done

echo "All pickers completed."
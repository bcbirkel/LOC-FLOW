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
vel=../../REAL/tt_db/mymodel.nd # velocity model directory
phasein_best=../../REAL/phase_best_allday.txt # use the SA locations (for mode = 0 only)
# phasein=../../REAL/phase_allday.txt # use the relocated SA locations
phasein=../../REAL/phase_allday.txt

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
    # 2. run velest to locate all events using updated velocity model
    perl convertformat_updated.pl $lat $lon $distmax 1 $station $vel $phasein

    mv sta.COR velest.sta # replace the station file (now you have updated station correction)
    mv velest.mod velest.mod.org # copy your original velocity model

    # Read the contents of velout.mod and extract the necessary lines
    {
        read -r header
        read -r num_layers
        echo "OutNepal1D-model (mod1.1)     Ref. station 2D12" > velest.mod
        echo "$num_layers        vel,depth,vdamp,phase (f5.2,5x,f7.2,2x,f7.3,3x,a1)" >> velest.mod
        read -r line
        echo "$line P-VELOCITY MODEL" >> velest.mod
        for i in {1..9}; do
            read -r line
            echo "$line" >> velest.mod
        done
        read -r num_layers
        echo "$num_layers" >> velest.mod
        read -r line
        echo "$line S-VELOCITY MODEL" >> velest.mod
        for i in {1..9}; do
            read -r line
            echo "$line" >> velest.mod
        done
    } < velout.mod
    # mv sta.COR velest.sta # replace the station file (now you have updated station correction)
    # mv velest.mod velest.mod.org # copy your original velocity model
    # mv velout.mod velest.mod # replace your original velocity model by the updated model
    # run velest
    velest
elif (($mode == 2))
then
    if [[ $# -lt 1 ]]; then
        echo "Usage: $0 input_model_file [output_file]" >&2
        exit 1
    fi

    infile="velest.mod"
    outfile="model1.nd"

    # Constants for the last 3 columns
    DENSITY=2.6      # g/cc (or whatever units you want)
    QP=1456.0
    QS=600.0

    awk -v dens="$DENSITY" -v qp="$QP" -v qs="$QS" '
    /P-VELOCITY MODEL/ { mode = "P"; next }
    /S-VELOCITY MODEL/ { mode = "S"; next }

    mode == "P" && NF >= 3 {
        # vp depth vdamp
        vp[$2] = $1
        next
    }

    mode == "S" && NF >= 3 {
        # vs depth vdamp
        vs[$2] = $1
        next
    }

    END {
        # Collect depths that exist in both P and S arrays
        for (d in vp) {
            if ((d in vs) && d >= -6 && d <= 51) {
                use_depth[d] = 1
            }
        }

        # Put depths into a list and sort numerically
        n = 0
        for (d in use_depth) {
            n++
            depths[n] = d
        }

        # Simple bubble sort (n is tiny here, so it’s fine)
        for (i = 1; i <= n; i++) {
            for (j = i + 1; j <= n; j++) {
                if (depths[i] > depths[j]) {
                    tmp = depths[i]
                    depths[i] = depths[j]
                    depths[j] = tmp
                }
            }
        }

        # Output: depth Vp Vs density Qp Qs
        for (i = 1; i <= n; i++) {
            d = depths[i]
            printf "%5.2f %10.5f %10.5f %10.5f %9.1f %9.1f\n",
                d, vp[d], vs[d], dens, qp, qs
        }
    }
    ' "$infile" > "$outfile"

    echo "Wrote converted model to: $outfile"

    vel=$outfile
    # 1. update location, velocity, station correction using high-quanlity events and picks
    # please go to convertformat.pl and change the vel and sta. corr. damping following the VELEST manual
    perl convertformat_updmod.pl $lat $lon $distmax 0 $station $vel $phasein_best
    # run velest, adjust parameters in covertformat.pl following velest's manual
    velest
    # # 2. run velest to locate all events using updated velocity model
    perl convertformat_updmod.pl $lat $lon $distmax 1 $station $vel $phasein

    # # mv sta.COR velest.sta # replace the station file (now you have updated station correction)
    # mv velest.mod velest.mod.1 # copy your original velocity model

    # Read the contents of velout.mod and extract the necessary lines
    {
        read -r header
        read -r num_layers
        echo "OutNepal1D-model (mod1.1)     Ref. station 2D12" > velest.mod
        echo "$num_layers        vel,depth,vdamp,phase (f5.2,5x,f7.2,2x,f7.3,3x,a1)" >> velest.mod
        read -r line
        echo "$line P-VELOCITY MODEL" >> velest.mod
        for i in {1..9}; do
            read -r line
            echo "$line" >> velest.mod
        done
        read -r num_layers
        echo "$num_layers" >> velest.mod
        read -r line
        echo "$line S-VELOCITY MODEL" >> velest.mod
        for i in {1..9}; do
            read -r line
            echo "$line" >> velest.mod
        done
    } < velout.mod
    # # mv sta.COR velest.sta # replace the station file (now you have updated station correction)
    # mv velest.mod velest.mod.2 # copy your original velocity model
    # mv velout.mod velest.mod # replace your original velocity model by the updated model
    # # run velest
    velest
else
   echo 'please choose your location mode 0 or 1'
   echo 'bash run_velest.sh 0 or 1'
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

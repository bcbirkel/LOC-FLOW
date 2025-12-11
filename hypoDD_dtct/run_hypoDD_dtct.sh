#!/bin/bash -w
((!$#)) && echo bash $0 0,1,2,3 && exit 1
# picker="QMigrate"
# picker="PhaseNet"
phaseout=hypoDD.pha; #phase format for hypoDD
stationin=../Data/station_filt.dat; #station list
stationout=station.dat; #station format by hypoDD


hypo=$1 #from your input

#########################step 1 (4a in cookbook)########################
#hypo=0 # use REAL's simulated annealing location
# hypo=1 # use velest location
# hypo=2 # use hypoinverse location
# hypo=3 # use hypoinverse_corr location

pickers=("STALTA" "PhaseNet" "QMigrate")

for picker in "${pickers[@]}"; do
    echo "========================================================"
    echo " Running VELEST-Hypoinverse Correlation for $picker"
    echo "========================================================"

        # BB change: flip lat/lon!!
        awk '{print($4,$1,$2)}' $stationin > $stationout
        rm $phaseout #delete previous phase file

        if (($hypo == 0))
        then    
                cp ../REAL/runs/$picker/phaseSA_allday.txt $phaseout
        elif (($hypo == 1))
        then
                rms_threshold=0.5 # in sec, events with rms larger than this will not be used
                gap_threshold=300 # in deg., events with station gap larger than this will not be used
                maxdep=40 # in km, events with larger depth will not be used (< dep in the timetable)
                phasein=../location/VELEST/$picker/final.CNV
                python velest2hypoDD.py $phasein $phaseout $rms_threshold $gap_threshold $maxdep
                echo python velest2hypoDD.py $phasein $phaseout $rms_threshold $gap_threshold $maxdep
        elif (($hypo == 2))
        then
                phasein="../location/hypoinverse/$picker/hypoOut.arc"
                rms_threshold=0.5 # in sec, events with rms larger than this will not be used
                gap_threshold=300 # in deg., events with station gap larger than this will not be used
                pick_nres=3       # if pick's residual larger than nres times event's rms
                                # the pick will not be used
                maxdep=40 # in km, events with larger depth will not be used (< dep in the timetable)
                maxdep_err=5 # in km, events with larger depth uncertainty will not be used
                maxdis_err=5 # in km, events with larger horizontal uncertainty will not be used
                python hypoinverse2hypoDD.py $phasein $phaseout $rms_threshold $gap_threshold $pick_nres $maxdep $maxdep_err $maxdis_err
                echo python hypoinverse2hypoDD.py $phasein $phaseout $rms_threshold $gap_threshold $pick_nres $maxdep $maxdep_err $maxdis_err
        elif (($hypo == 3))
        then
                phasein="../location/hypoinverse_corr/$picker/hypoOut.arc"
                rms_threshold=0.5 # in sec, events with rms larger than this will not be used
                gap_threshold=270 # in deg., events with station gap larger than this will not be used
                pick_nres=2       # if pick's residual larger than nres times event's rms
                                # the pick will not be used
                maxdep=40 # in km, events with larger depth will not be used (< dep in the timetable)
                maxdep_err=2 # in km, events with larger depth uncertainty will not be used
                maxdis_err=2 # in km, events with larger horizontal uncertainty will not be used
                python hypoinverse2hypoDD.py $phasein $phaseout $rms_threshold $gap_threshold $pick_nres $maxdep $maxdep_err $maxdis_err
                echo python hypoinverse2hypoDD.py $phasein $phaseout $rms_threshold $gap_threshold $pick_nres $maxdep $maxdep_err $maxdis_err
        else
                echo 'please select your location resources: 0, 1, 2, 3'
                exit
        fi

        #########################step 2 (4b in cookbook)########################
        rm dt.ct
        ph2dt ph2dt.inp

        #########################step 3 (4c in cookbook)########################
        hypoDD hypoDD.inp


    mkdir -p "$picker" && mv *.reloc *.reloc* *.log *.pha *.sta *.res *.dat "$picker"/ 2>/dev/null

    echo "Finished picker: $picker"
    echo
done

echo "All pickers completed."
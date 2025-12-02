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
    sed -i '1,21c\
InitNepal1D-modell (mod1.1 EK280993)     Ref. station 2D12\
 10        vel,depth,vdamp,phase (f5.2,5x,f7.2,2x,f7.3,3x,a1)\
 5.30       -5.00    1.000   P-VELOCITY MODEL\
 5.30        0.00    1.000\
 5.65        1.00    1.000\
 5.93        3.00    1.000\
 6.20        7.00    1.000\
 6.80       24.00    1.000\
 7.50       31.00    1.000\
 8.10       40.00    1.000\
 8.10       50.00    1.000\
 8.10       50.10    1.000\
 10\
 2.75       -5.00    1.000   S-VELOCITY MODEL\
 2.75        0.00    1.000\
 2.80        1.00    1.000\
 3.10        3.00    1.000\
 3.40        7.00    1.000\
 3.90       24.00    1.000\
 4.00       31.00    1.000\
 4.48       40.00    1.000\
 4.48       50.00    1.000\
 4.50       50.10    1.000' velout.mod
    mv sta.COR velest.sta # replace the station file (now you have updated station correction)
    mv velest.mod velest.mod.org # copy your original velocity model
    mv velout.mod velest.mod # replace your original velocity model by the updated model
    # run velest
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

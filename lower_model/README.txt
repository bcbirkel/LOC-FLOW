this directory is for scripts which take output from REAL and QMigrate -- catalogs and velocity models -- and lower all depths by 5km so that they are appropriately handled later in workflow.

VELEST input:
../../Data/station.dat
../../REAL/tt_db/mymodel.nd
../../REAL/phase_best_allday.txt [for mode=0 only]
../../REAL/phase_allday.txt

hypoinverse input:
../../REAL/tt_db/mymodel.nd
../../REAL/*.phase_sel.txt
../../REAL/tt_db/mymodel.nd
../../Data/station.dat

therefore, files which need to be adjusted are:

- station.dat
- mymodel.nd
- phase_best_allday.txt
- phase_allday.txt
- *.phase_sel.txt

To perform the depth lowering, execute the `run_lowering.sh` script from within this directory.
Make sure it is executable (`chmod +x run_lowering.sh`).

The script will copy the necessary files from the data directories, process them to adjust depths by 5km, and save the output with a `lowered_` prefix.

The logic for "lowering" is as follows:
- For stations (`station.dat`), elevation is decreased by 5km.
- For velocity model layers (`mymodel.nd`), depth is increased by 5km.
- For earthquake events (phase files), depth is increased by 5km.

This logic is implemented in the following Python scripts, which are called by `run_lowering.sh`:
- `lower_station_dat.py`
- `lower_mymodel_nd.py`
- `lower_phase_files.py`

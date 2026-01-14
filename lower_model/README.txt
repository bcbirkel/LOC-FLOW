Brianna Birkel, created 1/8/26

This directory is for scripts which take output from REAL and QMigrate (catalogs and velocity models) and 
lower all depths so that they are appropriately handled later in workflow.

** NOTE: The depth change value is not hardcoded. It must be provided as a command-line argument to the `run_lowering.sh` script.

VELEST input:
../../Data/station.dat
../../REAL/tt_db/mymodel_welev.nd
../../REAL/phase_best_allday.txt [for mode=0 only]
../../REAL/phase_allday.txt

hypoinverse input:
../../REAL/tt_db/mymodel_welev.nd
../../REAL/*.phase_sel.txt
../../Data/station.dat

therefore, files which need to be adjusted are:

- station.dat
- mymodel_welev.nd
- phase_best_allday.txt
- phase_allday.txt
- *.phase_sel.txt
- final.CNV

To perform the depth lowering, execute the `run_lowering.sh` script from within the `scripts` directory, providing the depth change in kilometers as an argument. For example:
`bash run_lowering.sh 0.75`

The script will create a `model_files` directory. Inside, it will copy the necessary original files to `model_files/original` and save the processed files (with adjusted depths) in `model_files`, prefixed with `lowered_`.

The logic for "lowering" is as follows:
- For stations (`station.dat`), elevation is decreased by the specified amount. The station file format is assumed to be `lat lon net station chan depth elev`.
- For velocity model layers (`mymodel_welev.nd`), depth is increased by the specified amount. Additionally, new layers at 1, 2, 3, and 4 km depth are interpolated.
- For earthquake events (phase files), depth is increased by the specified amount. The script `lower_phase_files.py` handles two main formats:
  - Event headers starting with `#` (`phase_allday.txt`/`phase_best_allday.txt`), where depth is the 9th column.
  - Event lines starting with an event index (`*.phase_sel.txt`), where depth is the 10th column.
- For earthquake events from VELEST (`final.CNV`), depth is increased by the specified amount. The script `lower_final_cnv.py` identifies event lines based on fixed-width columns and modifies the depth value.

This logic is implemented in the following Python scripts, which are called by `run_lowering.sh`:
- `lower_station_dat.py`
- `lower_mymodel_nd.py`
- `lower_phase_files.py`
- `lower_final_cnv.py`

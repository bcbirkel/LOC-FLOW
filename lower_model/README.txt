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

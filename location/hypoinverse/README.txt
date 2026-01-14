Brianna Birkel, created 1/13/26
some hypoinverse notes:

- can use station elevations and have model go above sea level with command CRE -- HOWEVER, this consistently produces
  poorer quality events (higher residuals and location uncertainty)
    --> one theory here is that layers in the real earth are more likely to mimic/be parallel to topography, so actually
        "flattening out" the stations and model might be relatively closer to real life. Could try artificially lifting all
        locations and model after the fact in 3D based on elevation.
    --> this is implemented using the various iterations of codes - i.e. hyp_test_welev.command, mk_velmodel_CRE_hypoi.py,
        run_hypoinverse_lowered.shd
    --> also often results in depths being so poorly constrained that they tend to collapse to the trial depth

- added some commands to all input files. Main changes:
    --> require higher min number of stations -- MIN 20
    --> make trial depth deeper and explicitly allow depth to float -- ZTR 20 F
    --> allow 50 iterations to converge rather than 20 -- CON 50 0.04 0.001 
        where 0.04 is default location uncertainty and 0.001 is default RMS in order to converge
    --> in model using elevation, downweighted S picks to 0.5 as this seems to constrain depth better -- SWT 0.5

- other important notes:
    --> current input file actually follows COP 3 and CAR 1 ("INPUT IS A HYPOINVERSE ARCHIVE-2000 FILE, NO SHADOWS")
        - this is set using the FIL command, which overwrites earlier format commands
    --> oddly, when using stations and model without elevations, lowering the depths phase files to the average 
        station depth (2 km) vs. leaving them at the same depth (holding the model constantly lowered by 2km) 
        makes very little difference in final locations/times. 2km is within the location error for some events
        but not all; suggests that (a) error might be underestimated and (b) velocity model is poor
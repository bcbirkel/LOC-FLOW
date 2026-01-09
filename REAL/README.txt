Running note - Brianna Birkel, created 1/8/26

In REAL, there are 2 options for locating events: 

1) associate picks using a 2-layer model (above sea level and below sea level) WITH station elevations 
    --> done by assuming vertical ray path and adding elevation * velocity above sea level to expected travel time

2) associate picks using a n-layer model, entirely below sea level, WITHOUT station elevations
    --> stations cannot be embedded in the model either, so best solution is to put sea level at average station elevation (~2km for Nepal stations)

runREAL_homo.pl uses (1), as this allows for the significant elevation differences (ranging from 0.8 to 3.3 km above sea level) 
to be accounted for, also of concern is systematic elevation changes across stations spatially

runREAL_lowered.pl uses (2) (although tt_db/model/station list need to be adjusted if lowering elevation changes in future runs), 
currently using a 1D model that has a top layer from 0-2km depth, then increasing in velocity with depth from there, with thinner layers
near the top and thicker layers near the bottom. Importantly, using this method will ignore station elevations, which could be off by
~1.5km in Z in either direction.

Unclear as of now (1/8/26) which method is more likely cause higher location uncertainty. Given that station elevations are known and 
velocity model is not, current run is using method (1) to eliminate introducing more sources of error and uncertainty.
 --> Note: after first 3 days ran, appears that homogenous method is generally performing well, see example output:
        before first selection: 1550
        remove duplicate events
        after first selection: 39
        before second selection: 39
        remove suspicious events, outlier picks and duplicate associated picks
        after second selection: 39
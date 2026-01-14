hypoDD.inp needs to be carefully tuned --

- want a CND (condition number) in iterations ~20-80
- damping ideally between 1-100
- current CND usually 200-500

how well conditioned the system is depends on a bunch of factors, e.g.
- P and S vs P only pccks (P only gives lower CND) by about 50%
- velocity model fitness (model5 from velest gives lower CND than model1)
---> could take hypoDD output, iterate VELEST, feed back into hypoDD again
- MINLNK in pd3dt.inp and OBSCT in hypoDD.inp
---> should have MINLNK >= OBSCT 
---> MINLNK = 40 threw MAXDATA error from hypoDD.inc
---> has some effect on CND but not a ton
---> lowered back to 8 and 8 after checking other params and this lowered CND so......
- weighting (haven't tested yet), although if only P and catalog are being used, 
  unclear if there is anything to weight? look at docs for this
- changing Vp/Vs ratio between 1.4 and 1.7 (usually ~1.6) shows little difference
- MAJOR CHANGES -- in pd2dt.inp:
    - setting MAXNGH (max number of neighbors per event) back to 10 instead of 50 
    - setting MAXOBS (max number of links per pair saved) back to 20 from 100
    *tl;dr don't fuck with the defaults here apparently...

**Read more in hypoDD docs/Ellsworth paper about tuning parameters.


!!! REMEMBER - HYPODD OUTPUTS ARE 2KM BELOW WHERE THEY ARE IN REALITY !!!
* This is a very simple hypoinverse test command file.
* It uses only a simple station and crust model file,
* with no station delay file or other options.
* Run hypoinverse, then type @test2000.hyp at the command prompt.

200 t 2000 0			/enable y2000 formats
H71 3 1 3			    /use new hypoinverse station format
DIS 4 50 1 3            /Main Distance weighting
RMS 4 0.16 1.5 3        /Residual weighting - BB change, originally RMS 4 0.16 1.5 3  
ERR 0.1                 /BB changed from 0.1
SWT 0.5                 /downweight S picks to half
CON 50 0.04 0.001       /BB add - 50 iterations to converge max
*POS 1.8
MIN 20                  /min number of stations - BB changed from 5
ZTR 20 F                 /trial depth
*WET 1. .5 .2 .1       /weighting by pick quality
*PRE 3, 3 0 0 9        /magnitude
* OUTPUT
ERF T
TOP F

STA 'station.dat'
LET 5 2 0                              /Net Sta Chn
TYP Read in crustal model(s):
CRE 1 'vel_model_P.crh'	2.75 T	    /read crust model for Vp
CRE 2 'vel_model_S.crh' 2.75 T	    /read crust model for Vs
SAL 1 2
PHS 'hypoinput.arc'		        /input phase file

FIL				        /automatically set phase format from file
ARC 'hypoOut.arc'		/output archive file
PRT 'prtOut.prt'		/output print file
SUM 'catOut.sum'        /output location summary
*RDM T
CAR 1
*LST 2
LOC				/locate the earthquake
*STO

#!/usr/bin/perl
# This is an updated version of convertformat.pl to generate VELEST input
# in a different format, and to allow selection of phases.
# isingle == 0: location+model updation; isingle == 1: location alone

@ARGV >= 7 || die "Usage: perl $0 latref lonref distmax isingle station velmodel phasein [phase_type]\n" .
                 "  phase_type can be 'P', 'S', or 'both' (default)\n";

$reflat = $ARGV[0];
$reflon = $ARGV[1];
$distmax = $ARGV[2];
$isingle = $ARGV[3];
$station = $ARGV[4];
$vel = $ARGV[5];
$phasein = $ARGV[6];
chomp($phasein);

my $phase_select = 'both';
if (defined $ARGV[7]) {
    $phase_select = lc($ARGV[7]);
    if ($phase_select ne 'p' && $phase_select ne 's' && $phase_select ne 'both') {
        die "Invalid phase_type. Must be 'P', 'S', or 'both'.\n";
    }
}

print "isingle = $isingle\n";
print "Phase selection: $phase_select\n";

if (-e "final.CNV"){`rm velest.* initial.cat final.CNV`;}

$reflon = $reflon*-1; # NOTE: western lon is positive in velest!!! e.g., 117.5W => 117.5
$iusestacorr = 0; # station correction used or not
$zmin = -5.0; # was -0.2 # the smallest depth allowed (e.g., -0.2 -> above the sea level)
$iuseelev = 1; # station elevation used or not (recommend: 0)
$lowvelocity = 1; # any low velocity layer in the region (recommend: 0)
$vthet = 10; # damping of velocity
$stathet = 1; # damping of station correction

if($isingle == 1){
    $ittmax = 99;
    $invertratio = 0;
}else{
    $ittmax = 50;
    $invertratio = 3;
}


##############################################
# station format conversion
##############################################
$stause = "velest.sta"; #station format for VELEST
open(JK,"<$station") or die "Could not open station file '$station': $!\n";
@par = <JK>;
close(JK);

if (scalar(@par) == 0) {
    die "Station file '$station' is empty.\n";
}

$p1=0;
$p2=1;
$p3=1;
$v1=0.00;
$v2=0.00;
open(OT,">$stause");
print OT "(a4,f7.4,a1,1x,f8.4,a1,1x,i4,1x,i1,1x,i3,1x,f5.2,2x,f5.2)\n";
#print OT "(a6,f7.4,a1,1x,f8.4,a1,1x,i4,1x,i1,1x,i3,1x,f5.2,2x,f5.2)\n"; #in modified code
foreach $_(@par){
	chomp($_);
	($lat,$lon,$net,$sta,$comp,$elev) = split(/\s+/, $_);
    #if(length($sta)>4){$sta = substr($sta,1,4);}  #in old code
	$vsn = "N";$vew = "E";
	if($lat < 0.0){$vsn = "S";$vsn = -1*$vsn;}
	if($lon < 0.0){$vew = "W";$lon = -1*$lon;}
    $p1 = $elev*1000;
	printf OT "%-4s%7.4f%1s %8.4f%s %4d %1d %3d %5.2f  %5.2f\n", substr($sta, 0, 4), $lat, $vsn, $lon, $vew, $p1, $p2, $p3, $v1, $v2;
	$p3++;
}
print OT "\n";
close(OT);

################################################
# velocity model format conversion
###############################################
$newvel = "velest.mod";
open(JK,"<$vel");
@par = <JK>;
close(JK);

open(NV,">$newvel") or die "cannot write to file '$file' [$!]]\n";
# the fist title line
print NV "InitNepal1D-modell (mod1.1 EK280993)     Ref. station 2D12\n";

for($i=0;$i<@par;$i++){
    chomp($par[$i]);
    $comp = substr($par[$i],0,6) eq "mantle";
    if($comp == 1){
        last;
    }
}
$nlayer = $i;

# the second line - indicate the number of layers for Vp
printf NV "%3d        vel,depth,vdamp,phase (f5.2,5x,f7.2,2x,f7.3,3x,a1)\n",$nlayer;
$vdamp = 1.0;

# vp velocity
for($i=0;$i<$nlayer;$i++){
    chomp($par[$i]);
    ($hp,$vp,$vs,$den,$qp,$qs) = split(" ",$par[$i]);
    if ($i == 0) {
        printf NV "%5.2f     %7.2f  %7.3f   P-VELOCITY MODEL\n",$vp,$hp,$vdamp;
    } else {
        printf NV "%5.2f     %7.2f  %7.3f\n",$vp,$hp,$vdamp;
    }
}

# indicate the number of layers for Vs
printf NV "%3d\n",$nlayer;
$vdamp = 1.0;

# vs velocity
for($i=0;$i<$nlayer;$i++){
    chomp($par[$i]);
    ($hs,$vp,$vs,$den,$qp,$qs) = split(" ",$par[$i]);
    if ($i == 0) {
        printf NV "%5.2f     %7.2f  %7.3f   S-VELOCITY MODEL\n",$vs,$hs,$vdamp;
    } else {
        printf NV "%5.2f     %7.2f  %7.3f\n",$vs,$hs,$vdamp;
    }
}
close(NV);

##################################################
# Phase file conversion for VELEST (updated format)
#################################################
$phaseout = "velest.pha"; # phase format for VELEST ISED=0
$phasecat = "initial.cat"; # catalog format for VELEST

open(JK,"<$phasein");
@par = <JK>;
close(JK);

$neqs = 0; # This will count events written to file
open(EV,">$phaseout");
open(CT,">$phasecat");

my $header_line = "";
my $cat_line = "";
my @phase_buffer = ();
my %processed_phases;

sub flush_event_buffer {
    if ($header_line ne "" && scalar(@phase_buffer) > 0) {
        print EV $header_line;
        print CT $cat_line;
        
        my $line = "";
        my $count = 0;
        foreach my $phase_item (@phase_buffer) {
            $line .= $phase_item;
            $count++;
            if ($count % 6 == 0) {
                print EV "$line\n";
                $line = "";
            }
        }
        if ($line ne "") {
            print EV "$line\n";
        }
        print EV "\n"; # Blank line to terminate event phase block
        $neqs++;
    }
    $header_line = "";
    $cat_line = "";
    @phase_buffer = ();
    %processed_phases = ();
}

foreach $file(@par){
    chomp($file);
    @fields = split(/\s+/, $file);
    if (!@fields) { next; } # Skip empty lines
    $test = $fields[0];

    if($test eq "#"){
        flush_event_buffer();

		my ($jk,$year,$month,$day,$hour,$min,$sec,$lon,$lat,$dep,$mag,$jk,$jk,$jk,$num) = @fields;
		my $year_short = substr($year,2,2); # VELEST format
		my $vsn = "N"; my $vew = "E";
		if($lat < 0.0){$vsn = "S"; $lat = -1*$lat;} # VELEST format
		if($lon < 0.0){$vew = "W"; $lon = -1*$lon;}
        $mag=0.0; ## adjustment here bc mags are wrong
		
        my $hourmin = sprintf("%02d%02d", $hour, $min);
        $header_line = sprintf("%s%02d%02d %s %5.2f %7.4f%s %8.4f%s %7.2f  %5.2f\n", $year_short, $month, $day, $hourmin, $sec, $lat, $vsn, $lon, $vew, $dep, $mag);
		$cat_line = sprintf("%s%02d%02d %02d%02d %5.2f %7.4f%s %8.4f%s %7.2f  %5.2f\n",$year_short,$month,$day,$hour,$min,$sec,$lat,$vsn,$lon,$vew,$dep,$mag);

	}else{
        my ($station,$tpick,$jk,$phase) = @fields;

        if (not defined $phase) {
            next;
        }
        $phase = uc($phase);

        # Filter phases based on user selection
        if ($phase_select eq 'p' and $phase ne 'P') { next; }
        if ($phase_select eq 's' and $phase ne 'S') { next; }
        if ($phase ne 'P' and $phase ne 'S') { next; }
        
        my $sta_short = substr($station, 0, 4);
        if (exists $processed_phases{"$sta_short.$phase"}) {
            next; # Skip duplicate phase
        }
        $processed_phases{"$sta_short.$phase"} = 1;
        
        my $iwt;
        if ($phase eq 'P') {
            $iwt = 0;
        } elsif ($phase eq 'S') {
            # In single-event mode, VELEST sets w=0.0 for ipwt > 4,
            # effectively excluding them from location.
            $iwt = 5;
        }
        
        $sta_short = sprintf("%-4s", $sta_short); # Pad to 4 chars
        
        my $phase_item = sprintf("%s%s%d%6.2f", $sta_short, $phase, $iwt, $tpick);
        push @phase_buffer, $phase_item;
    }
}
flush_event_buffer(); # Flush the last event

close(EV);
close(CT);

print STDERR "Total events written: $neqs\n";

################################################
# velest input file preparation
################################################
$velestinput = "velest.cmn";
open(JK,">$velestinput");
print JK "velest parameters are below\n";
#***  olat       olon   icoordsystem      zshift   itrial ztrial    ised
print JK "$reflat   $reflon      0            0.0      0     0.00       0\n"; # ised=0 for new format
#*** neqs   nshot   rotate
print JK "$neqs      0      0.0\n";
#*** isingle   iresolcalc
print JK "$isingle      0\n";
#*** dmax    itopo    zmin     veladj    zadj   lowveloclay
print JK "$distmax   0      $zmin    0.20    5.00    $lowvelocity\n";
#*** nsp    swtfac   vpvs       nmod
print JK "2      0.75      1.730        1\n";
#***   othet   xythet    zthet    vthet   stathet
print JK "0.01    0.01      0.01    $vthet     $stathet\n";
#*** nsinv   nshcor   nshfix     iuseelev    iusestacorr
print JK  "1       0       0        $iuseelev        $iusestacorr\n";
#*** iturbo    icnvout   istaout   ismpout
print JK  "1         1         2        0\n";
#*** irayout   idrvout   ialeout   idspout   irflout   irfrout   iresout
print JK  "0         0         0         0         0         0         0\n";
#*** delmin   ittmax   invertratio
print JK  "0.001   $ittmax   $invertratio\n";
#*** Modelfile:
print JK  "$newvel\n";
#*** Stationfile:
print JK  "$stause\n";
#*** Seismofile:
print JK  " \n";                                                                               
#*** File with region names:
print JK  "regionsnamen.dat\n";
#*** File with region coordinates:
print JK  "regionskoord.dat\n";
#*** File #1 with topo data:
print JK  " \n";                                                                                
#*** File #2 with topo data:
print JK  " \n";                                                                                
#*** File with Earthquake data (phase):
print JK  "$phaseout\n";
#*** File with Shot data:
print JK  " \n";                                                                               
#*** Main print output file:
print JK "main.OUT\n";
#*** File with single event locations:
print JK "out.CHECK\n";
#*** File with final hypocenters in *.cnv format:
print JK "final.CNV\n";
#*** File with new station corrections:
print JK "sta.COR\n";
close(JK);

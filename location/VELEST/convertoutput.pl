#!/usr/bin/perl
use Scalar::Util qw(looks_like_number);
#
# Author: Miao Zhang, miao.zhang@dal.ca
#
@ARGV == 4 || die "perl $0 stationgap residual finalcatalog deletedcatalog\n";
$gapmax = $ARGV[0];
$resmax = $ARGV[1];
$relo = $ARGV[2];
$dele = $ARGV[3];
chomp($dele);

$relocate = "final.CNV"; # output by VELEST
if (-e $relo){`rm $relo $dele`;}

# DEBUG: Check if input file exists and is readable
unless (-f $relocate and -r $relocate) {
    print STDERR "DEBUG convertoutput.pl: Error - Cannot find or read input file '$relocate'. It might not have been created by 'velest'.\n";
    # Create empty files to avoid errors downstream
    open(my $fh_relo, '>', $relo) or die "Cannot create $relo: $!";
    close $fh_relo;
    open(my $fh_dele, '>', $dele) or die "Cannot create $dele: $!";
    close $fh_dele;
    exit 0;
}

open(JK,"<$relocate");
@par = <JK>;
close(JK);

# DEBUG: Print number of lines read from final.CNV
print STDERR "DEBUG convertoutput.pl: Read " . scalar(@par) . " lines from $relocate\n";

$i=0;
open(OT,">$relo");
open(DE,">$dele");
foreach $_(@par){
	chomp($_);
	#if(looks_like_number(substr($_,0,2))){
	if(substr($_,25,1) eq 'N' || substr($_,25,1) eq 'S'){
        # DEBUG: Processing a line
        # print STDERR "DEBUG convertoutput.pl: Processing line: $_\n";
	$year = substr($_,0,2); $year=~s/^\s+//;
    $mon = substr($_,2,2); $mon=~s/^\s+//;
    $day = substr($_,4,2); $day=~s/^\s+//;
    if(length($year) == 1){$year = "0$year";}
    if(length($mon) == 1){$mon = "0$mon";}
    if(length($day) == 1){$day = "0$day";}

    $date = "$year$mon$day";
	$hour = substr($_,7,2);
	$min = substr($_,9,2);
	$sec = substr($_,12,5);
	$lat = substr($_,18,7);
	$lon = substr($_,27,8);
	$dep = substr($_,37,6);
	$mag = substr($_,44,10);
	$az = substr($_,54,3);
	$res = substr($_,62,5);
    if(substr($_,25,1) eq 'S'){$lat = -1*$lat;}
    if(substr($_,35,1) eq 'W'){$lon = -1*$lon;}
    #    if($dep < 0){$dep = 0.0;}
	if($az <= $gapmax && $res <= $resmax){
        $i++;
		print OT "$date $hour $min $sec $lat $lon $dep $mag $az $res $i\n";
	}else{
		print DE "$date $hour $min $sec $lat $lon $dep $mag $az $res $i\n";
	}
	}
}
close(OT);
close(DE);

# DEBUG: Print total number of events written
print STDERR "DEBUG convertoutput.pl: Wrote $i events to $relo\n";

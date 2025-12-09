### Usage: awk -f pha_t-dist_all.awk ../phase_allday.txt

BEGIN {
    FS  = "[ \t]+"
    OFS = " "

    DEBUG_EVERY = 5000
    start_time = systime()

    # mawk-compatible stderr prints
    print "[DEBUG] Starting run. Epoch:", start_time > "/dev/stderr"
    print "[DEBUG] Reading station.dat ..." > "/dev/stderr"

    # constants
    DEG2KM   = 111.19
    PI       = 3.141592653589793
    DEG2RAD  = PI / 180.0

    sta_count = 0

    # -------- Read station.dat ----------
    while ((getline line < "../../Data/station.dat") > 0) {
        n = split(line, f, FS)

        staID = f[4]
        lat   = f[2]
        lon   = f[1]
        dep   = 0

        if (!(staID in sta_lat)) {
            sta_lat[staID] = lat
            sta_lon[staID] = lon
            sta_dep[staID] = dep
            sta_count++
        } else {
            if (sta_lat[staID] != lat || sta_lon[staID] != lon) {
                print "[DEBUG] WARNING: conflicting coords for station", staID > "/dev/stderr"
            }
        }
    }
    close("../../Data/station.dat")

    print "[DEBUG] Loaded", sta_count, "unique stations" > "/dev/stderr"

    n_P = n_S = 0
}

# -------- Event header lines ----------
$4 != "P" && $4 != "S" {
    eveID    = $15
    lat1     = $8
    lon1     = $9
    dep1     = $10
    cos_lat1 = cos(lat1 * DEG2RAD)

    event_count++
    if (event_count % 100 == 0) {
        print "[DEBUG] Event", event_count, "at input line", NR > "/dev/stderr"
    }
    next
}

# -------- Phase pick lines --------
$4 == "P" || $4 == "S" {

    # periodic progress
    if (NR % DEBUG_EVERY == 0) {
        elapsed = systime() - start_time
        print "[DEBUG]", NR, "lines processed. Elapsed", elapsed, "sec" > "/dev/stderr"
        print "[DEBUG] Counts:", "P=", n_P, "S=", n_S > "/dev/stderr"
    }

    sta    = $1
    t_pick = $2

    if (!(sta in sta_lat)) {
        print "[DEBUG] WARNING: no coords for station", sta, "line", NR > "/dev/stderr"
        next
    }

    lat2 = sta_lat[sta]
    lon2 = sta_lon[sta]
    dep2 = sta_dep[sta]

    dlat = lat1 - lat2
    dlon = lon1 - lon2

    kmNS = dlat * DEG2KM
    kmEW = dlon * DEG2KM * cos_lat1
    dz   = dep1 - dep2
    dist = sqrt(kmNS*kmNS + kmEW*kmEW + dz*dz)

    if ($4 == "P") {
        phase_code = 1
        n_P++
    } else {
        phase_code = 2
        n_S++
    }

    print eveID, sta, t_pick, dist, phase_code >> "t_dist.dat"
}

END {
    elapsed = systime() - start_time

    print "[DEBUG] Finished." > "/dev/stderr"
    print "[DEBUG] Events:", event_count > "/dev/stderr"
    print "[DEBUG] Total P:", n_P, "Total S:", n_S > "/dev/stderr"
    print "[DEBUG] Elapsed seconds:", elapsed > "/dev/stderr"
}

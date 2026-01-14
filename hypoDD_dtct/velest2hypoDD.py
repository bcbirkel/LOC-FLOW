#!/usr/bin/python -w
import sys

def format_convert(phaseinput,phaseoutput,nrms,ngap,maxdep):
#phaseinput = 'final.CNV' # phase file output by hypoinverse
#phaseoutput = 'hypoDD.pha' # input phase file for hypoDD
    year0 = '20'
    #year0 = '19' 
    g = open(phaseoutput, 'w')
    nn = 0
    nrms = float(nrms)
    ngap = int(ngap)
    maxdep = float(maxdep)

    with open(phaseinput, "r") as f:
        for line in f:
            if (len(line) == 68):
                iok = 0
                RMS = float(line[61:67])
                gap = int(line[54:57])
                dep = float(line[36:43])
                if RMS <= nrms and gap <= ngap and dep <= maxdep:
                    line = line.strip('\n')
                    nn = nn + 1
                    if int(line[0:2]) < 10: 
                        year = year0 + '0' + str(int(line[0:2]))
                    else:
                        year = year0 + line[0:2]
                    mon = int(line[2:4])
                    day = int(line[4:6])
                    hour = int(line[7:9])
                    min = int(line[9:11])
                    sec = float(line[12:17])

                    if line[25] == 'N': #N
                        lat = float(line[18:25])
                    else:
                        lat = float(line[18:25]) * (-1)
                    if line[35] == 'E':
                        lon = float(line[27:35])
                    else:
                        lon = float(line[27:35]) * (-1)

                    dep = float(line[36:43])
                    mag = float(line[43:50])
                    EH = 0.00
                    EZ = 0.00
                    g.write(
                        '# {:4s} {:2d} {:2d} {:2d} {:2d} {:5.2f}  {:8.4f}  {:9.4f}  {:6.2f} {:5.2f} {:7.2f} {:7.2f} {:7.2f}      {:6d}\n'.format(
                            year, mon, day, hour, min, sec, lat, lon, dep, mag, EH, EZ, RMS, nn))
                    iok = 1
            else:
                if (iok == 1 and line[0] != '\n'):
                    line = line.rstrip('\n')
                    L = len(line)

                    def looks_like_pick_start(s, j):
                        # Need at least 6 chars: 4(sta) + pha + '0'
                        if j + 6 > len(s):
                            return False
                        sta4 = s[j:j+4]
                        pha  = s[j+4:j+5]
                        z0   = s[j+5:j+6]
                        # station field must not be blank; phase must be P/S; then '0'
                        return (sta4.strip() != "") and (pha in ('P', 'S')) and (z0 == '0')

                    i = 0
                    while i < L:
                        # Find the next pick start (in case the line isn't perfectly aligned)
                        while i < L and not looks_like_pick_start(line, i):
                            i += 1
                        if i >= L or i + 6 > L:
                            break

                        sta4 = line[i:i+4]
                        pha  = line[i+4:i+5]   # 'P' or 'S'
                        # line[i+5] should be '0' by looks_like_pick_start()

                        # Time begins after "P0"/"S0", with optional spaces
                        k = i + 6
                        while k < L and line[k] == ' ':
                            k += 1

                        # Time ends right before the next pick start
                        j = k
                        while j < L and not looks_like_pick_start(line, j):
                            j += 1

                        tstr = line[k:j].strip()   # can be "3.66" or "11.29" etc.

                        try:
                            t = float(tstr)
                        except ValueError:
                            # If parsing fails, skip ahead a bit to avoid infinite loops
                            i = max(i + 6, j)
                            continue

                        g.write('{:<5s}    {:8.3f}   1.000   {:1s}\n'.format(sta4.strip(), t, pha))

                        # Move to next pick
                        i = j

    f.close()
    g.close()

if __name__ == '__main__':
    if len(sys.argv) != 6:
        print('velest2hypoDD.py final.CNV hypoDD.pha rms_threhold gap_threshold maxdep')
        sys.exit()
    format_convert(sys.argv[1],sys.argv[2],sys.argv[3],sys.argv[4],sys.argv[5])

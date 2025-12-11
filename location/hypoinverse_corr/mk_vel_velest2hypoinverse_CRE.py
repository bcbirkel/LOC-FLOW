import os
import sys
import datetime
import linecache

#Here we didn't consider depth above the sea level to avoid negative depth
#velocity model is relative to the average of station elevation

def get_line_context(file_path, line_number):
    return linecache.getline(file_path, line_number).strip()

def model_format(modelin):
    output = 'vel_model_P.crh'  # velocity model
    gg = open(output, 'w')
    gg.write("MODEL Vp Output by isingle = 0 iterated in VELEST\n")
    kk = 0
    i=0
    with open(modelin, "r") as f:
        for line in f:
            line = line.strip('\n')
            dep = line.split()[0]
            if dep == 'mantle':
                kk = 1
            if kk == 0:
                dep = float(dep) + 2.0 # push all of v model down by 2km for avg station elev
                # dep = float(dep) + 5.0 - 2.0 # push all of v model down by 5km to use CRE command in hypoinverse
                if dep < 0.0:
                    dep = 0.0
                vp = float(line.split()[1])
                gg.write('{:4.2f}  {:5.2f}\n'.format(vp, dep))
                i=i+1
    line_more = get_line_context(modelin, i+2)
    # ## BB added if statement:
    # if len(line_more) != 0:
    #     dep = line_more.split()[0]
    #     dep_1 = float(dep) + 0.1 + 2.0 # HYPOINVERSE doesn't like the same depth
    #     if dep_1 < 0.0:
    #         dep_1 = 0.0
    #     vp_1 = float(line_more.split()[1])
    #     vs_1 = float(line_more.split()[2])
    #     gg.write('{:4.2f}  {:5.2f}\n'.format(vp_1, dep_1)) # include the upper mantle layer

    output = 'vel_model_S.crh'  # velocity model
    gg = open(output, 'w')
    gg.write("MODEL Vs Output by isingle = 0 iterated in VELEST\n")
    kk = 0
    with open(modelin, "r") as f:
        for line in f:
            line = line.strip('\n')
            dep = line.split()[0]
            if dep == 'mantle':
                kk = 1
            if kk == 0:
                dep = float(dep) + 2.0 # push all of v model down by AVG STATION ELEV (2KM) to use CRE command in hypoinverse
                if dep < 0.0:
                    dep = 0.0
                vs = float(line.split()[2])
                gg.write('{:4.2f}  {:5.2f}\n'.format(vs, dep))
    if len(line_more) != 0:
        gg.write('{:4.2f}  {:5.2f}\n'.format(vs_1, dep_1)) # include the upper mantle layer 
        
if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('mk_vel_velest2hypoinverse.py modelfile')
        sys.exit()
    model_format(sys.argv[1]) 

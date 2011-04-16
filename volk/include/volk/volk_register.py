#! /usr/bin/env python

import sys
import re
import string
from xml.dom import minidom
from volk_regexp import *
from make_cpuid_c import make_cpuid_c
from make_cpuid_h import make_cpuid_h
from make_set_simd import make_set_simd
from make_registry import make_registry
from make_config_fixed import make_config_fixed
from make_typedefs import make_typedefs
from make_environment_init_c import make_environment_init_c
from make_environment_init_h import make_environment_init_h
from make_makefile_am import make_makefile_am
from make_machines_h import make_machines_h
from make_machines_c import make_machines_c
from make_each_machine_c import make_each_machine_c
from make_c import make_c
from make_h import make_h
import copy

outfile_set_simd = open("../../config/lv_set_simd_flags.m4", "w");
outfile_reg = open("volk_registry.h", "w");
outfile_h = open("volk.h", "w");
outfile_c = open("../../lib/volk.cc", "w");
outfile_typedefs = open("volk_typedefs.h", "w");
outfile_init_h = open("../../lib/volk_init.h", "w");
outfile_cpu_h = open("volk_cpu.h", "w");
outfile_cpu_c = open("../../lib/volk_cpu.c", "w");
#outfile_config_in = open("../../volk_config.h.in", "w");
outfile_config_fixed = open("volk_config_fixed.h", "w");
#outfile_mktables = open("../../lib/volk_mktables.c", "w");
outfile_environment_c = open("../../lib/volk_environment_init.c", "w");
outfile_environment_h = open("volk_environment_init.h", "w");
outfile_makefile_am = open("../../lib/Makefile.am", "w");
outfile_machines_h = open("volk_machines.h", "w");
outfile_machines_c = open("../../lib/volk_machines.cc", "w");
infile = open("Makefile.am", "r");


mfile = infile.readlines();

datatypes = [];
functions = [];



for line in mfile:
    subline = re.search(".*_(a16|u)\.h.*", line);
    if subline:
        subsubline = re.search("(?<=volk_).*", subline.group(0));
        if subsubline:
            dtype = remove_after_underscore.sub("", subsubline.group(0));
            subdtype = re.search("[0-9]+[A-z]+", dtype);
            if subdtype:
                datatypes.append(subdtype.group(0));
                

datatypes = set(datatypes);

for line in mfile:
    for dt in datatypes:
        if dt in line:
            subline = re.search("(volk_" + dt +"_.*(a16|u).*\.h)", line);
            if subline:
                
                subsubline = re.search(".+(?=\.h)", subline.group(0));
                functions.append(subsubline.group(0));

archs = [];
afile = minidom.parse("archs.xml");
filearchs = afile.getElementsByTagName("arch");
for filearch in filearchs:
    archs.append(str(filearch.attributes["name"].value));
                 
for arch in archs:
    a_var = re.search("^\$", arch);
    if a_var:
        archs.remove(arch);
        
        

archflags_dict = {}
for filearch in filearchs:
    archflags_dict[str(filearch.attributes["name"].value)] = str(filearch.getElementsByTagName("flag")[0].firstChild.data)

archs_or = "("
for arch in archs:
    archs_or = archs_or + string.upper(arch) + "|";
archs_or = archs_or[0:len(archs_or)-1];
archs_or = archs_or + ")";

#get machine list and parse to a list of machines, each with a list of archs (none of this DOM crap)
machine_str_dict = {}
mfile = minidom.parse("machines.xml");
filemachines = mfile.getElementsByTagName("machine")

for filemachine in filemachines:
    machine_str_dict[str(filemachine.attributes["name"].value)] = str(filemachine.getElementsByTagName("archs")[0].firstChild.data).split()

#all right now you have a dict of arch lists
#next we expand it
#this is an expanded list accounting for the OR syntax
#TODO: make this work for multiple "|" machines
machines = {}
already_done = False
for machine_name in machine_str_dict:
    already_done = False
    marchlist = machine_str_dict[machine_name]
    for march in marchlist:
        or_marchs = march.split("|")
        if len(or_marchs) > 1:
            marchlist.remove(march)
            for or_march in or_marchs:
                tempmarchlist = copy.deepcopy(marchlist)
                tempmarchlist.append(or_march)
                machines[machine_name + "_" + or_march] = tempmarchlist
                already_done = True

    if not already_done:
        machines[machine_name] = marchlist
 
#for machine_name in machines:
#    print machine_name + ": " + str(machines[machine_name])

#ok, now we have all the machines we're going to build. next step is to generate a Makefile.am where they're all laid out and compiled

taglist = [];
fcountlist = [];
arched_arglist = [];
retlist = [];
my_arglist = [];
my_argtypelist = [];
for func in functions:
    tags = [];
    fcount = [];
    infile_source = open(func + ".h");
    begun_name = 0;
    begun_paren = 0;
    sourcefile = infile_source.readlines();
    infile_source.close();
    for line in sourcefile:
#FIXME: make it work for multiple #if define()s
        archline = re.search("^\#if.*?LV_HAVE_" + archs_or + ".*", line);
        if archline:
            arch = archline.group(0);
            archline = re.findall(archs_or + "(?=( |\n|&))", line);
            if archline:
                archsublist = [];
                for tup in archline:
                    archsublist.append(tup[0]);
                fcount.append(archsublist);
        testline = re.search("static inline.*?" + func, line);
        if (not testline):
            continue
        tagline = re.search(func + "_.+", line);
        if tagline:
            tag = re.search("(?<=" + func + "_)\w+(?= *\()",line);
            if tag:
                tag = re.search("\w+", tag.group(0));
                if tag:
                    tags.append(tag.group(0));
               
    
        if begun_name == 0:
            retline = re.search(".+(?=" + func + ")", line);
            if retline:
                ret = retline.group(0);
                
                
                
        
            subline = re.search(func + ".*", line);
            if subline:
                subsubline = re.search("\(.*?\)", subline.group(0));
                if subsubline:
                    args = subsubline.group(0);
                    
                else:
                    begun_name = 1;
                    subsubline = re.search("\(.*", subline.group(0));
                    if subsubline:
                        args = subsubline.group(0);
                        begun_paren = 1;
        else:
            if begun_paren == 1:
                subline = re.search(".*?\)", line);
                if subline:
                    args = args + subline.group(0);
                    begun_name = 0;
                    begun_paren = 0;
                else:
                    subline = re.search(".*", line);
                    args = args + subline.group(0);
            else:
                subline = re.search("\(.*?\)", line);
                if subline:
                    args = subline.group(0);
                    begun_name = 0;
                else: 
                    subline = re.search("\(.*", line);
                    if subline:
                        args = subline.group(0);
                        begun_paren = 1;
    
    replace = re.compile("static ");
    ret = replace.sub("", ret);
    replace = re.compile("inline ");
    ret = replace.sub("", ret);
    replace = re.compile("\)");
    arched_args = replace.sub(", const char* arch) {", args);
    
    remove = re.compile('\)|\(|{');
    rargs = remove.sub("", args);
    sargs = rargs.split(',');
    
    
    
    margs = [];
    atypes = [];
    for arg in sargs:
        temp = arg.split(" ");
        margs.append(temp[-1]);
        replace = re.compile(" " + temp[-1]);
        atypes.append(replace.sub("", arg));

    
    my_args = ""
    arg_types = ""
    for arg in range(0, len(margs) - 1):
        this_arg = leading_space_remove.sub("", margs[arg]);
        my_args = my_args + this_arg + ", ";
        this_type = leading_space_remove.sub("", atypes[arg]);
        arg_types = arg_types + this_type + ", ";

    this_arg = leading_space_remove.sub("", margs[-1]);
    my_args = my_args + this_arg;
    this_type = leading_space_remove.sub("", atypes[-1]);
    arg_types = arg_types + this_type;
    my_argtypelist.append(arg_types);
    
    if(ret[-1] != ' '):
        ret = ret + ' ';

    arched_arglist.append(arched_args); #!!!!!!!!!!!
    my_arglist.append(my_args) #!!!!!!!!!!!!!!!!!
    retlist.append(ret);
    fcountlist.append(fcount);
    taglist.append(tags);               


outfile_cpu_h.write(make_cpuid_h(filearchs));
outfile_cpu_h.close();

outfile_cpu_c.write(make_cpuid_c(filearchs));
outfile_cpu_c.close();

outfile_set_simd.write(make_set_simd(filearchs, machines));
outfile_set_simd.close();
    
outfile_reg.write(make_registry(filearchs, functions, fcountlist, taglist));
outfile_reg.close();

outfile_config_fixed.write(make_config_fixed(filearchs));
outfile_config_fixed.close();

outfile_typedefs.write(make_typedefs(functions, retlist, my_argtypelist));
outfile_typedefs.close();

outfile_makefile_am.write(make_makefile_am(filearchs, machines, archflags_dict))
outfile_makefile_am.close()

outfile_machines_h.write(make_machines_h(functions, machines))
outfile_machines_h.close()

outfile_machines_c.write(make_machines_c(machines))
outfile_machines_c.close()

outfile_c.write(make_c(machines, archs, functions, arched_arglist, my_arglist))
outfile_c.close()

outfile_h.write(make_h(functions))
outfile_h.close()

for machine in machines:
    machine_c_filename = "../../lib/volk_machine_" + machine + ".cc"
    outfile_machine_c = open(machine_c_filename, "w")
    outfile_machine_c.write(make_each_machine_c(machine, machines[machine], functions, fcountlist, taglist))
    outfile_machine_c.close()

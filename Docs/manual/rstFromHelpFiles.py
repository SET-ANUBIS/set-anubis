#!/usr/bin/env python3

from __future__ import print_function
import sys, os
# sys.path.append(f"{os.getcwd()}/../../")
import warnings
warnings.filterwarnings("ignore")
import subprocess

def isEmpty ( string ):
    return string.strip() == ""

def write(c, f):
    lines = c.split("\n")
    isIn = ""
    lastIn = isIn

    for line in lines:
        new = line.replace("optional arguments", "*arguments*")
        new = new.replace("usage: ", "   ")

        if line[:3] == "  -":
            isIn = "newargument"
            while "[" in new:
                p1 = new.find("[")
                p2 = new.find("]")
                new = new[:p1] + new[p2 + 1:]
            new = new.rstrip()
            new = new.replace(" ,", ",")

        if isIn == "afterusage" and not isEmpty(line):
            isIn = "afterdescription"
            continue
        if isIn == "usage" and isEmpty(line):
            isIn = "afterusage"
        if line[:5] == "usage":
            isIn = "usage"

        if not isIn in ["usage", "argument"]:
            new += "\n"
        if isIn == "newargument" and lastIn == "argument":
            new = "\n" + new

        if isIn == "newargument":
            new += "\n"

        f.write(new + "\n")
        lastIn = isIn

        if line[:3] == "  -":
            isIn = "argument"

def run ( tool ):
    with open("source/%s.rst" % tool, "w" ) as f:
        c = subprocess.getoutput ( f"python ../../Pipeline/{tool}.py -h")
        write ( c, f )

def runSModelS ():
    with open("source/RunSModelS.rst", "w" ) as f:
        c = "waouw c'est génial ici"
        # c = subprocess.getoutput ( "../../runSModelS.py -h" )
        write ( c, f )


# run ("BR_calculator")
# run ( "lhechecker", "LheChecker" )
# run ( "slhachecker", "SlhaChecker" )
# run ( "database-browser", "DatabaseBrowser" )
# run ( "interactive-plots", "InteractivePlots" )
# run ( "toolbox", "ToolBox" )
# run ( "fixpermissions", "FixPermissions" )
# run ( "xsecresummino", "XSecResummino" )
# runSModelS()
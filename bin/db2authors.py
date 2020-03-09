#!/usr/bin/env python3

"""
Load the author list and database from the support directory and
convert it to an author tex file using AASTeX6.1 syntax.

  python3 db2authors.py > authors.tex

The list of authors for the paper should be defined in a authors.yaml
file in the current working directory.  This YAML file contains a
sequence of author IDs matching the keys in the author database
file in the etc/authordb.yaml file in this package.

This program requires the "yaml" package to be installed.

"""
from __future__ import print_function
import os
import sys
import os.path
import re
import yaml
import argparse

# Set to True to write a comma separated list of authors
WRITE_CSV = False

# There is a file listing all the authors and a file mapping
# those authors to full names and affiliations

# This is the author list. It's a yaml file with authorID that
# maps to the database file below.  For now we assume this file is in
# the current working directory.
authorfile = os.path.join("authors.yaml")

# this should probably be a dict with the value of affil_cmd
# the keys could then be passed to the arg parser.
OUTPUT_MODES = ["aas", "spie"]

description = __doc__
formatter = argparse.RawDescriptionHelpFormatter
parser = argparse.ArgumentParser(description=description,
                                 formatter_class=formatter)

parser.add_argument("-m", "--mode", default="aas", choices=OUTPUT_MODES,
                    help="""Display mode for translated parameters.
                         'verbose' displays all the information...""")
args = parser.parse_args()

affil_cmd = "affiliation"
if args.mode == "spie":
    affil_cmd = "authorinfo"


with open(authorfile, "r") as fh:
    authors = yaml.safe_load(fh)

# This is the database file with all the generic information
# about authors. Locate it relative to this script.
exedir = os.path.abspath(os.path.dirname(__file__))
dbfile = os.path.normpath(os.path.join(exedir, os.path.pardir, "etc", "authordb.yaml"))

with open(dbfile, "r") as fh:
    authordb = yaml.safe_load(fh)

# author db is dict indexed by author id.
# Each entry is a dict with keys
# name: Surname
# initials: A.B.
# orcid: ORCID (can be None)
# affil: List of affiliation labels
# altaffil: List of alternate affiliation text
authorinfo = authordb["authors"]

# dict of all the affiliations, key is a label
# used in author list
affil = authordb["affiliations"]

# AASTeX6.1 author files are of the form:
# \author[ORCID]{Initials~Surname}
# \altaffiliation{Hubble Fellow}   * must come straight after author
# \affiliation{Affil1}
# \affiliation{Affill2}
# Do not yet handle \email or \correspondingauthor

if WRITE_CSV:
    # Used for arXiv submission
    names = ["{auth[initials]} {auth[name]}".format(auth=a) for a in authors]
    print(", ".join(names))
    sys.exit(0)

print("""%% DO NOT EDIT THIS FILE. IT IS GENERATED FROM db2authors.py"
%% Regenerate using:
%%    python $LSST_TEXMF_DIR/bin/db2authors.py > authors.tex
""")
print()

for authorid in authors:
    orcid = ""

    try:
        auth = authorinfo[authorid]
    except KeyError as e:
        raise RuntimeError(f"Author ID {authorid} now defined in author database.") from e

    if "orcid" in auth and auth["orcid"]:
        orcid = "[{}]".format(auth["orcid"])

    # For spaces in surnames use a ~
    surname = re.sub(r"\s+", "~", auth["name"])

    # Preference for A.~B.~Surname rather than A.B.~Surname
    initials = re.sub(r"\.(\w)", lambda m: ".~" + m.group(1), auth["initials"])

    # For spaces in initials use a ~
    initials = re.sub(r"\s+", "~", initials)

    print(r"\author{}{{{}~{}}}".format(orcid, initials, surname))
    if "altaffil" in auth:
        for af in auth["altaffil"]:
            print(r"\altaffiliation{{{}}}".format(af))

    # The affiliations have to be retrieved via label
    for aflab in auth["affil"]:
        print(r"\{}{{{}}}".format(affil_cmd, affil[aflab]))

    print()

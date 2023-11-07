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
OUTPUT_MODES = ["aas", "spie", "adass", "arxiv"]

description = __doc__
formatter = argparse.RawDescriptionHelpFormatter
parser = argparse.ArgumentParser(description=description,
                                 formatter_class=formatter)

parser.add_argument("-m", "--mode", default="aas", choices=OUTPUT_MODES,
                    help="""Display mode for translated parameters.
                         'verbose' displays all the information...""")
parser.add_argument("-n", "--noafil", action='store_true',
                    help="""Do not add affil at all for arxiv.""")
args = parser.parse_args()

buffer_affil = False  # hold affiliation until after author output
buffer_authors = False  # out put authors in one \author command (adass)
affil_cmd = "affiliation"  # command for latex affiliation
affil_form = r"\{}[{}]{{{}}}"  # format of the affiliation
auth_afil_form = "{}{}{}"  # format of author with affiliation
author_form = r"\author{}{{~{}~{}}}"  # fomrmat of the author
author_super = False  # Author affiliation as super script

# The default is AAS and if no mode is specified you get that
if args.mode == "arxiv":
    author_form = r"{} {}{}"
    affil_cmd = ""
    affil_out_sep = ", "
    affil_form = r"{}({}) {}"
    auth_afil_form = "{}{}({})"
    buffer_affil = True
    buffer_authors = True

if args.mode == "spie":
    affil_cmd = "affil"
    buffer_affil = True

if args.mode == "adass":
    affil_cmd = "affil"
    affil_out_sep = "\n"
    affil_form = r"\{}{{$^{}${}}}"
    auth_afil_form = "{}{}$^{}$"
    author_form = r"{}~{}{}"  # initial, surname, affil
    buffer_affil = True
    buffer_authors = True
    author_super = True

with open(authorfile, "r") as fh:
    authors = yaml.safe_load(fh)

# This is the database file with all the generic information
# about authors. Locate it relative to this script.
exedir = os.path.abspath(os.path.dirname(__file__))
dbfile = os.path.normpath(
    os.path.join(exedir, os.path.pardir, "etc", "authordb.yaml"))

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
affilset = list()  # it will be a set but I want index() which is supported in list

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
%% Regenerate using:""")
print(f"%%    python $LSST_TEXMF_DIR/bin/db2authors.py {args} ")
print()

authOutput = list()
allAffil = list()
pAuthorOutput = list()
indexOutput = list()

anum = 0


def get_initials(initials):
    """Authors db has full name not initials -
       sometimes we just want intials"""
    names = re.split(r'[ -\.\~]', initials)
    realInitials = []
    for name in names:
        if len(name) > 0:
            realInitials.append(name[0])
    return "~"+".~".join(realInitials)+"."


for anum, authorid in enumerate(authors):
    orcid = ""

    try:
        auth = authorinfo[authorid]
    except KeyError as e:
        raise RuntimeError(
            f"Author ID {authorid} not defined in author database.") from e

    affilOutput = list()
    affilAuth = ""
    affilSep = ""
    if author_super and anum < len(authors) - 1:
        # ADASS  comma before the affil except the last entry
        affilSep = ","
    for theAffil in auth["affil"]:
        if theAffil not in affilset:
            affilset.append(theAffil)
            # unforuneately you can not output an affil before an author
            affilOutput.append(
                affil_form.format(affil_cmd, len(affilset), affil[theAffil]))

        affilInd = affilset.index(theAffil) + 1
        if args.noafil:
            affilAuth = affilAuth
        else:
            affilAuth = auth_afil_form.format(affilAuth, affilSep, str(affilInd))

        affilSep = " "

    if buffer_affil:
        orcid = "[{}]".format(affilAuth)
    else:
        if "orcid" in auth and auth["orcid"]:
            orcid = "[{}]".format(auth["orcid"])

    orc = auth.get("orcid", "")
    if orc is None:
        orc = ""
    email = auth.get("email", "")
    if email is None:
        email = ""
    # For spaces in surnames use a ~
    surname = re.sub(r"\s+", "~", auth["name"])

    # Preference for A.~B.~Surname rather than A.B.~Surname
    initials = re.sub(r"\.(\w)", lambda m: ".~" + m.group(1), auth["initials"])

    # For spaces in initials use a ~
    initials = re.sub(r"\s+", "~", initials)

    # adass has index and paper authors ..
    addr = [a.strip() for a in affil[theAffil].split(',')]
    tute = addr[0]
    ind = len(addr) - 1
    if ind > 0:
        country = addr[ind]
        ind = ind - 1
    if ind > 0:
        sc = addr[ind].split()
        ind = ind - 1
        state = sc[0]
        pcode = ""
        if (len(sc) == 2):
            pcode = sc[1]
    city = ""
    if ind > 0:
        city = addr[ind]

    pAuthorOutput.append(
        r"\paperauthor{{{}~{}}}{{{}}}{{{}}}{{{}}}{{}}{{{}}}{{{}}}{{{}}}{{{}}}".
        format(initials, surname, email, orc, tute, city, state, pcode,
               country))

    if args.mode == "arxiv":
        affilOutput = list()  # reset this
        affilOutput.append(affil_form.format(affil_cmd, len(affilset), tute))

    justInitials = get_initials(initials)
    indexOutput.append(r"%\aindex{{{},{}}}".format(surname, justInitials))

    if buffer_authors:
        authOutput.append(author_form.format(initials, surname, affilAuth))
        allAffil = allAffil + affilOutput
    else:
        print(author_form.format(orcid, initials, surname))
        if buffer_affil:
            print(*affilOutput, sep="\n")
        else:
            if auth.get("altaffil"):
                for af in auth["altaffil"]:
                    print(r"\altaffiliation{{{}}}".format(af))

            # The affiliations have to be retrieved via label
            for aflab in auth["affil"]:
                print(r"\{}{{{}}}".format(affil_cmd, affil[aflab]))
        print()

if buffer_authors:
    if args.mode == "arxiv":
        print(r"Authors:", end='')
    else:
        print(r"\author{", end='')
    anum = 0
    numAuths = len(authOutput) - 1
    for auth in authOutput:
        print(auth, end='')
        anum = anum + 1
        if (anum == numAuths and numAuths > 1) or \
                (args.mode == "arxiv" and anum < numAuths):
            print(" and ", end='')
        else:
            if anum < numAuths:
                print(" ", end='')
    if args.mode == "arxiv":
        print("\n(", end="")
    else:
        print("}")
    if not args.noafil:
        print(*allAffil, sep=affil_out_sep, end="")
    if args.mode == "arxiv":
        print(")\n")
    if args.mode != "arxiv":
        print("")
        print(*pAuthorOutput, sep="\n")
        print("% Yes they said to have these index commands commented out.")
        print(*indexOutput, sep="\n")

#!/usr/bin/env python

import os, sys
import argparse
import difflib
import json
import logging
import operator

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(BASE_DIR)
from lib import pulp_lib

logger = logging.getLogger()

list_headers = [
    "name",
    "version",
    "release",
    "arch",
]

def list_content(args, parser):
    global list_headers

    if not args.repoid:
        logger.error("Must provide repoid argument")
        sys.exit(1)

    criteria = {}
    criteria["fields"] = {
        "unit": list_headers
    }
    criteria["type_ids"] = ["rpm"]
    if args.match:
        criteria["filters"] = {
            "unit": {"name": {"$regex": args.match}}
        }
    data = pulp_lib.post_request("repositories/%s/search/units/" % args.repoid, data={"criteria": criteria})
    #print json.dumps(data[0], sort_keys=True, indent=4)
    #return None
    units = []
    for unit in data:
        if not unit["metadata"]:
            continue
        row = []
        for header in list_headers:
            row.append(unit["metadata"][header])
        units.append(row)
        #print json.dumps(row, sort_keys=True, indent=4)
    rows = []
    for unit in sorted(units, key=operator.itemgetter(0,1,2)):
        rows.append(unit)
    pulp_lib.print_table(list_headers, rows)


def diff_content(args, parser):
    global list_headers

    fields = list_headers + ["arch"]
    criteria = {}
    criteria["fields"] = {
        "unit": fields
    }
    criteria["type_ids"] = ["rpm"]
    #criteria["filters"] = {"unit": {"name": {"$regex": "zlib-devel"}}}
    if args.match:
        criteria["filters"] = {
            "unit": {"name": {"$regex": args.match}}
        }

    from_data = pulp_lib.post_request("repositories/%s/search/units/" % args.from_repoid, data={"criteria": criteria})
    to_data = pulp_lib.post_request("repositories/%s/search/units/" % args.to_repoid, data={"criteria": criteria})
    #print json.dumps(from_data, sort_keys=True, indent=4)

    from_rpms = []
    to_rpms = []
    for unit in from_data:
        m = unit["metadata"]
        name = "%s-%s-%s.%s" % (m["name"], m["version"], m["release"], m["arch"])
        if name not in from_rpms:
            from_rpms.append(name)
    for unit in to_data:
        m = unit["metadata"]
        name = "%s-%s-%s.%s" % (m["name"], m["version"], m["release"], m["arch"])
        if name not in to_rpms:
            to_rpms.append(name)

    #print json.dumps(to_rpms, sort_keys=True, indent=4)
    if args.show_diff:
        for line in difflib.unified_diff(from_rpms, to_rpms, fromfile=args.from_repoid, tofile=args.to_repoid):
            print(line)
    else:
        differences = list(set(from_rpms) - set(to_rpms))
        for d in sorted(differences):
            print(d)

def content_changelog(args, parser):
    criteria = {}
    criteria["type_ids"] = ["rpm"]
    if args.match:
        criteria["filters"] = {
            "unit": {"name": {"$regex": "^%s$" % args.match}}
        }
    data = pulp_lib.post_request("repositories/%s/search/units/" % args.repoid, data={"criteria": criteria})
    #print json.dumps(data, sort_keys=True, indent=4)
    units = []
    unit_names = []
    for unit in data:
        u = {}
        m = unit["metadata"]
        u_name = "%s-%s-%s" % (m["name"], m["version"], m["release"])
        if u_name in unit_names:
            continue
        else:
            unit_names.append(u_name)
        rows = []
        for c in sorted(m["changelog"], key=operator.itemgetter(0)):
            row = []
            row.append(c[1])
            row.append(c[2])
            row.append("")
            rows.append(["\n".join(row)])
        pulp_lib.print_table(["%s Changelog" % u_name], rows)


parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers()
parser_list = subparsers.add_parser('list', help="list command")
parser_diff = subparsers.add_parser('diff', help="diff command")
parser_changelog = subparsers.add_parser('changelog', help="changelog command")

parser_list.add_argument("repoid",
                         action="store",
                         nargs="?")
parser_list.add_argument("-m", "--match",
                         help="filter for contents",
                         dest="match",
                         action="store")
parser_list.set_defaults(func=list_content)

parser_diff.add_argument("--from-repo-id",
                         help="from repo ID",
                         dest="from_repoid",
                         action="store",
                         required=True)
parser_diff.add_argument("--to-repo-id",
                         help="to repo ID",
                         dest="to_repoid",
                         action="store",
                         required=True)
parser_diff.add_argument("-m", "--match",
                         help="filter for contents",
                         dest="match",
                         action="store")
parser_diff.add_argument("--show-diff",
                         help="show diff",
                         dest="show_diff",
                         action="store_true")
parser_diff.set_defaults(func=diff_content)

parser_changelog.add_argument("repoid",
                         action="store",
                         nargs="?")
parser_changelog.add_argument("-m", "--match",
                              help="filter for contents",
                              dest="match",
                              action="store",
                              required=True)
parser_changelog.set_defaults(func=content_changelog)


args = parser.parse_args()
args.func(args, parser)

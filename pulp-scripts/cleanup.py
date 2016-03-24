#!/usr/bin/env python

import argparse
import difflib
import json
import logging
import operator
import os, sys

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(BASE_DIR)
from lib import pulp_lib

logger = logging.getLogger()


def remove_old(args, parser):
    global list_headers

    #fields = ["unit_type_id", "unit_id"]#list_headers + ["arch"]
    criteria = {}
    #criteria["fields"] = {
    #   "unit": fields
    #}
    criteria["type_ids"] = ["package_group"]
    #criteria["filters"] = {"unit": {"name": {"$regex": "zlib-devel"}}}
    #if args.match:
    #    criteria["filters"] = {
    #        "unit": {"name": {"$regex": args.match}}
    #    }

    from_data = pulp_lib.post_request("repositories/%s/search/units/" % args.from_repoid, data={"criteria": criteria}, limit=100)
    to_data = pulp_lib.post_request("repositories/%s/search/units/" % args.to_repoid, data={"criteria": criteria}, limit=100)
    print json.dumps(from_data[0], sort_keys=True, indent=4)
    print json.dumps(to_data[0], sort_keys=True, indent=4)
    return None
    from_units = []
    to_units = []
    remove_units = []
    from_unit_ids = [ d["unit_id"] for d in from_data ]
    for unit in to_data:
        _unit_id = unit["unit_id"]
        _unit_type = unit["unit_type_id"]
        if _unit_id not in from_unit_ids:
            _unit = {
                "id": _unit_id,
                "type": _unit_type
            }
            remove_units.append(_unit)
    remove_types = {}
    for unit in remove_units:
        _id = unit["id"]
        _type = unit["type"]
        if _type in remove_types:
            remove_types[_type]["ids"].append(_id)
        else:
            remove_types[_type] = {}
            remove_types[_type]["ids"] = [_id]
            remove_types[_type]["type"] = _type
    #print json.dumps(remove_types, indent=4, sort_keys=True)
    #return None
    for remove_type in remove_types.values():
        criteria = {
            'type_ids': [remove_type['type']],
            'filters': {
                'association': { 'unit_id': {'$in': remove_type['ids']} },
            }
        }
        pulp_lib.post_request("repositories/%s/actions/unassociate/" % args.to_repoid, data={"criteria": criteria})
    return None


parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers()
parser_remove_old = subparsers.add_parser('removeold', help="removeold command")

parser_remove_old.add_argument("--from-repo-id",
                         help="from repo ID",
                         dest="from_repoid",
                         action="store",
                         required=True)
parser_remove_old.add_argument("--to-repo-id",
                         help="to repo ID",
                         dest="to_repoid",
                         action="store",
                         required=True)
parser_remove_old.set_defaults(func=remove_old)


args = parser.parse_args()
args.func(args, parser)

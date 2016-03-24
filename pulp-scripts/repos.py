#!/usr/bin/env python

import os, sys
import argparse
import json

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(BASE_DIR)
from lib import pulp_lib

list_headers = {
    "details": [
        "name",
        "http",
        "https",
        "remove_missing",
        "rpms",
        "package_group",
        "package_category",
        "distribution",
    ],
    "no_details": [
        "name",
        "last_published",
        "last_sync",
        "relative_url",
        "feed"
    ]
}

def list(args, parser):
    global list_headers

    if args.details:
        headers = list_headers["details"]
    else:
        headers = list_headers["no_details"]
    #data = pulp_lib.get_request("repositories/", params={"details": 1})
    criteria = {}
    if args.repo:
        criteria['filters'] = {
            'id': {'$in': args.repo},
        }
    data = pulp_lib.post_request("repositories/search/", data={"criteria": criteria, "importers": 1, "distributors": 1})
    #print json.dumps(data, indent=4, sort_keys=True)
    #return None
    repo_names = []
    repos = {}
    for repo in data:
        name = repo["display_name"]
        #if args.repo and name not in args.repo:
        #    continue
        #if name == 'centos-6-base':
        #    print json.dumps(repo, indent=4, sort_keys=True)
        # Collect distributors
        for distributor in repo["distributors"]:
            if distributor["distributor_type_id"] == "yum_distributor":
                distributors = distributor
        # Collect importers
        for importer in repo["importers"]:
            if importer["importer_type_id"] == "yum_importer":
                importers = importer
        repo_names.append(name)
        repo_data = {
            "name": name,
            "last_published": distributors.get("last_publish", ""),
            "relative_url": distributors["config"].get("relative_url", ""),
            "last_sync": importers.get("last_sync", ""),
            "feed": importers["config"].get("feed", ""),
            "http": distributors["config"].get("http", ""),
            "https": distributors["config"].get("https", ""),
            "remove_missing": importers["config"].get("remove_missing", ""),
            "rpms": repo["content_unit_counts"].get("rpm", ""),
            "package_group": repo["content_unit_counts"].get("package_group", ""),
            "package_category": repo["content_unit_counts"].get("package_category", ""),
            "distribution": repo["content_unit_counts"].get("distribution", ""),
        }
        row = []
        for header in headers:
            row.append(repo_data[header])
        repos[name] = row
    rows = []
    for repo_name in sorted(repo_names):
        row = repos[repo_name]
        rows.append(row)
    pulp_lib.print_table(headers, rows)

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers()
parser_list = subparsers.add_parser('list', help="list command")

parser_list.add_argument('--repo',
                         help="repo(s) to display.  Multiple are space separated",
                         dest="repo",
                         action="store",
                         nargs='*',
                         default=[])
parser_list.add_argument('--details',
                         help="show repo details",
                         dest="details",
                         action="store_true",
                         default=False)
parser_list.set_defaults(func=list)


args = parser.parse_args()
args.func(args, parser)

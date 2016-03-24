#!/usr/bin/env python

import os, sys
import argparse
import json
import re

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(BASE_DIR)
from lib import pulp_lib

def list(args, parser):
    """
        {
            "_href": "/pulp/api/v2/tasks/5cfedd93-e300-4edd-9b18-a94454a0190f/",
            "_id": {
                "$oid": "54e4f3d91378605a940f0b77"
            },
            "error": null,
            "exception": null,
            "finish_time": null,
            "id": "54e4f3d9e97f1818df85ead9",
            "progress_report": {},
            "queue": "reserved_resource_worker-0@repo01.brazos.tamu.edu.dq",
            "result": null,
            "spawned_tasks": [],
            "start_time": null,
            "state": "waiting",
            "tags": [
                "pulp:repository:epel-7-testing",
                "pulp:action:publish"
            ],
            "task_id": "5cfedd93-e300-4edd-9b18-a94454a0190f",
            "task_type": "pulp.server.managers.repo.publish.publish",
            "traceback": null
        },
    """
    #print vars(args)
    criteria = {}
    if args.list_state:
        criteria["filters"] = {
            "state": {"$in": args.list_state},
        }
    criteria["sort"] = [["start_time", "ascending"]]
    params = {
        "criteria": criteria
    }
    #data = pulp_lib.get_request("tasks/")
    data = pulp_lib.post_request("tasks/search/", data=params)
    #print json.dumps(data, sort_keys=True, indent=4)
    tasks = []
    for r in data:
        task = []
        resource = ""
        action = ""
        tags = r.get("tags", None)
        if not tags:
            continue
        for tag in tags:
            act_m = re.search('^pulp:action:(.*)$', tag)
            if act_m:
                action = act_m.group(1)
                continue
            res_m = re.search('^pulp:(.*):(.*)$', tag)
            if res_m:
                resource = "%s (%s)" % (res_m.group(2), res_m.group(1))
        state = r["state"]
        start_time = r["start_time"]
        finish_time = r["finish_time"]
        task_id = r["task_id"]
        task.append(resource)
        task.append(action)
        task.append(state)
        task.append(start_time)
        task.append(finish_time)
        task.append(task_id)
        tasks.append(task)
    headers = ["Resource", "Action", "State", "Start", "Finish", "Task ID"]
    pulp_lib.print_table(headers, tasks)

parser = argparse.ArgumentParser()
subparsers = parser.add_subparsers(dest='mode')
parser_list = subparsers.add_parser('list')

parser_list.add_argument('--list-state',
                         help="state of tasks to list",
                         dest="list_state",
                         action="store",
                         nargs='*',
                         default=[],
                         choices=["waiting", "skipped", "running", "suspended", "finished", "error", "canceled", "timed out"])
parser_list.set_defaults(func=list)


args = parser.parse_args()
args.func(args, parser)


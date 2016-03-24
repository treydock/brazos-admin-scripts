#!/usr/bin/env python

import os
import sys
import base64
import ConfigParser
import requests
import json
import logging
import re
from urlparse import urljoin
import prettytable

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
sys.path.append(BASE_DIR)
from lib.config import load_config
from lib.logs import setup_logging

configs = load_config()
config = configs['production']['pulp']

hostname = config.get("hostname", "localhost")
username = config.get("username", "admin")
password = config.get("password", "password")

logger = logging.getLogger()
setup_logging()

auth_str = "%s:%s" % (username, password)
auth_encoded = base64.b64encode(auth_str)
auth = "Basic %s" % auth_encoded

rest_headers = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
    'Authorization': auth,
}
base_url = "https://%s/pulp/api/v2/" % hostname

def get_request(url_path, params={}):
    global base_url
    global rest_headers

    json_data = {}
    url = urljoin(base_url, url_path)
    print url
    get_r = requests.get(url, params=params, headers=rest_headers, verify=True)

    if get_r.status_code == requests.codes.ok:
        json_data = get_r.json()
    else:
        print "GET %s failed with error code %s" % (url, get_r.status_code)
    return json_data

def post_request(url_path, data={}, limit=None, skip=0):
    global base_url
    global rest_headers

    if "criteria" not in data:
        data["criteria"] = {}
    json_data = []
    url = urljoin(base_url, url_path)
    if limit is None:
        _limit = 1000
        _recursive = True
    else:
        _limit = limit
        _recursive = False
    _skip = skip
    while True:
        data["criteria"]["limit"] = _limit
        data["criteria"]["skip"] = _skip
        logger.info("POST request to %s with parameters %s" % (url, json.dumps(data)))
        post_r = requests.post(url, data=json.dumps(data), headers=rest_headers, verify=True)

        if post_r.status_code in [requests.codes.ok, requests.codes.accepted]:
            returned_data = post_r.json()
        else:
            print "GET %s failed with error code %s" % (url, post_r.status_code)
            returned_data = {}

        if not _recursive:
            json_data = returned_data
            break

        if isinstance(returned_data, list):            
            if returned_data:
                json_data = json_data + returned_data
                _skip += _limit
            else:
                break
            if len(returned_data) < _limit:
                break
        else:
            break

    return json_data

def print_table(headers, rows):
    table = prettytable.PrettyTable(headers)
    table.hrules = prettytable.FRAME
    for header in headers:
        table.align[header] = "l"
    for row in rows:
        table.add_row(row)
    print table

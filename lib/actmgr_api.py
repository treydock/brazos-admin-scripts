import json
import logging
import requests
import sys
from urlparse import urljoin

logger = logging.getLogger()

def get_status(url, headers, name = 'CLOSED'):
    json_data = {}
    _url = urljoin(url, "/api/statuses/%s" % name)
    get_r = requests.get(_url, headers=headers, verify="/etc/pki/tls/certs/ca-bundle.crt")

    if get_r.status_code == requests.codes.ok:
        json_data = get_r.json()
    else:
        logger.fatal("Failed to retrieve %s status data...exiting", name)
        sys.exit(1)
    return json_data.get("status")


def get_accounts(url, headers, params):
    json_data = {}
    _url = urljoin(url, "/api/accounts")
    _page = 1
    _all_accounts = []
    while True:
        params["page"] = _page
        get_r = requests.get(_url, params=params, headers=headers, verify="/etc/pki/tls/certs/ca-bundle.crt")

        if get_r.status_code == requests.codes.ok:
            json_data = get_r.json()
        else:
            logger.fatal("Failed to retrieve account...exiting")
            sys.exit(1)
        _accounts = json_data.get("accounts")
        if _accounts:
            _all_accounts = _all_accounts + _accounts
            _page += 1
        else:
            break
    return _all_accounts


def update_account(url, headers, account_id, data):
    _url = urljoin(url, "/api/accounts/%s" % account_id)
    data = {"account": data}
    put_r = requests.put(_url, data=json.dumps(data), headers=headers, verify="/etc/pki/tls/certs/ca-bundle.crt")

    if put_r.status_code ==requests.codes.ok:
        return put_r.json()
    else:
        logging.error("Failed to update account, code: %s", put_r.status_code)
        return None


def get_groups(url, headers, params):
    json_data = {}
    _url = urljoin(url, "/api/groups")
    _page = 1
    _all_groups = []
    while True:
        params["page"] = _page
        get_r = requests.get(_url, params=params, headers=headers, verify=True)

        if get_r.status_code == requests.codes.ok:
            json_data = get_r.json()
        else:
            logger.fatal("Failed to retrieve groups...exiting")
            sys.exit(1)
        _groups = json_data
        if _groups:
            _all_groups = _all_groups + _groups
            _page += 1
        else:
            break
    return _all_groups

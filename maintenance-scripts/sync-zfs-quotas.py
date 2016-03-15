#!/usr/bin/env python

import os, sys, re
import logging
import pprint
import subprocess
import argparse
from sh import zfs

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(BASE_DIR)
from lib.config import load_config
from lib.logs import setup_logging
from lib.local_ldap import LocalLdap, LdapUser, LdapGroup
from lib.byte_converter import human2bytes, bytes2human

logger = logging.getLogger()

active_only = True
search_base = "ou=People,dc=brazos,dc=tamu,dc=edu"
search_filter = "objectClass=systemQuotas"
search_return_attribs = [
    "dn",
    "uid",
    "uidNumber",
    "mail",
    "quota",
    "loginShell",
]
search_scope = "one"

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', help="set debug level (0-4)", dest="debug", nargs="?", const=0, type=int)
    parser.add_argument('--noop', help="only print actions, make no changes", dest="noop", action="store_true", default=False)
    parser.add_argument('--config-env', help="config environment", dest="config_env", default="production")
    args = parser.parse_args()

    return args

def print_data(msg, user):
    #if user["zfs_quota"]:
    _zfs_quota = bytes2human(user["zfs_quota"])
    #else:
    #    _zfs_quota = "None"
    print "%s - user=%s, uid=%s, email=%s, used=%s, current-quota=%s, ldap-quota=%s" \
        % (msg, user["username"], user["uid"], user["mail"], bytes2human(user["zfs_used"]), _zfs_quota, bytes2human(user["ldap_quota"]))

def main():
    args = parse_args()
    config = load_config()
    config_env = config[args.config_env]["ldap"]

    # Setup logging
    setup_logging(debug=args.debug, noop=False)

    logger.debug4("OPTIONS: %s" % vars(args))
    logger.debug4("CONFIG: %s" % config_env)

    _ldap_url = config_env.get("url")
    _use_tls = config_env.get("tls")
    _bind_dn = config_env.get("bind_dn", None)
    _bind_pass = config_env.get("bind_pass", None)

    local_ldap = LocalLdap(url=_ldap_url[0], use_tls=_use_tls, bind_dn=_bind_dn, bind_pass=_bind_pass, log_level=None)
    ldap_users = local_ldap.paged_search(base=search_base, sfilter=search_filter, attrlist=search_return_attribs, scope=search_scope)

    users_over_quota = []
    users_over_ldap_quota = []
    users_over_zfs_quota = []
    users_ldap_quota_mismatch = []
    zfs_set_cmds = []

    for user in ldap_users:
        _user_data = {}
        _user = LdapUser()
        _user.setattrs(data=user, listvals=["mail"])
        _username = _user.uid
        _uid = _user.uidNumber
        _shell = _user.loginShell
        _quota = _user.quota
        if hasattr(_user, "mail"):
            _mail = ",".join(_user.mail)
        else:
            _mail = ""

        if active_only and _shell != "/bin/bash":
            continue

        mount, softlimit, hardlimit, softinode, hardinode = re.findall(r"^(.*):([0-9]+),([0-9]+),([0-9]+),([0-9]+)$", _quota)[0]
        _ldap_quota = int(hardlimit) * 1024
        zfs_fs = "tank%s" % mount

        # Get current ZFS quota
        userquota_args = ["get", "-H", "-p", "-o", "value", "userquota@%s" % _username, zfs_fs]
        logger.debug("Executing: zfs %s", " ".join(userquota_args))
        userquota_output = zfs(userquota_args)
        _userquota = userquota_output.strip()
        if _userquota != "-":
            current_quota = int(_userquota)
        else:
            current_quota = 0

        # Get current used space
        userused_args = ["get", "-H", "-p", "-o", "value", "userused@%s" % _username, zfs_fs]
        logger.debug("Executing: zfs %s", " ".join(userused_args))
        userused_output = zfs(userused_args)
        _userused = userused_output.strip()
        if _userused != "-":
            current_used = int(_userused)
        else:
            current_used = 0

        _user_data["username"] = _username
        _user_data["uid"] = _uid
        _user_data["mail"] = _mail
        _user_data["zfs_fs"] = zfs_fs
        _user_data["ldap_quota"] = _ldap_quota
        _user_data["zfs_quota"] = current_quota
        _user_data["zfs_used"] = current_used

        if current_used >= _ldap_quota and current_used >= current_quota:
            users_over_quota.append(_user_data)
        elif current_used and current_used >= _ldap_quota:
            users_over_ldap_quota.append(_user_data)
        elif current_used and current_used >= current_quota:
            users_over_zfs_quota.append(_user_data)

        if _ldap_quota != current_quota:
            users_ldap_quota_mismatch.append(_user_data)
            zfs_set_cmd = [
                "set", "userquota@%s=%s" % (_username, _ldap_quota), zfs_fs
            ]
            zfs_set_cmds.append(zfs_set_cmd)

    for user in users_over_quota:
        print_data("WARNING: over quota", user)
    print "---------"

    for user in users_over_ldap_quota:
        print_data("WARNING: over LDAP quota", user)
    print "---------"

    for user in users_over_zfs_quota:
        print_data("WARNING: over ZFS quota", user)
    print "---------"

    for user in users_ldap_quota_mismatch:
        print_data("WARNING: quota does not match LDAP", user)
    print "---------"

    for zfs_set_cmd in zfs_set_cmds:
        logger.debug("Executing: zfs %s", " ".join(zfs_set_cmd))
        if args.noop:
            pass
        else:
            try:
                zfs_set_output = zfs(zfs_set_cmd)
            except ErrorReturnCode:
                logger.error("FAILED to execute zfs set: %s", zfs_set_output)


if __name__ == '__main__':
    main()

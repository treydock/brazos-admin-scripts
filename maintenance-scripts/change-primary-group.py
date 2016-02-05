#!/usr/bin/env python

import argparse
import os, sys
import logging
import json
import ldap
from sh import sacctmgr, find, ErrorReturnCode

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(BASE_DIR)
from lib import actmgr_api
from lib.config import load_config
from lib.logs import setup_logging
from lib.local_ldap import LocalLdap, LdapUser, LdapGroup

logger = logging.getLogger()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--username', help="User's username", required=True)
    parser.add_argument('--new-group', help="New group to assign", required=True)
    parser.add_argument('--old-group', help="Old group", required=True)
    parser.add_argument('--config-env', help="config environment", dest="config_env", default="production")
    parser.add_argument('--debug', help="set debug level (0-4)", dest="debug", nargs="?", const=0, type=int)
    args = parser.parse_args()
    options = vars(args)

    config = load_config()
    config_env = config[args.config_env]["ldap"]
    _account_home_config = config[args.config_env].get("account_home")
    _auth_token = config[args.config_env].get("api_auth_token")
    _host = config[args.config_env].get("host")
    _port = config[args.config_env].get("port")
    _https = config[args.config_env].get("https")
    _protocol = 'https' if _https else 'http'
    _url = "%s://%s:%s/" % (_protocol, _host, _port) if _port else "%s://%s/" % (_protocol, _host)
    _json_headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Token token=%s" % _auth_token,
    }

    # Setup logging
    setup_logging(debug=args.debug, noop=False)

    logger.debug4("OPTIONS: %s" % options)
    logger.debug4("CONFIG: %s" % config_env)

    _ldap_url = config_env.get("url")
    _use_tls = config_env.get("tls")
    _bind_dn = config_env.get("bind_dn", None)
    _bind_pass = config_env.get("bind_pass", None)

    group_search_base = "ou=Groups,dc=brazos,dc=tamu,dc=edu"
    user_search_base = "ou=People,dc=brazos,dc=tamu,dc=edu"
    new_group_filter = "cn=%s" % args.new_group
    old_group_filter = "cn=%s" % args.old_group
    user_filter = "uid=%s" % args.username
    group_attribs = [
        "dn",
        "cn",
        "gidNumber",
        "uniqueMember",
        "slurmAccountName",
    ]
    user_attribs = [
        "dn",
        "uid",
        "gidNumber",
    ]
    scope = "one"

    local_ldap = LocalLdap(url=_ldap_url[0], use_tls=_use_tls, bind_dn=_bind_dn, bind_pass=_bind_pass, log_level=None)
    new_group_results = local_ldap.paged_search(base=group_search_base, sfilter=new_group_filter, attrlist=group_attribs, scope=scope)
    old_group_results = local_ldap.paged_search(base=group_search_base, sfilter=old_group_filter, attrlist=group_attribs, scope=scope)
    user_results = local_ldap.paged_search(base=user_search_base, sfilter=user_filter, attrlist=user_attribs, scope=scope)

    logger.debug("LDAP new group: %s", json.dumps(new_group_results))
    logger.debug("LDAP old group: %s", json.dumps(old_group_results))
    logger.debug("LDAP user: %s", json.dumps(user_results))

    if len(new_group_results) != 1 or len(old_group_results) != 1:
        logger.error("More than one group LDAP result returned")
        sys.exit(1)
    if len(user_results) != 1:
        logger.error("More than one user LDAP result returned")
        sys.exit(1)

    ldap_group_new = LdapGroup()
    ldap_group_new.setattrs(data=new_group_results[0], listvals=["uniqueMember"])
    ldap_group_old = LdapGroup()
    ldap_group_old.setattrs(data=old_group_results[0], listvals=["uniqueMember"])
    ldap_user = LdapUser()
    ldap_user.setattrs(data=user_results[0])

    # Not all LDAP groups have slurmAccountName attribute
    if not hasattr(ldap_group_new, 'slurmAccountName'):
        ldap_group_new.slurmAccountName = ldap_group_new.cn
    if not hasattr(ldap_group_old, 'slurmAccountName'):
        ldap_group_old.slurmAccountName = ldap_group_old.cn

    # Check certain things exist to avoid sending None to LDAP which could delete more than we want
    _ldap_group_new_valid = True
    _ldap_group_old_valid = True
    for a in ['dn', 'gidNumber', 'slurmAccountName', 'uniqueMember', 'cn']:
        if not hasattr(ldap_group_new, a):
            _ldap_group_new_valid = False
        elif getattr(ldap_group_new, a) is None:
            _ldap_group_new_valid = False
        if not hasattr(ldap_group_old, a):
            _ldap_group_old_valid = False
        elif getattr(ldap_group_old, a) is None:
            _ldap_group_old_valid = False
    if not _ldap_group_new_valid:
        logger.error("LDAP group %s does not have all necessary information", args.new_group)
    if not _ldap_group_old_valid:
        logger.error("LDAP group %s does not have all necessary information", args.old_group)
    if ldap_user.dn is None or ldap_user.uid is None or ldap_user.gidNumber is None:
        logger.error("LDAP user %s does not have all necessary information", args.username)

    ## Update account management database
    get_group_params = {
        "name": args.new_group,
    }
    group_data = actmgr_api.get_groups(_url, _json_headers, get_group_params)
    group = group_data[0]
    logger.debug("Group API data: %s", json.dumps(group))

    get_account_params = {
        "username": args.username,
    }
    account_data = actmgr_api.get_accounts(_url, _json_headers, get_account_params)
    account = account_data[0]
    logger.debug("Account API data: %s", json.dumps(account))

    update_account_data = {
        "primary_group_id": group['id'],
    }
    account = actmgr_api.update_account(_url, _json_headers, account['id'], update_account_data)
    if not account or not account["account"]:
        logger.error("Failed to update account management data")
        sys.exit(1)
    logger.debug("Account updated API data: %s", json.dumps(account))
    account = account["account"]

    ## Update LDAP
    if ldap_user.gidNumber != ldap_group_new.gidNumber:
        logger.info("LDAP replace %s gidNumber=%s", ldap_user.dn, ldap_group_new.gidNumber)
        local_ldap.modify(ldap_user.dn, [(ldap.MOD_REPLACE, 'gidNumber', ldap_group_new.gidNumber)])
    else:
        logger.warn("Skipping LDAP update of user gidNumber - already updated")

    if ldap_user.dn not in ldap_group_new.uniqueMember:
        logger.info("LDAP add to %s uniqueMember=%s", ldap_group_new.dn, ldap_user.dn)
        local_ldap.modify(ldap_group_new.dn, [(ldap.MOD_ADD, "uniqueMember", ldap_user.dn)])
    else:
        logger.warn("Skipping LDAP update of group add uniqueMember - already updated")

    if ldap_user.dn in ldap_group_old.uniqueMember:
        logger.info("LDAP delete from %s uniqueMember=%s", ldap_group_old.dn, ldap_user.dn)
        local_ldap.modify(ldap_group_old.dn, [(ldap.MOD_DELETE, "uniqueMember", ldap_user.dn)])
    else:
        logger.warn("Skipping LDAP update of group delete uniqueMember - already updated")

    ## Update SLURM
    _slurm_account = account["primary_group"]["alias"]
    _slurm_accounts = [g["alias"] for g in account["groups"] if "alias" in g]
    if _slurm_account not in _slurm_accounts:
        _slurm_accounts.append(_slurm_account)

    if not _slurm_account or not _slurm_accounts:
        logger.error("SLURM accounts not correctly determined")
        sys.exit(1)

    sacctmgr_check_args = [
        "--parsable2", "--noheader", "show", "user",
        "name=%s" % args.username, "account=%s" % _slurm_account,
        "format=User,DefaultAccount,Account", "WithAssoc",
    ]
    logger.debug("Executing: sacctmgr %s", " ".join(sacctmgr_check_args))
    try:
        output = sacctmgr(sacctmgr_check_args)
    except ErrorReturnCode:
        logger.error("FAILED to check if SLURM account already exists.")
        sys.exit(1)
    expected_output = "%s|%s|%s" % (args.username, _slurm_account, _slurm_account)
    existing_slurm_accounts = output.split(os.linesep)
    if expected_output not in existing_slurm_accounts:
        sacctmgr_delete_args = ["-i", "delete", "user","where", "name=%s" % args.username, "account=%s" % ldap_group_old.slurmAccountName]
        logger.debug("Executing: sacctmgr %s", " ".join(sacctmgr_delete_args))
        try:
            output = sacctmgr(sacctmgr_delete_args)
        except ErrorReturnCode:
            logger.error("FAILED to delete user from SLURM.")
            sys.exit(1)

        sacctmgr_create_args = [
            "-i", "create", "user", args.username,
            "account=%s" % ",".join(_slurm_accounts),
            "defaultaccount=%s" % _slurm_account,
        ]
        logger.debug("Executing: sacctmgr %s", " ".join(sacctmgr_create_args))
        try:
            output = sacctmgr(sacctmgr_create_args)
        except ErrorReturnCode:
            logger.error("FAILED to retrieve all user names from SLURM.")
            sys.exit(1)
    else:
        logger.warn("Skipping SLURM account modifications - record already exists")

    ## Update permissions of $HOME and $SCRATCH
    home_path = os.path.join(_account_home_config.get("base_dir"), args.username)
    scratch_path = os.path.join(_account_home_config.get("scratch_base"), args.username)
    find_home_args = [
        home_path, "-group", args.old_group, "-exec", "chgrp", args.new_group, '{}', ';'
    ]
    logger.info("Changing group ownership of files under %s", home_path)
    logger.debug("Executing: find %s", " ".join(find_home_args))
    try:
        find(find_home_args)
    except ErrorReturnCode, e:
        logger.error("Failed to fix permissions of %s: %s", home_path, e.stderr)
        sys.exit(1)

    find_scratch_args = [
        scratch_path, "-group", args.old_group, "-exec", "chgrp", args.new_group, '{}', ';'
    ]
    logger.info("Changing group ownership of files under %s", scratch_path)
    logger.debug("Executing: find %s", " ".join(find_scratch_args))
    try:
        find(find_scratch_args)
    except ErrorReturnCode, e:
        logger.error("Failed to fix permissions of %s", scratch_path, e.stderr)
        sys.exit(1)

    sys.exit(0)

if __name__ == '__main__':
    main()

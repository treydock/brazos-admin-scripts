#!/usr/bin/env python

import argparse
import os, sys, stat
import logging
from pwd import getpwuid, getpwnam
import paramiko
import requests
import json
from urlparse import urljoin
import prettytable
from sh import du, rm, unlink, sacctmgr, ErrorReturnCode

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(BASE_DIR)
from lib import actmgr_api
from lib.config import load_config
from lib.logs import setup_logging
from lib.byte_converter import bytes2human

logger = logging.getLogger()

# Get /fdata usage from quota reports
BEEGFS_USED = {}
if os.path.isfile('/tmp/beegfs_userspace.json'):
    with open('/tmp/beegfs_userspace.json') as _json_file:
        _beegfs_used = json.load(_json_file)
    for _user in _beegfs_used:
        BEEGFS_USED[_user["name"]] = int(_user["space"])
FDATA_USERS = []


def get_space_used(path, host=None):
    if not os.path.isdir(path):
        return 0
    _user = os.path.basename(path)
    # Get /home usage from ZFS
    if os.path.dirname(path) == "/home":
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(host, username='root')
        stdin, stdout, stderr = ssh.exec_command("zfs get -H -p -o value userused@%s tank/home" % _user)
        out = stdout.read().splitlines()
        logger.debug1("HOME zfs output for %s: %s", _user, out)
        if type(out) is list:
            _value = out[0]
        else:
            _value = out
        if _value == '-':
            _value = 0
        return int(_value)
    # Get /fdata usage from quota reports in /tmp
    if "/fdata" in path:
        if _user in FDATA_USERS:
            return 0
        if _user in BEEGFS_USED:
            FDATA_USERS.append(_user)
            return int(BEEGFS_USED[_user])
    # If the above methods failed for some reason, use du
    logger.debug1("Executing: du -s -x %s", path)
    _du_out = du("-s", "-x", path)
    _du_split = _du_out.split()

    _du_used = _du_split[0]
    _du_path = _du_split[1]
    if _du_path != path:
        logger.error("du %s invalid", path)
        return False
    return int(_du_used) * 1024

class AccountHome(object):
    def __init__(self, username, config, options={}):
        self.username = username
        self.home = os.path.join(config["base_dir"], self.username)
        self.scratch = os.path.join(config["scratch_base"], self.username)
        self.verbose = options.get('debug')
        self.noop = options.get('noop')
        self.force = options.get('force')
        self.check_extra_directories(extra_dirs=config.get("extra_scratch_directories", []))

    def home_exists(self):
        if os.path.isdir(self.home):
            return True
        else:
            return False

    def scratch_exists(self):
        if os.path.isdir(self.scratch):
            return True
        else:
            return False

    def check_extra_directories(self, extra_dirs):
        self.extra_directories = []
        if extra_dirs:
            for _extra_dir in extra_dirs:
                _dir = os.path.join(_extra_dir, self.username)
                if os.path.isdir(_dir):
                    self.extra_directories.append(_dir)
        if len(self.extra_directories) > 0:
            self.extra_directories_exist = True
        else:
            self.extra_directories_exist = False

    def cleanup(self):
        if not self.home_exists() and not self.scratch_exists() and not self.extra_directories_exist:
            logger.debug("HOME, SCRATCH and extra directories do not exist: %s, skipping.", self.username)
            return True

        if self.home_exists():
            _rm_home = True
            self.check_path_owner(self.home)
            logger.info("Removing %s", self.home)
            self.rmdir(self.home)
        else:
            _rm_home = False
            logger.debug("HOME not found for %s", self.username)

        if self.scratch_exists():
            _rm_scratch = True
            self.check_path_owner(self.scratch)
            logger.info("Removing %s", self.scratch)
            self.rmdir(self.scratch)
        else:
            _rm_scratch = False
            logger.debug("SCRATCH not found for %s", self.username)

        for _dir in self.extra_directories:
            self.check_path_owner(_dir)
            logger.info("Removing %s", _dir)
            self.rmdir(_dir)

        if self.noop:
            return True

        if _rm_home:
            if not self.home_exists():
                logger.info("SUCCESS: Removed %s", self.home)
            else:
                logger.error("Not removed %s", self.home)
        if _rm_scratch:
            if not self.scratch_exists():
                logger.info("SUCCESS: Removed %s", self.scratch)
            else:
                logger.error("Not removed %s", self.scratch)

        for _dir in self.extra_directories:
            if os.path.isdir(_dir):
                logger.error("Not removed %s", _dir)
            else:
                logger.info("SUCCESS: Removed %s", _dir)

        return True


    def rmdir(self, path):
        if os.path.islink(path):
            _link = True
        else:
            _link = False
        if _link:
            logger.debug1("Executing: unlink %s", path)
        else:
            logger.debug1("Executing: rm -rf %s", path)
        if self.noop: return True
        try:
            if _link:
                output = unlink(path)
            else:
                output = rm("-rf", path)
        except ErrorReturnCode:
            logger.error("FAILED deleting %s: Exit code %s", path, output.exit_code)
            logger.error(output)
            return False
        logger.info("%s deleted.", path)
        return True

    def check_path_owner(self, path):
        if not os.path.isdir(path):
            return
        try:
            _uid = os.stat(path).st_uid
            _owner = getpwuid(_uid).pw_name
        except KeyError as e:
            logger.warn("OWNERSHIP MISMATCH: %s owned by %s not %s", path, _uid, self.username)
            logger.warn(e)
            return False
        logger.debug4("%s owned by %s", path, _owner)
        if _owner not in [self.username, "badquota", "root"]:
            logger.warn("OWNERSHIP MISMATCH: %s owned by %s not %s", path, _owner, self.username)
            return False
        return True


class SlurmAccount(object):
    all_usernames = []

    @classmethod
    def get_all(cls):
        if cls.all_usernames:
            return cls.all_usernames

        sacctmgr_args = ["--parsable2", "--noheader", "show", "user", "format=user"]
        logger.debug1("Executing: sacctmgr %s", " ".join(sacctmgr_args))
        try:
            output = sacctmgr(sacctmgr_args)
        except ErrorReturnCode:
            logger.error("FAILED to retrieve all user names from SLURM.")
            sys.exit(1)
        cls.all_usernames = output.splitlines()
        return cls.all_usernames

    def __init__(self, username, options={}):
        self.username = username
        self.verbose = options.get('debug')
        self.noop = options.get('noop')
        self.force = options.get('force')

    def delete(self):
        if not self.exists():
            logger.debug("SLURM account does not exist: %s, skipping.", self.username)
            return True

        logger.info("Deleting SLURM account: %s", self.username)
        sacctmgr_args = ["-i", "delete", "user","where", "name=%s" % self.username]
        logger.debug1("Executing: sacctmgr %s", " ".join(sacctmgr_args))
        if self.noop: return True
        try:
            output = sacctmgr(sacctmgr_args)
        except ErrorReturnCode:
            logger.error("FAILED deleting SLURM account %s: Exit code %s", self.username, exit_code)
            logger.error(output)
            return False
        logger.info("%s SLURM account deleted.", self.username)
        return True

    def exists(self):
        if self.username in self.__class__.get_all():
            return True
        else:
            return False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config-env', help="config environment", dest="config_env", default="production")
    parser.add_argument('--force', help="force bootstrap of account even if files exist", dest="force", action="store_true", default=False)
    parser.add_argument('--debug', help="set debug level (0-4)", dest="debug", nargs="?", const=0, type=int)
    parser.add_argument('--noop', help="only print actions, make no changes", dest="noop", action="store_true", default=False)
    parser.add_argument('--report', help="generate report of what will be done", dest="report", action="store_true", default=False)
    parser.add_argument('--report-space', help="report on space that can be removed", dest="report_space", action="store_true", default=False)
    parser.add_argument('--account', help="account to create", dest="account", default=None)
    parser.add_argument('--exclude-accounts', nargs="+", help="accounts to exclude", dest="exclude_accounts", default=[])
    args = parser.parse_args()
    options = vars(args)

    # Set values based on loaded config
    config = load_config()
    _auth_token = config[args.config_env].get("api_auth_token")
    _account_home_config = config[args.config_env].get("account_home")
    _cleanup_exclude = _account_home_config.get("cleanup_exclude", []) + args.exclude_accounts
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
    setup_logging(debug=args.debug, noop=args.noop)

    logger.debug4("OPTIONS: %s" % options)
    logger.debug4("CONFIG: %s" % config)

    # Get status ID
    status = actmgr_api.get_status(url=_url, headers=_json_headers, name='CLOSED')
    logger.debug1("STATUS: %s", status)
    status_id = status.get("id")

    # Get accounts and perform account cleanup steps
    if args.account:
        accounts = actmgr_api.get_accounts(url=_url, headers=_json_headers, params={"username": args.account, "status_id": status_id})
    else:
        accounts = actmgr_api.get_accounts(url=_url, headers=_json_headers, params={"status_id": status_id})
    logger.debug4("Number of accounts returned: %s", len(accounts))

    _report = []
    for account in accounts:
        logger.debug4("Account data: %s", json.dumps(account))
        _username = account["username"]
        if _username in _cleanup_exclude:
            logger.info("EXCLUDED: %s", _username)
            continue
        try:
            _shell = getpwnam(_username).pw_shell
        except KeyError:
            logger.warn("Unable to get shell for %s", _username)
            _shell = None
        if _shell != '/sbin/nologin':
            logger.warn("User %s shell %s != /sbin/nologin", _username, _shell)
            continue

        _account_home = AccountHome(username=_username, config=_account_home_config, options=options)
        _slurm_account = SlurmAccount(username=_username, options=options)

        if args.report:
            _account_home.check_path_owner(_account_home.home)
            _account_home.check_path_owner(_account_home.scratch)
            for _dir in _account_home.extra_directories:
                _account_home.check_path_owner(_dir)
            _data = {}
            _data["username"] = _username
            _data["HOME"] = _account_home.home_exists()
            _data["SCRATCH"] = _account_home.scratch_exists()
            _data["EXTRA"] = _account_home.extra_directories
            _data["SLURM"] = _slurm_account.exists()
            if args.report_space:
                _data["HOME_USED"] = get_space_used(host=_account_home_config["server"], path=_account_home.home)
                _data["SCRATCH_USED"] = get_space_used(path=_account_home.scratch)
                _data["EXTRA_USED"] = 0
                for _dir in _account_home.extra_directories:
                    _data["EXTRA_USED"] += get_space_used(path=_dir)
            _report.append(_data)
        else:
            _account_home.cleanup()
            _slurm_account.delete()
    if args.report:
        if args.report_space:
            table = prettytable.PrettyTable(["Username", "HOME", "HOME-USED", "SCRATCH", "SCRATCH-USED", "EXTRA", "EXTRA-USED", "SLURM"])
        else:
            table = prettytable.PrettyTable(["Username", "HOME", "SCRATCH", "EXTRA", "SLURM"])
        table.hrules = prettytable.FRAME
        _home_total = 0
        _home_used_total = 0
        _scratch_total = 0
        _scratch_used_total = 0
        _extra_total = 0
        _extra_used_total = 0
        _slurm_total = 0
        for r in sorted(_report, key=lambda k: k["username"]):
            _home = r["HOME"]
            _scratch = r["SCRATCH"]
            _extra = r["EXTRA"]
            _slurm = r["SLURM"]
            if _home:
                _home_total += 1
            if _scratch:
                _scratch_total += 1
            if _extra:
                _extra_total += len(_extra)
            if _slurm:
                _slurm_total += 1
            if args.report_space:
                _home_used = bytes2human(r["HOME_USED"])
                _home_used_total += r["HOME_USED"]
                _scratch_used = bytes2human(r["SCRATCH_USED"])
                _scratch_used_total += r["SCRATCH_USED"]
                _extra_used = bytes2human(r["EXTRA_USED"])
                _extra_used_total += r["EXTRA_USED"]
                table.add_row([r["username"], _home, _home_used, _scratch, _scratch_used, "\n".join(_extra), _extra_used, _slurm])
            else:
                table.add_row([r["username"], _home, _scratch, "\n".join(_extra), _slurm])
        if args.report_space:
            table.add_row(["", "", "", "", "", "", "", ""])
            table.add_row(["Total", _home_total, bytes2human(_home_used_total), _scratch_total, bytes2human(_scratch_used_total), _extra_total, bytes2human(_extra_used_total), _slurm_total])
        else:
            table.add_row(["", "", "", "", ""])
            table.add_row(["Total", _home_total, _scratch_total, _extra_total, _slurm_total])
        print table

if __name__ == '__main__':
    main()

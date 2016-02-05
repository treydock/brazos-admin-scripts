#!/usr/bin/env python

import argparse
from subprocess import Popen, PIPE
from datetime import date
from dateutil.relativedelta import relativedelta
from calendar import monthrange
import time
import dateutil.parser
import os, sys, re
from decimal import Decimal
import prettytable

BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
sys.path.append(BASE_DIR)
from lib.slurm import slurm_duration_to_sec

def cmp_start_end_time(start, end, debug=False):
    _start = dateutil.parser.parse(start).strftime("%s")
    _end = dateutil.parser.parse(end).strftime("%s")
    _sec = int(_end) - int(_start)
    return _sec

def cmp_start_end_suspended_time(start, end, suspend, debug=False):
    _end_start_sec = cmp_start_end_time(start=start, end=end, debug=debug)
    _suspend = slurm_time_to_sec(t=suspend, debug=debug)
    _sec = int(_end_start_sec) - int(_suspend)
    return _sec

TODAY = date.today()
LAST_MONTH = TODAY - relativedelta(months=1)
LAST_DAY_OF_MONTH=monthrange(LAST_MONTH.year, LAST_MONTH.month)[1]
DEFAULT_STARTTIME="%s-%02d-01T00:00:00" % (LAST_MONTH.year, LAST_MONTH.month)
DEFAULT_ENDTIME="%s-%02d-%sT23:59:59" % (LAST_MONTH.year, LAST_MONTH.month, LAST_DAY_OF_MONTH)

parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
parser.add_argument('--account', help="SLURM account", default=None)
parser.add_argument('--start', help="sacct starttime", default=DEFAULT_STARTTIME)
parser.add_argument('--end', help="sacct endtime", default=DEFAULT_ENDTIME)
parser.add_argument('--calc2', help="calculate using end-start times", action="store_true", default=False)
parser.add_argument('--calc3', help="calculate using end-start times minus suspended time", action="store_true", default=False)
parser.add_argument('--file', help='read sacct output from file instead of command', default=None)
parser.add_argument('--debug', help="debug output", action="store_true", default=False)
args = parser.parse_args()

if args.file:
    if not os.path.isfile(args.file):
        print "ERROR: File %s not found" % args.file
        sys.exit(1)
    with open(args.file, 'r') as file:
        out = file.read()
else:    
    cmd = [
        "sacct", "--allusers", "--parsable2", "--noheader", "--allocations", "--clusters", "brazos",
    ]
    if args.account:
        cmd += ["--accounts=%s" % args.account]
    cmd += [
        "--format", "user,account,elapsed,ncpus,start,end,suspended",
        "--state", "CANCELLED,COMPLETED,FAILED,NODE_FAIL,PREEMPTED,TIMEOUT",
    	"--starttime", args.start,
    	"--endtime", args.end,
    ]
    cmd_str = " ".join(cmd)
    print cmd_str

    process = Popen(cmd, stdout=PIPE)
    out, err = process.communicate()

users = {}
accounts = {}
cpu_hours_total = Decimal('0.0')
num_jobs_total = 0
for line in out.split(os.linesep):
    _line =  line.strip()
    if args.debug: print "_line: %s" % _line
    if not _line:
        continue
    _data = _line.split("|")
    if args.debug: print "_data: %s" % _data
    if args.calc2:
        _elapsed_sec = cmp_start_end_time(start=_data[4], end=_data[5], debug=args.debug)
    elif args.calc3:
        _elapsed_sec = cmp_start_end_suspended_time(start=_data[4], end=_data[5], suspend=_data[6], debug=args.debug)
    else:
        _elapsed_sec = slurm_duration_to_sec(t=_data[2], debug=args.debug)
    _username = _data[0]
    _account_name = _data[1]
    _hours = Decimal(str(_elapsed_sec)) / Decimal('3600.0')
    _ncpus = Decimal(_data[3])
    _cpu_hours = _hours * _ncpus
    if args.debug: print "H: %f C: %d - CH: %f" % (_hours, _ncpus, _cpu_hours)
    # Collect user data
    if _username in users:
        _user = users[_username]
        _user['cpu_hours'] += _cpu_hours
        _user['num_jobs'] += 1
    else:
        _user = {}
        _user['username'] = _username
        _user['account'] = _account_name
        _user['cpu_hours'] = _cpu_hours
        _user['num_jobs'] = 1
    users[_username] = _user
    # Collect account data
    if _account_name in accounts:
        _account = accounts[_account_name]
        _account['cpu_hours'] += _cpu_hours
        _account['num_jobs'] += 1
    else:
        _account = {}
        _account['account'] = _account_name
        _account['cpu_hours'] = _cpu_hours
        _account['num_jobs'] = 1
    accounts[_account_name] = _account
    # Collect totals
    cpu_hours_total += _cpu_hours
    num_jobs_total += 1

table = prettytable.PrettyTable(["Username", "Account", "CPU Hours", "Completed Jobs"])
table.hrules = prettytable.FRAME

# Display user usage
user_data = users.values()
for d in sorted(user_data, key=lambda k: k['cpu_hours'], reverse=True):
    _account = d['account']
    _cpu_hours = d['cpu_hours']
    _num_jobs = d['num_jobs']
    table.add_row([d['username'], _account, str(round(_cpu_hours, 1)), _num_jobs])

table.add_row(['', '', '', ''])

# Calculate account(s) percent usage and display account(s) usage
account_data = accounts.values()
for account in sorted(account_data, key=lambda k: k['cpu_hours'], reverse=True):
    _cpu_hours = account['cpu_hours']
    _num_jobs = account['num_jobs']
    _percent = (_cpu_hours / cpu_hours_total) * Decimal('100.0')
    _percent = round(_percent, 1)
    _cpu_hours_percent = "%s (%s%%)" % (str(round(_cpu_hours, 1)), str(_percent))
    table.add_row(['Total', account['account'], _cpu_hours_percent, _num_jobs])

# Display cluster or account total, depending if --account was used
table.add_row(['Total', '', int(round(cpu_hours_total, 1)), num_jobs_total])
print table

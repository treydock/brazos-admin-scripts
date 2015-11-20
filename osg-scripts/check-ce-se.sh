#!/bin/bash

. /etc/rc.d/init.d/functions

DEBUG=0

usage () {

cat << EOF
usage: $(basename $0) [OPTIONS]

This script tests the OSG presence of a cluster.

ARGUMENTS:
  None

OPTIONS:

    -c, --ce        FQDN of CE
    -s, --se        FQDN of SE
    -h, --help      Show this message
    -d, --debug     Show debug output

EXAMPLE:

$(basename $0) --ce ce01.brazos.tamu.edu --se srm.brazos.tamu.edu

EOF
}

ARGS=`getopt -o hdc:s: -l help,debug,ce:,se: -n "$0" -- "$@"`

[ $? -ne 0 ] && { usage; exit 1; }

eval set -- "${ARGS}"

while true; do
    case "$1" in
        -h|--help) usage ; exit 0 ;;
        -c|--ce) CE=$2 ; shift 2 ;;
        -s|--se) SE=$2 ; shift 2 ;;
        -d|--debug) DEBUG=1 ; shift ;;
        --) shift ; break ;;
        *) break ;;
  esac
done

if [ $DEBUG -eq 1 ]; then
    set -x
fi

if [[ "x${CE}" = "x" ]]; then
    echo "Must provide CE argument"
    usage
    exit 1
fi

if [[ "x${SE}" = "x" ]]; then
    echo "Must provide SE argument"
    usage
    exit 1
fi

grid-proxy-info -exists > /dev/null 2>&1
if [ $? -ne 0 ]; then
    grid-proxy-init
fi

# Test condor_ce_run
echo -n "Condor CE Run of /usr/bin/id"
id=`condor_ce_run -lr ${CE}:9619 /usr/bin/id -nu`
if [ $? -ne 0 ]; then
    echo_failure
    echo
else
    echo_success
    echo
    echo -n "OK. id=$id"
    echo_success
    echo
fi

srcfile=/tmp/proc_version_$$
cp /proc/version $srcfile
chmod 644 $srcfile

ftppath="${HOME}/proc_version"
srmpath="${HOME}/proc_version"

# Test GridFTP copy
echo -n "GSIFTP to ${CE}"
[ -f $ftppath ] && rm -f $ftppath
globus-url-copy file:///${srcfile} gsiftp://${CE}${ftppath}
if [ $? -eq 0 ]; then
    echo_success
    echo
else
    echo_failure
    echo
fi
condor_ce_run -lr ${CE}:9619 /bin/rm $ftppath

# Test SRMCP
echo -n "SRMCP v2 to ${SE}"
[ -f $srmpath ] && rm -f $srmpath
srmurl=srm://${SE}:8443/srm/v2/server
ls -l $srcfile
srmcp -2  file:///$srcfile ${srmurl}\?SFN=${srmpath}
if [ $? -eq 0 ]; then
    echo_success
    echo
    echo "ls via globus:"
    condor_ce_run -lr ${CE}:9619 /bin/ls -l $srmpath
else
    echo_failure
    echo
fi
/bin/rm -f $srcfile

# Test srmrm
echo -n "SRMRM v2 ${srmurl}"
srmrm -srm_protocol_version=2 ${srmurl}\?SFN=${srmpath}
if [ $? -ne 0 ]; then
    echo_failure
    echo
    condor_ce_run -lr ${CE}:9619 /bin/rm $srmpath
else
    echo_success
    echo
fi
exit 0

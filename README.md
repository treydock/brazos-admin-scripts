
* [Install](#install)
* [Usage](#usage)
    * [Maintenance Scripts](#maintenance-scripts)
        * [cleanup_disabled_accounts.py](#cleanup_disabled_accountspy)
        * [change-primary-group.py](#change-primary-grouppy)
        * [sync-zfs-quotas.py](#sync-zfs-quotaspy)
    * [SLURM Scripts](#slurm-scripts)
        * [sacct-account-summary.py](#sacct-account-summarypy)
        * [sacct-cpu-hours.py](#sacct-cpu-hourspy)
    * [OSG Scripts](#osg-scripts)
        * [check-ce-se.sh](#check-ce-sesh)
        * [gums-check-dn.sh](#gums-check-dnsh)
        * [gums-find-by-username.sh](#gums-find-by-usernamesh)
    * [Node Scripts](#node-scripts)
        * [update_slurm.sh](#update_slurmsh)
        * [sync_slurm_conf.sh](#sync_slurm_confsh)
    * [Pulp Scripts](#pulp-scripts)
        * [repos.py](#repospy)
        * [content.py](#contentpy)
        * [tasks.py](#taskspy)
        * [cleanup.py](#cleanuppy)

## Install

Rename the following files and update their config values:

    cp etc/settings.yml.example etc/settings.yml

Scripts that use Python and SSL do not work with available libraries for doing SSL verification when SNI is used, so a virtualenv must be setup

    virtualenv --no-site-packages ./python-env
    ./python-env/bin/pip install -r ./.requirements.txt

## Usage

### Maintenance Scripts

##### `cleanup_disabled_accounts.py`

Removes or reports on directories that belong to disabled accounts.

Report:

    ./maintenance-scripts/cleanup_disabled_accounts.py --noop --report --report-space

Run through removal without actually removing anything

    ./maintenance-scripts/cleanup_disabled_accounts.py --noop

Run actual removal

    ./maintenance-scripts/cleanup_disabled_accounts.py

##### `change-primary-group.py`

Changes the primary GID of an account.  This will perform the following updates

* Set correct primary_group in account management application
* Set proper gidNumber for user in LDAP
* Remove user's DN from uniqueMember of old group
* Add user's DN to uniqueMember of new group
* Remove old user's SLURM record associating them to old group/account
* Add user's SLURM record associating them to new group/account
* find /home/$user -group $oldgroup -exec chgrp $newgroup {] \;
* find /fdata/scratch/$user -group $oldgroup -exec chgrp $newgroup {] \;

Example execution:

    ./python-env/bin/python ./maintenance-scripts/change-primary-group.py --username treydock-test1 --new-group general --old-group acad1

##### `sync-zfs-quotas.py`

Sync the ZFS quota information from LDAP to the local ZFS filesystem (tank/home).

Run command without making changes and only reporting information

    ./python-env/bin/python ./maintenance-scripts/sync-zfs-quotas.py --noop

Run command applying any necessary changes to ZFS quotas

    ./python-env/bin/python ./maintenance-scripts/sync-zfs-quotas.py

### SLURM Scripts

##### `sacct-account-summary.py`

Report on CPU hours for cluster or account for given amount of time.  Default is previous month.

    ./slurm-scripts/sacct-account-summary.py

Report on CPU hours for previous month for a specific account

    ./slurm-scripts/sacct-account-summary.py --account hepx


##### `sacct-cpu-hours.py`

Report on CPU hours used for given amount of time.  Default is previous month.

    ./slurm-scripts/sacct-cpu-hours.py

Report on CPU hours for previous month for a specific account

    ./slurm-scripts/sacct-cpu-hours.py --account hepx

### OSG Scripts

##### `check-ce-se.sh`

Run sanity checks against an OSG CE and SE.  The following items are tested

* Condor CE can run simple commands via condor\_ce\_run
* CE can transfer files via globus-url-copy
* SE can transfer files via srmcp
* SE can remove files via srmrm

Example usage:

    ./osg-scripts/check-ce-se.sh --ce ce01.brazos.tamu.edu --se srm.brazos.tamu.edu

##### `gums-check-dn.sh`

Check that the provided DN and username is mapped in GUMS

Example usage:

    ./osg-scripts/gums-check-dn.sh 'DN HERE' USERNAME

##### `gums-find-by-username.sh`

Find a GUMS mapped DN by username

Example usage:

    ./osg-scripts/gums-find-by-username.sh USERNAME

### Node Scripts

##### `update_slurm.sh`

Update SLURM on compute nodes and restart SLURM service.  Intended to be run via parallel SSH programs like clush

      clush -g all -b '/path/to/node-scripts/update_slurm.sh'

##### `sync_slurm_conf.sh`

Update SLURM config files from shared location.  Updates slurm.conf, nodes.conf, partitions.conf and cgroup.conf.

    clush -g all -b '/path/to/node-scripts/sync_slurm_conf.sh /home/admin/etc/slurm-node'

### Pulp Scripts

##### `repos.py`

This script is a used to query repos currently in Pulp.

Query all repos:

    ./python-env/bin/python -W ignore ./pulp-scripts/repos.py list

Query a specific repo:

    ./python-env/bin/python -W ignore ./pulp-scripts/repos.py list --repo test-osg33-el6

Query details about all repos (or specific repo using --repo flag):

    ./python-env/bin/python -W ignore ./pulp-scripts/repos.py list --details

##### `content.py`

This script is used to query content of specific repos.

List content of a specific repo:

    ./python-env/bin/python -W ignore ./pulp-scripts/content.py list brazos-el6

List specific content of a specific repo:

    ./python-env/bin/python -W ignore ./pulp-scripts/content.py list brazos-el6 --match slurm

Show a diff between two repos:

    ./python-env/bin/python -W ignore ./pulp-scripts/content.py diff --from-repo-id=test-osg32-el6 --to-repo-id=osg32-el6 --show-diff

##### `tasks.py`

This script will query Pulp tasks.

List all tasks:

    ./python-env/bin/python -W ignore ./pulp-scripts/tasks.py list

List all tasks with waiting or skipped state:

    ./python-env/bin/python -W ignore ./pulp-scripts/tasks.py list --list-state waiting skipped

##### `cleanup.py`

This script was intended to cleanup repos.  In practice it did not work, so the script currently just prints data.

Remove packages from brazos-centos-6-base that are not in centos-6-base, attempt to make brazos-centos-6-base have same packages as centos-6-base:

    ./python-env/bin/python -W ignore ./pulp-scripts/cleanup.py removeold --from-repo-id centos-6-base --to-repo-id=brazos-centos-6-base

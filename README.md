
* [Install](#install)
* [Usage](#usage)
    * [Maintenance Scripts](#maintenance-scripts)
        * [cleanup_disabled_accounts.py](#cleanup_disabled_accountspy)
    * [SLURM Scripts](#slurm-scripts)
        * [sacct-account-summary.py](#sacct-account-summarypy)
        * [sacct-cpu-hours.py](#sacct-cpu-hourspy)
    * [OSG Scripts](#osg-scripts)
        * [check-ce-se.sh](#check-ce-sesh)
        * [gums-check-dn.sh](#gums-check-dnsh)
        * [gums-find-by-username.sh](#gums-find-by-usernamesh)
    * [Node Scripts](#node-scripts)
        * [update_slurm.sh](#update_slurmsh)

## Install

Rename the following files and update their config values:

    cp etc/settings.yml.example etc/settings.yml

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

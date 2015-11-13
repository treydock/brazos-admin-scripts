
* [Install](#install)
* [Usage](#usage)
    * [Maintenance Scripts](#maintenance-scripts)
        * [cleanup_disabled_accounts.py](#cleanup_disabled_accountspy)
    * [SLURM Scripts](#slurm-scripts)
        * [sacct-cpu-hours.py](#sacct-cpu-hourspy)

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

##### `sacct-cpu-hours.py`

Report on CPU hours used for given amount of time.  Default is previous month.

    ./slurm-scripts/sacct-cpu-hours.py

Report on CPU hours for previous month for a specific account

    ./slurm-scripts/sacct-cpu-hours.py --account hepx

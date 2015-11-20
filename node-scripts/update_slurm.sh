#!/bin/bash

/etc/init.d/slurm stop &>/dev/null
if [ $? -ne 0 ]; then
	echo 1
	/etc/init.d/slurm restart &>/dev/null
	exit 1
fi

yum -y -q update slurm\* &>/dev/null
if [ $? -ne 0 ]; then
	echo 2
	exit 2
fi

/etc/init.d/slurm start &>/dev/null
if [ $? -ne 0 ]; then
	echo 3
	exit 3
fi

rpm -qa | grep slurm | sort

exit 0


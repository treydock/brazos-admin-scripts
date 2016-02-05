#!/bin/bash

DIR=$1
FILES_CHANGED=0

if [[ "x${DIR}" = "x" ]]; then
  echo "Must provide shared directory containing SLURM configs"
  exit 1
fi

for file in slurm.conf nodes.conf partitions.conf cgroup.conf ; do
  src=${DIR}/${file}
  dest=/etc/slurm/${file}

  cmp -s $dest $src
  if [ $? -ne 0 ]; then
    install -m 0644 $src $dest
    FILES_CHANGED=$((FILES_CHANGED + 1))
  fi
done

echo -n "CHANGED=$FILES_CHANGED "
if [ $FILES_CHANGED -gt 0 ]; then
  /etc/init.d/slurm restart &>/dev/null
  retval=$?
  echo "RESTART=$retval"
else
  retval=0
  echo "RESTART=no"
fi

exit $retval

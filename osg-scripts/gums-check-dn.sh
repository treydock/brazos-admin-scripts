#!/bin/bash

grid-proxy-info > /dev/null 2>&1
if [ $? -ne 0 ]; then
    grid-proxy-init -bits 1024
fi

[ -z "$1" ] && { echo "Must provide DN argument"; exit 1; }
[ -z "$2" ] && { echo "Must provide username argument"; exit 1; }

DN="$1"
USERNAME="$2"

server="/CN=$(hostname -f)"

mapUser=$(gums mapUser -s ${server} "${DN}")

if [ "${mapUser}" != "${USERNAME}" ]; then
    echo "DN does not map to username"
    exit 1
fi

gums mapAccount ${USERNAME} | grep -q "${DN}"
ret=$?

if [ $ret -ne 0 ]; then
    echo "username does not map to DN"
    exit 1
fi

echo "DN and username mappings are correct"

exit 0

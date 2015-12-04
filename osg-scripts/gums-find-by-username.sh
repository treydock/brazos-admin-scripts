#!/bin/bash

grid-proxy-info > /dev/null 2>&1
if [ $? -ne 0 ]; then
    grid-proxy-init -bits 1024
fi

[ -z "$1" ] && { echo "Must provide username argument"; exit 1; }

USERNAME="$1"

mapAccount=$(gums mapAccount ${USERNAME})

echo "Username: ${USERNAME}"
if [ -z "${mapAccount}" ]; then
    echo "Not found"
    exit 1
fi

echo "${mapAccount}"

exit 0

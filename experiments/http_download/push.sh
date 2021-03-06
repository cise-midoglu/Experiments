#!/bin/bash
#
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

CONTAINER=${DIR##*/}

#REPO=monroe1.cs.kau.se:5000
CONTAINERTAG=monroe/${CONTAINER}
#REPO=monroe1.cs.kau.se:5000
#CONTAINERTAG=${REPO}/monroe/${CONTAINER}

docker login && docker tag ${CONTAINER} ${CONTAINERTAG} && docker push ${CONTAINERTAG} && echo "Finished uploading ${CONTAINERTAG}"
#docker login ${REPO} && docker tag ${CONTAINER} ${CONTAINERTAG} && docker push ${CONTAINERTAG} && echo "Finished uploading ${CONTAINERTAG}"

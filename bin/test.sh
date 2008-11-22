#!/bin/sh

SCRIPT_DIR=`dirname $0`
APP_ROOT=`cd $SCRIPT_DIR; cd ..; pwd`
. ${APP_ROOT}/bin/env-test.sh

pushd ${APP_ROOT}/tests > /dev/null

python ${APP_ROOT}/tests/main.py

popd > /dev/null

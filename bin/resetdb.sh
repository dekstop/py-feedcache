#!/bin/sh

SCRIPT_DIR=`dirname $0`
APP_ROOT=`cd $SCRIPT_DIR; cd ..; pwd`
. ${APP_ROOT}/bin/env.sh

${APP_ROOT}/bin/dropdb.sh $@
${APP_ROOT}/bin/createdb.sh $@ || exit 1
${APP_ROOT}/bin/loadschema.sh $@ || exit 1

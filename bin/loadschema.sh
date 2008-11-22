#!/bin/sh

SCRIPT_DIR=`dirname $0`
APP_ROOT=`cd $SCRIPT_DIR; cd ..; pwd`
. ${APP_ROOT}/bin/env.sh

PSQL_ARGS="-q -v client_min_messages=ERROR -h ${DBHOST} -U ${DBUSER} ${DBNAME}"
PRELUDE="SET client_min_messages TO WARNING;"

echo "Loading ${SCHEMA_FILE} into database ${DBNAME}"
(echo "${PRELUDE}"; cat $SCHEMA_FILE ) | psql $PSQL_ARGS || exit 1

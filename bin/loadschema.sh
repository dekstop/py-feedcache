#!/bin/sh

bin=`dirname $0`
bin=`cd $bin; pwd`

. ${bin}/env.sh

SCHEMA_FILE=${FEEDCACHE_HOME}/sql/schema_postgres.sql

# Commandline parameters can override defaults
if [ $# == 1 ]; then
	DBNAME=$1
fi

PSQL_ARGS="-q -v client_min_messages=ERROR -h ${DBHOST} -U ${DBUSER} ${DBNAME}"
PRELUDE="SET client_min_messages TO WARNING;"

echo "Loading ${SCHEMA_FILE} into database ${DBNAME}"
(echo "${PRELUDE}"; cat $SCHEMA_FILE ) | psql $PSQL_ARGS || exit 1

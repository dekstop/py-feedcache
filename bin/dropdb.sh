#!/bin/sh

SCRIPT_DIR=`dirname $0`
APP_ROOT=`cd $SCRIPT_DIR; cd ..; pwd`
. ${APP_ROOT}/bin/env.sh

echo "Dropping database ${DBNAME}"
dropdb -h $DBHOST -U $DBUSER $DBNAME || exit 1

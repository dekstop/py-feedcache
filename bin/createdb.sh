#!/bin/sh

SCRIPT_DIR=`dirname $0`
APP_ROOT=`cd $SCRIPT_DIR; cd ..; pwd`
. ${APP_ROOT}/bin/env.sh

echo "Creating database ${DBNAME}"
createdb -h $DBHOST -U $DBUSER $DBNAME --encoding utf8 || exit 1
echo "Creating language plpgsql for database ${DBNAME}"
createlang -h $DBHOST -U $DBUSER -d $DBNAME plpgsql || exit 1

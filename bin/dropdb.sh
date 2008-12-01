#!/bin/sh

bin=`dirname $0`
bin=`cd $bin; pwd`

. ${bin}/env.sh

# Commandline parameters can override defaults
if [ $# == 1 ]; then
	DBNAME=$1
fi

echo "Dropping database ${DBNAME}"
dropdb -h $DBHOST -U $DBUSER $DBNAME || exit 1

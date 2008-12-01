#!/bin/sh

bin=`dirname $0`
bin=`cd $bin; pwd`

. ${bin}/env.sh

# Commandline parameters can override defaults
if [ $# == 1 ]; then
	DBNAME=$1
fi

echo "Creating database ${DBNAME}"
createdb -h $DBHOST -U $DBUSER $DBNAME --encoding utf8 || exit 1
echo "Creating language plpgsql for database ${DBNAME}"
createlang -h $DBHOST -U $DBUSER -d $DBNAME plpgsql || exit 1

#!/bin/sh

bin=`dirname $0`
bin=`cd $bin; pwd`

# First ask to exit politely.
${bin}/feedcache.sh stop

if [ $? != 0 ]
then
	# no processes running
	exit 1
fi

# Wait.
echo "Giving processes a grace period to shut down..."
sleep 20

# Stupid pp processes keep hanging. This kills the app. (This is not nice.)
pid=`pgrep -f "bin/updateloop.sh" | head -n 1`

if [ -n "$pid" ]
then
	echo "updateloop.sh process found, killing it and its children..."
	kill -- -${pid}
	echo "Done."
fi

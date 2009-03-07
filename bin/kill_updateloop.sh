#!/bin/sh

bin=`dirname $0`
bin=`cd $bin; pwd`

# First ask to exit politely.
${bin}/feedcache.sh stop

# Wait.
sleep 20

# Stupid pp processes keep hanging. This kills the app. (This is not nice.)
pid=`pgrep -f "bin/updateloop.sh" | head -n 1`
if [ -n $pid ]
then
	kill -- -${pid}
fi


#!/bin/bash

bin=`dirname $0`
bin=`cd $bin; pwd`

(while [ true ]; do
	nice -5 ${bin}/feedcache.sh update || exit 1
	sleep 1800
done)

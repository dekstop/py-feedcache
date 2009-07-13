#!/bin/bash

bin=`dirname $0`
bin=`cd $bin; pwd`

(while [ true ]; do
	nice -5 ${bin}/feedcache.sh update || exit 1
	nice -5 ${bin}/feedcache.sh index || exit 1
	nice -5 ${bin}/feedcache.sh uniq musicblogs --log-sql || exit 1
	sleep 800
done)

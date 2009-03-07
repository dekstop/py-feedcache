#!/bin/bash

bin=`dirname $0`
bin=`cd $bin; pwd`

LOGDIR=`cd $bin; cd ../log/; pwd`

(while [ true ]; do
	nice -5 ${bin}/feedcache.sh update || exit 1
	sleep 1800
done) 2>&1 | tee -a ${LOGDIR}/feedcache.log


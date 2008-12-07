#!/bin/bash

bin=`dirname $0`
bin=`cd $bin; pwd`

LOGDIR=`cd $bin; cd ../log/; pwd`

(while [ true ]; do
	nice -5 ${bin}/feedcache.sh update
	sleep 7200
done) 2>&1 | tee -a ${LOGDIR}/feedcache.log

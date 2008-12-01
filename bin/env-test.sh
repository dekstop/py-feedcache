#!/bin/sh
#
# Variables used to run tests.
# Overrides some of the parameters in env.sh
#

bin=`dirname $0`
bin=`cd $bin; pwd`

. ${bin}/env.sh

export DBENGINE=postgres
export DBHOST=localhost
export DBUSER=postgres
export DBPASSWORD=
export DBNAME=feedcache_test

export PYTHONPATH=${PYTHONPATH}:"${FEEDCACHE_HOME}/test"

#!/bin/sh
#
# Variables used for setting up the application.
#

bin=`dirname $0`
bin=`cd $bin; pwd`

export FEEDCACHE_VERSION=0.0-dev

export DBENGINE=postgres
export DBHOST=localhost
export DBUSER=postgres
export DBPASSWORD=
export DBNAME=feedcache_dev

export FEEDCACHE_HOME=`cd $bin; cd ..; pwd`
export FEEDCACHE_PID_DIR=/tmp

export PYTHONPATH="${FEEDCACHE_HOME}/src"

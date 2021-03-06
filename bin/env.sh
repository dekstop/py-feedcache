#!/bin/sh
#
# Variables used for setting up the application.
#

bin=`dirname $0`
bin=`cd $bin; pwd`

export FEEDCACHE_VERSION=0.0-dev

export PYTHON=/usr/bin/python

export DBENGINE=postgres
export DBHOST=localhost
#export DBUSER=postgres
#export DBPASSWORD=
export DBUSER=postgres
export DBPASSWORD=
export DBNAME=feedcache

export FEEDCACHE_HOME=`cd $bin; cd ..; pwd`
export FEEDCACHE_PID_DIR=/tmp

# python
export PYTHONPATH="${FEEDCACHE_HOME}/src"
# postgres client timezone
export PGTZ=UTC

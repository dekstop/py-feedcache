#!/bin/sh
#
# Variables used for setting up the application.
#

SCRIPT_DIR=`dirname $0`
APP_ROOT=`cd $SCRIPT_DIR; cd ..; pwd`

DBHOST=localhost
DBUSER=postgres
DBPASSWORD=
DBNAME=feedcache_test

SCHEMA_FILE=${APP_ROOT}/sql/schema_postgres.sql

# Commandline parameters can override defaults
if [ $# == 1 ]; then
	export DBNAME=$1
fi

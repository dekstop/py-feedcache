#!/bin/sh
#
# Variables used to run tests.
#

SCRIPT_DIR=`dirname $0`
APP_ROOT=`cd $SCRIPT_DIR; cd ..; pwd`
export PYTHONPATH="${APP_ROOT}/src"

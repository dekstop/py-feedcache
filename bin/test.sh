#!/bin/sh

bin=`dirname $0`
bin=`cd $bin; pwd`

. ${bin}/env.sh
. ${bin}/env-test.sh

TESTS_DIR="${FEEDCACHE_HOME}/tests"
MAIN="${TESTS_DIR}/main.py"

# we chdir so the test data can be found
pushd ${TESTS_DIR} > /dev/null
python $MAIN $@
popd > /dev/null

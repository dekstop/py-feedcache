#!/bin/sh

bin=`dirname $0`
bin=`cd $bin; pwd`

. ${bin}/env.sh

# if no args specified, show usage
if [ $# = 0 ]; then
  echo "Usage: feedcache COMMAND [parameters]"
  echo "where COMMAND is one of:"
  echo "  import      load feed URLs into import queue"
  echo "  update      import new feeds, update stale feeds"
  echo "  stop        stop all update workers"
  echo "  index       index new posts for search"
  echo "  search      keyword search"
  echo "Most commands print help when invoked with --help"
  exit 1
fi

# parameters
DSN="${DBENGINE}://${DBUSER}:${DBPASSWORD}@${DBHOST}/${DBNAME}"

# run
COMMAND=$1
shift

if [ "$COMMAND" = "import" ] ; then	
	$PYTHON "${FEEDCACHE_HOME}/src/app/batchimport.py" $DSN $@ || exit 1

elif [ "$COMMAND" = "update" ] ; then
	pid="${FEEDCACHE_PID_DIR}/feedcache-${FEEDCACHE_VERSION}-${COMMAND}.pid"
	mkdir -p "${FEEDCACHE_PID_DIR}"
	
	if [ -f $pid ]; then
		if kill -0 `cat $pid` > /dev/null 2>&1; then
			echo "${COMMAND} running as process `cat $pid`.  Stop it first."
			exit 1
		fi
	fi
	
	echo $$ > $pid
	$PYTHON "${FEEDCACHE_HOME}/src/app/update.py" $DSN $@ || exit 1
	rm $pid

elif [ "$COMMAND" = "stop" ] ; then
	$PYTHON "${FEEDCACHE_HOME}/src/app/stop.py" $DSN $@ || exit 1

elif [ "$COMMAND" = "index" ] ; then
	pid="${FEEDCACHE_PID_DIR}/feedcache-index-${FEEDCACHE_VERSION}-${COMMAND}.pid"
	mkdir -p "${FEEDCACHE_PID_DIR}"
	
	if [ -f $pid ]; then
		if kill -0 `cat $pid` > /dev/null 2>&1; then
			echo "${COMMAND} running as process `cat $pid`.  Stop it first."
			exit 1
		fi
	fi
	
	echo $$ > $pid
	$PYTHON "${FEEDCACHE_HOME}/src/solr/index.py" $DSN $@ || exit 1
	rm $pid

elif [ "$COMMAND" = "search" ] ; then
	$PYTHON "${FEEDCACHE_HOME}/src/examples/search.py" $DSN "$@" || exit 1

elif [ "$COMMAND" = "lastfm" ] ; then
	$PYTHON "${FEEDCACHE_HOME}/src/lastfm-api.py" $DSN "$@" || exit 1

elif [ "$COMMAND" = "vis1" ] ; then
	$PYTHON "${FEEDCACHE_HOME}/src/examples/vis1.py" $DSN "$@" || exit 1

else
	echo "Unknown command: ${COMMAND}"
fi

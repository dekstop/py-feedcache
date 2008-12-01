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
  echo "Most commands print help when invoked with --help"
  exit 1
fi

# parameters
DSN="${DBENGINE}://${DBUSER}:${DBPASSWORD}@${DBHOST}/${DBNAME}"

# run
COMMAND=$1
shift

if [ "$COMMAND" = "import" ] ; then	
	python "${FEEDCACHE_HOME}/src/batchimport.py" $DSN $@
elif [ "$COMMAND" = "update" ] ; then
	pid="${FEEDCACHE_PID_DIR}/feedcache-${COMMAND}.pid"
	mkdir -p "${FEEDCACHE_PID_DIR}"
	
	if [ -f $pid ]; then
		if kill -0 `cat $pid` > /dev/null 2>&1; then
			echo "${COMMAND} running as process `cat $pid`.  Stop it first."
			exit 1
		fi
	fi
	
	echo $$ > $pid
	python "${FEEDCACHE_HOME}/src/main.py" $DSN $@
	rm $pid
elif [ "$COMMAND" = "stop" ] ; then
	python "${FEEDCACHE_HOME}/src/stop.py" $DSN $@
else
	echo "Unknown command: ${COMMAND}"
fi

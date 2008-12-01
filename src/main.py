#!/usr/bin/env python
#
# main.py
#
# Batch update runner, imports feeds from the batchimports table and updates
# stale feeds. Loops until there are no more items to process.
#
# By default this spawns as many processes as there are CPUs, this can
# be overridden with a commandline parameter.
#
# martind 2008-12-01, 14:54:36
#

import datetime
import pp
import random
import sys
import time

# ========
# = conf =
# ========

DSN = 'postgres://postgres:@localhost/feedcache'

# from storm.tracer import debug
# debug(True, stream=sys.stdout)

LOCK_TIMEOUT = datetime.timedelta(hours=2)

UPDATE_TIMEOUT = datetime.timedelta(minutes=30)
RETRY_TIMEOUT = datetime.timedelta(hours=1)


# ===========
# = helpers =
# ===========

def create_and_run_worker(dsn, lock_timeout, update_timeout, retry_timeout):
	"""
	Instantiates and starts a worker, returns the result of Worker.run()
	"""
	from worker import Worker # required for pp
	worker = Worker(dsn, lock_timeout, update_timeout, retry_timeout)
	return worker.run()

# ========
# = main =
# ========

if __name__ == '__main__':
	
	ppservers=() # only spawn workers on localhost
	job_server = None
	num_processes = None
	
	if len(sys.argv)==1:
		# automatically determine number of workers based on CPU
		job_server = pp.Server(ppservers=ppservers)
		num_processes = job_server.get_ncpus()
	elif len(sys.argv)==2:
		# specified number of workers
		ncpus = int(sys.argv[1])
		job_server = pp.Server(ncpus=ncpus, ppservers=ppservers)
		num_processes = job_server.get_ncpus()
	else:
		print "[num_processes]"
		sys.exit(1)
	
	# =======
	# = run =
	# =======
	
	start_time = datetime.datetime.now()
	
	result = []

	if num_processes==1:
		# run in main thread
		result.append(create_and_run_worker(DSN, LOCK_TIMEOUT, UPDATE_TIMEOUT, RETRY_TIMEOUT))
	else:
		# sawn processes
		workers = []
		for i in range(num_processes):
			worker = job_server.submit(create_and_run_worker, (DSN, LOCK_TIMEOUT, UPDATE_TIMEOUT, RETRY_TIMEOUT), (), ())
			workers.append(worker)
			time.sleep(0.1 + random.random()) # to avoid lock contention

		for worker in workers:
			result.append(worker())
		
		job_server.print_stats()

	end_time = datetime.datetime.now()

	# ==========
	# = finish =
	# ==========
	
	print 'Done, elapsed time: %s' % (end_time-start_time,)

	for item in result:
		print '- %s' % (item,)

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
from optparse import OptionParser
import pp
import random
import sys
import time

import feedcache.util as util

# ========
# = conf =
# ========

LOCK_TIMEOUT = datetime.timedelta(minutes=131)

UPDATE_TIMEOUT = datetime.timedelta(minutes=97)
RETRY_TIMEOUT = datetime.timedelta(minutes=61)


# ===========
# = helpers =
# ===========

def create_and_run_worker(dsn, lock_timeout, update_timeout, retry_timeout, log_sql=False):
	"""
	Instantiates and starts a worker, returns the result of Worker.run()
	"""
	if log_sql:
		from storm.tracer import debug
		debug(True, stream=sys.stdout)
	from feedcache.worker import Worker # required for pp
	worker = Worker(dsn, lock_timeout, update_timeout, retry_timeout)
	return worker.run()

# ========
# = main =
# ========

if __name__ == '__main__':
	
	usage = 'usage: %prog [options] driver://user:password@host/database'
	parser = OptionParser(usage)
	
	parser.add_option('-s', '--log-sql', 
		dest='log_sql', 
		action='store_true', 
		help='enable logging of SQL statements')
	parser.add_option('-p', '--num-processes', 
		dest='num_processes', 
		type='int',
		help='number of worker processes')
	
	(options, args) = parser.parse_args()

	if len(args) != 1:
		parser.error('incorrect number of arguments')
	dsn = args[0]
	
	ppservers=() # only spawn workers on localhost
	job_server = None
	num_processes = None
	
	if options.num_processes==None:
		# automatically determine number of workers based on CPU
		job_server = pp.Server(ppservers=ppservers)
		num_processes = job_server.get_ncpus()
	else:
		# specified number of workers
		ncpus = options.num_processes
		job_server = pp.Server(ncpus=ncpus, ppservers=ppservers)
		num_processes = job_server.get_ncpus()
	
	# =======
	# = run =
	# =======
		
	start_time = util.now()
	result = []

	if num_processes==1:
		# run in main thread
		result.append(create_and_run_worker(dsn, LOCK_TIMEOUT, UPDATE_TIMEOUT, 
			RETRY_TIMEOUT, options.log_sql))
	else:
		# spawn processes
		print 'Spawning %d worker processes...' % num_processes
		workers = []
		for i in range(num_processes):
			worker = job_server.submit(create_and_run_worker, (dsn, LOCK_TIMEOUT, 
				UPDATE_TIMEOUT, RETRY_TIMEOUT, options.log_sql), (), ())
			workers.append(worker)
			time.sleep(0.1 + random.random()) # to avoid lock contention

		for worker in workers:
			result.append(worker())
		
		job_server.print_stats()

	end_time = util.now()

	# ==========
	# = finish =
	# ==========
	
	print 'Done, elapsed time: %s' % (end_time-start_time,)

	for item in result:
		print '- %s' % (item,)

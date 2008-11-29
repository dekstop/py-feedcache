#!/usr/bin/env python
#
# crawl.py
#
# ...
#
# martind 2008-11-16, 15:30:05
#

import datetime
import os
import pp
import psycopg2.extensions
import random
import sys
import time

import feedparser
import storm.locals

from feedcache.models.feeds import Batchimport, Feed
from feedcache.models.semaphores import Semaphore
from feedcache.models.messages import BatchimportMessage, FeedMessage
import feedcache.exceptions


# ========
# = conf =
# ========

DSN = 'postgres://postgres:@localhost/feedcache'

# from storm.tracer import debug
# debug(True, stream=sys.stdout)

stdout = sys.stdout
stderr = sys.stdout

# ===========
# = helpers =
# ===========

def load_batchimport_file(DSN, file):
	db = storm.database.create_database(DSN)
	store = storm.store.Store(db)
	
	FILE = open('crawltest.txt', 'r')
	feedurls = map(unicode, FILE.read().split("\n"))
	FILE.close()

	for url in feedurls:
		Batchimport.CreateIfMissing(store, url)

	store.close()

def spawn_worker(DSN):
	from benchmark_processes_worker import Worker
	worker = Worker(DSN)
	return worker.run()

# ========
# = main =
# ========

if __name__ == '__main__':
	
	if len(sys.argv)!=2:
		print "<num_processes>"
		sys.exit(1)
	
	num_processes = int(sys.argv[1])
	ncpus = num_processes
	ppservers=()
	job_server = pp.Server(ncpus, ppservers=ppservers)
	#job_server = pp.Server(ppservers=ppservers)

	# setup
	load_batchimport_file(DSN, 'crawltest.txt')

	# =======
	# = run =
	# =======
	
	start_time = datetime.datetime.now()
	
	workers = []
	num_retries = 0

	try:
		for i in range(num_processes):
			worker = job_server.submit(spawn_worker, (DSN,), (), ())
			workers.append(worker)
			time.sleep(0.1 + random.random()) # to avoid lock contention

		for worker in workers:
			num_retries += worker()
	except (KeyboardInterrupt, SystemExit):
		# ask all workers to shut down
		print "Asking workers to shut down..."
		db = storm.database.create_database(DSN)
		store = storm.store.Store(db)
		store.execute(storm.expr.Update({Semaphore.shutdown_requested: True}, True, Semaphore))
		store.commit()
		store.close()
		job_server.wait()

	end_time = datetime.datetime.now()

	job_server.print_stats()
	
	# ===========
	# = measure =
	# ===========
	
	db = storm.database.create_database(DSN)
	store = storm.store.Store(db)
	num_messages = store.execute('select count(*) from messages').get_one()[0]
	store.close()
	
	# create table stats(id serial primary key, type text, start_time timestamp, end_time timestamp, num_retries int, num_messages int);
	db = storm.database.create_database('postgres://postgres:@localhost/metrics')
	store = storm.store.Store(db)
	
	# create table stats(id serial primary key, type text, start_time timestamp, end_time timestamp, num_retries int, num_messages int);
	# create view stats_summary as select type, count(*), min(end_time-start_time) as min_time, max(end_time-start_time) as max_time, avg(end_time-start_time) as avg_time, round(cast(stddev(extract(epoch from (end_time-start_time))) as numeric), 2) as sd_time, min(num_retries) as min_retries, max(num_retries) as max_retries, round(avg(num_retries), 2) as avg_retries, round(stddev(num_retries), 2) as sd_retries, min(num_messages) as min_messages, max(num_messages) as max_messages, round(avg(num_messages), 2) as avg_messages, round(stddev(num_messages), 2) as sd_messages from stats group by type order by min(id);
	store.execute(
		"insert into stats(type, start_time, end_time, num_retries, num_messages) values ('%s', '%s', '%s', %d, %d)" %
		(
			("processes: %d" % num_processes),
			start_time.isoformat(),
			end_time.isoformat(),
			num_retries,
			num_messages
		))
	store.commit()
	store.close()

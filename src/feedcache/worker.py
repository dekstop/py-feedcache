#!/usr/bin/env python
#
# worker.py
#
# Threadsafe worker class that imports and updates feeds.
#
# martind 2008-12-01, 14:54:36
#

#from collections import defaultdict
import datetime
import os
import pp
import random
import sys
import time

import storm.locals

import feedcache.exceptions
from feedcache.models.semaphores import Semaphore
from feedcache.models.feeds import Batchimport, Feed
from feedcache.models.messages import BatchimportMessage, FeedMessage
from feedcache.queues import BatchimportQueue, FeedQueue

__all__ = [
	'Worker'
]

NUM_ITEMS_PER_LOCK = 1

class Worker(object):
	"""
	Updates items (batchimports, feeds) until there are no more left to process.
	Instantiates a BatchimportQueue and FeedQueue to fetch and lock items.
	
	Automatically marks items a inactive after multiple failures.
	"""
	
	def __init__(self, dsn, 
		lock_timeout=datetime.timedelta(hours=6), 
		update_timeout=datetime.timedelta(minutes=30),
		retry_timeout=datetime.timedelta(hours=1),
		max_failures=3):
		"""
		Parameters:
		dsn: 
			a DSN as used by storm.database.create_database(DSN)
		lock_timeout: 
			a datetime.timedelta, time until a lock expires (which should only 
			happen when a worker dies.)
		update_timeout: 
			a datetime.timedelta, minimum delay between feed updates
		retry_timeout: 
			a datetime.timedelta, delay before retrying a failed import/update
		max_failures:
			number of failures before the item gets marked as inactive
		"""
		self.dsn = dsn
		self.lock_timeout = lock_timeout
		self.update_timeout = update_timeout
		self.retry_timeout = retry_timeout
		self.max_failures = max_failures
		self.semaphore = None
		self.stats = dict() #defaultdict(lambda: 0)
	
	def log(self, message):
		"""
		Logger for debug messages.
		"""
		print "%s %s %s" % (
			self.semaphore and self.semaphore.id, # self.semaphore may be None
			datetime.datetime.now().isoformat(), 
			message)
	
	def inc(self, key, n=1):
		"""
		Helper to increment entries in the 'stats' dict. 
		We can't use a defaultdict because pp apparently  can't pickle those,
		hence this function to reduce code verbosity.
		"""
		if self.stats.has_key(key):
			self.stats[key] += n
		else:
			self.stats[key] = n
	
	def add(self, store, batchimport):
		self.log('import: %s' % batchimport.url)
		self.inc('num_batchimport_adds')
		try:
			return batchimport.import_feed(store)
		except:
			if batchimport.fail_count > self.max_failures:
				batchimport.active = False
				store.commit()
			e = sys.exc_info()[1]
			self.log(e)
			self.inc('num_exceptions:%s' % e.__class__.__name__)
			return None

	def update(self, store, feed):
		self.log('update: %s' % feed.url)
		self.inc('num_feed_updates')
		try:
			feed.update(store)
			return feed
		except:
			if feed.fail_count > self.max_failures:
				feed.active = False
				store.commit()
			e = sys.exc_info()[1]
			self.log(e)
			self.inc('num_exceptions:%s' % e.__class__.__name__)
			return None

	def run(self):
		"""
		Runs until all batchimports have been processed and all stale feeds updated.
		
		Returns a dictionary of diagnostic variables.
		"""
		db = storm.database.create_database(self.dsn)
		store = storm.store.Store(db)

		self.semaphore = Semaphore()
		store.add(self.semaphore)
		store.commit()
		
		batchimport_queue = BatchimportQueue(self.semaphore, self.lock_timeout, self.update_timeout, self.retry_timeout)
		feed_queue = FeedQueue(self.semaphore, self.lock_timeout, self.update_timeout, self.retry_timeout)
		
		while self.semaphore.shutdown_requested==False:
			keep_running = False

			for batchimport in batchimport_queue.next(store, NUM_ITEMS_PER_LOCK):
				self.add(store, batchimport)
				keep_running = True

			for feed in feed_queue.next(store, NUM_ITEMS_PER_LOCK):
				self.update(store, feed)
				keep_running = True

			if keep_running==False:
				break
			
			store.flush()
		
		if self.semaphore.shutdown_requested==True:
			self.log("Shutdown requested")
		
		store.remove(self.semaphore)
		store.commit()
		
		store.close()
		
		self.stats['batchimport_queue'] = batchimport_queue.stats
		self.stats['feed_queue'] = feed_queue.stats
		
		return self.stats

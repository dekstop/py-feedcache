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
import psycopg2.extensions
import random
import sys
from threading import Thread
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

LOCK_TIMEOUT = datetime.timedelta(hours=2)

RETRY_TIMEOUT = datetime.timedelta(hours=1)
UPDATE_TIMEOUT = datetime.timedelta(minutes=30)

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


# ===========
# = classes =
# ===========

class Worker(object):
	
	def __init__(self, DSN):
		self.DSN = DSN
		self.semaphore = Semaphore()
	
	def log(self, message):
		print str(self.semaphore), message
	
	def _expr_importable_batchimports(self, store, semaphore, cutoff_time):
		"""
		Storm query expression: find Batchimport entries that are ready for importing.
		"""
		return storm.expr.And(
			# added before cutoff_time
			Batchimport.date_added<cutoff_time,
			# AND not imported yet
			Batchimport.imported==False, 
			# AND:
			storm.expr.Or(
				# hasn't failed
				Batchimport.fail_count == 0,
				# OR last request has failed, but happened before RETRY_TIMEOUT
				storm.expr.And(
					Batchimport.fail_count > 0,
					Batchimport.date_last_fetched < (datetime.datetime.now() - RETRY_TIMEOUT),
				)
			),
			# AND:
			storm.expr.Or(
				# is not locked
				Batchimport.semaphore == None,
				# OR is locked, but lock has timed out
				Batchimport.date_locked < (datetime.datetime.now() - LOCK_TIMEOUT)
			)
		)
	
	def acquire_batchimports(self, store, semaphore, cutoff_time, retries=3):
		"""
		Locks and returns a random non-imported Batchimport that is ready for importing:
		it was added before cutoff_time, if the last attempt failed it was last fetched 
		before cutoff_time - RETRY_TIMEOUT, and it is not locked.
		
		The Batchimport instance must be unlocked after processing.
		May return None if it failed to acquire a lock several times.
		"""
		try:
			self.log('acquiring lock...')
			store.execute(storm.expr.Update({
					Batchimport.semaphore_id: semaphore.id, 
					Batchimport.date_locked: datetime.datetime.now()
				}, 
				Batchimport.id.is_in(
					storm.expr.Select(
						[Batchimport.id],
						self._expr_importable_batchimports(store, semaphore, cutoff_time),
						Batchimport,
						limit=1
					)
				),
				Batchimport))
			store.commit()
			
			items = store.find(Batchimport, Batchimport.semaphore == semaphore)
			for batchimport in items:
					self.log('locked batchimport_id %d' % batchimport.id)
			return items
		except psycopg2.extensions.TransactionRollbackError, e:
			# http://www.postgresql.org/docs/8.1/static/transaction-iso.html
			# https://bugs.launchpad.net/storm/+bug/149335
			# -> retry
			store.rollback()
			self.log('%s, retrying...' % str(e))
			if retries>0:
				self.acquire_batchimports(store, semaphore, cutoff_time, retries-1)
			return None
		except storm.exceptions.IntegrityError, e:
			# Violated unique constraint: another worker has already acquired the lock.
			# If this happens we failed at making Storm do an atomic INSERT .. SELECT
			raise	
	
	def release_batchimport(self, store, semaphore, batchimport):
		self.log('unlocking batchimport_id %d' % batchimport.id)
		store.execute(storm.expr.Update({
				Batchimport.semaphore_id: None, 
				Batchimport.date_locked: None
			}, 
			storm.expr.And(
				Batchimport.id == batchimport.id,
				Batchimport.semaphore_id == semaphore.id
			), 
			Batchimport))
		store.commit()
	
	def add(self, store, batchimport):
		self.log('import: %s' % batchimport.url)
		try:
			return batchimport.import_feed(store)
		except:
			e = sys.exc_info()[1]
			self.log(e)
			return None

	def update(self, store, feed):
		self.log('update: %s' % feed.url)
		try:
			feed.update(store)
			return feed
		except:
			e = sys.exc_info()[1]
			self.log(e)
			return None

	def run(self):
		"""
		Runs until all batchimports have been processed and all stale
		feeds updated.
		"""
		db = storm.database.create_database(DSN)
		store = storm.store.Store(db)

		store.add(self.semaphore)
		store.commit()
		
		# ignore entries that get added during this session:
		cutoff_time = datetime.datetime.now()
		
		while self.semaphore.shutdown_requested==False:
			keep_running = False

			batchimports = self.acquire_batchimports(store, self.semaphore, cutoff_time)
			if batchimports and batchimports.count()>0:
				for batchimport in batchimports:
					self.add(store, batchimport)
					self.release_batchimport(store, self.semaphore, batchimport)
				keep_running = True

			# feed = self.acquire_feed(store, self.semaphore, cutoff_time)
			# if feed:
			# 	self.update(store, feed)
			# 	keep_running = True
					
			if keep_running==False:
				break
		
		store.remove(self.semaphore)
		store.commit()
		
		store.close()

# ========
# = main =
# ========

if __name__ == '__main__':
	# setup
	load_batchimport_file(DSN, 'crawltest.txt')
	
	db = storm.database.create_database(DSN)
	store = storm.store.Store(db)
	
	for tablename in ['semaphores']:
		store.execute('truncate ' + tablename)
	for tablename in ['feeds', 'batchimports']:
		store.execute('update ' + tablename + ' set semaphore_id=null, date_locked=null')
	store.commit()
	
	# run
	# from storm.tracer import debug
	# debug(True, stream=sys.stdout)

	# worker = Worker(DSN)
	# worker.run()
	
	workers = []

	for i in range(9):
		worker = Worker(DSN)
		t = Thread(target=worker.run)
		workers.append(t)
		time.sleep(0.1 + random.random()) # to avoid lock contention
		t.start()
	
	for worker in workers:
		worker.join()
	
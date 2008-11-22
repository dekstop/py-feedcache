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
import sys

import feedparser
import storm.locals

from feedcache.models.feeds import Batchimport, Feed
from feedcache.models.messages import BatchimportMessage, FeedMessage
import feedcache.exceptions

# ========
# = conf =
# ========

DSN = 'postgres://postgres:@localhost/feedcache'

MIN_TIME_BETWEEN_RETRIES = datetime.timedelta(minutes=0) # datetime.timedelta(hours=1)
MIN_TIME_BETWEEN_UPDATES = datetime.timedelta(minutes=30)

# from storm.tracer import debug
# debug(True, stream=sys.stdout)

stdout = sys.stdout
stderr = sys.stdout

# ===========
# = classes =
# ===========

class Crawler(object):
	
	def __init__(self):
		# single worker
		self.worker = CrawlerWorker()
	
	def run(self, store):
		"""
		Runs until all batchimports have been processed and all stale
		feeds updated.
		"""
		# ignore entries that get added during this session:
		cutoff_time = datetime.datetime.now()
		
		keep_running = True
		while keep_running:
			keep_running = False

			batchimport = Batchimport.GetOne(store, 
				cutoff_time, 
				cutoff_time - MIN_TIME_BETWEEN_RETRIES)
			if batchimport:
				print '' % batchimport.feed_url
				self.worker.add(store, batchimport)
				keep_running = True

			feed = Feed.GetOneForUpdate(store, 
				cutoff_time - MIN_TIME_BETWEEN_UPDATES,
				cutoff_time - MIN_TIME_BETWEEN_RETRIES)
			if feed:
				print feed
				self.worker.update(store, feed)
				keep_running = True

class CrawlerWorker(object):
	
	def add(self, store, batchimport):
		try:
			batchimport.import_feed(store)
		except:
			e = sys.exc_info()[1]			
			#store.rollback()
			#batchimport.fail_count += 1
			b = BatchimportMessage.FromException(store, batchimport, e)
			print b
			store.add(b)
			store.commit()

	def update(self, store, feed):
		try:
			feed.update(store)
		except:
			e = sys.exc_info()[0]
			#store.rollback()
			#feed.fail_count += 1
			f = FeedMessage.FromException(store, feed, e)
			print f
			store.add(f)
			store.commit()

# ========
# = main =
# ========

if __name__ == "__main__":
	# setup
	db = storm.database.create_database(DSN)
	store = storm.store.Store(db)
	
	FILE = open('crawltest.txt', 'r')
	feedurls = map(unicode, FILE.read().split("\n"))
	FILE.close()

	for url in feedurls:
		Batchimport.CreateIfMissing(store, url)

	# run
	crawler = Crawler()
	crawler.run(store)

	store.close()

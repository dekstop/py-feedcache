#!/usr/bin/env python
#
# crawl.py
#
# Traverses local copies of feeds and does stuff.
#
# martind 2008-11-01, 16:04:12
#

import os
import sys

import feedparser
import storm.locals

from feedcache.models.feeds import Batchimport, Feed, Entry
import feedcache.exceptions

# helpers
def print_exception(e):
	import traceback
	tb = traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2])
	msg = tb.pop()
	stderr.write("%r : %s\n%s" % (type(e), msg, "\n".join(tb)))
	if (hasattr(e, 'document')):
		stderr.write("====\n")
		stderr.write(str(e.document))
		stderr.write("\n")
	stderr.write("==========\n")
	

# conf
feeds_dir = u'/Users/mongo/Documents/code/_aggregator/python/data/feeds'

# setup
db = storm.database.create_database("postgres://postgres:@localhost/feedcache")
store = storm.store.Store(db)

from storm.tracer import debug
debug(True, stream=sys.stdout)

stdout = sys.stdout
stderr = sys.stdout

# main

# store.execute('truncate feeds')
# store.execute('truncate entries')
# store.execute('truncate authors')
# store.execute('truncate feeds_authors')
# store.execute('truncate entries_authors')

feedurls = []
# for root, dirs, files in os.walk(feeds_dir):
# 	for file in [f for f in files if False==os.path.isdir(f)]:
# 		feedurl = root + '/' + file
# 		feedurls.append(feedurl)

# FILE = open('crawltest.txt', 'r')
# feedurls += map(unicode, FILE.read().split("\n"))
# FILE.close()

feedurls.append(u'/Users/mongo/Documents/code/_aggregator/python/data/feeds/river/software/www.cascading.org_atom.xml')
#  feedurls.append(u'/Users/mongo/Documents/code/_aggregator/python/src/test/data/dekstop.de_weblog_index.xml')
#feedurls.append(u'/Users/mongo/Documents/code/_aggregator/python/src/test/data/empty.xml')

for feedurl in feedurls:
	try:
		feed = Feed.FindByUrl(store, feedurl)
		if (feed==None):
			print 'adding: ' + feedurl
			feed = Feed.Load(store, feedurl)
		else:
			print 'updating: ' + feedurl
			feed.update(store)
		store.commit()
	except storm.exceptions.IntegrityError, e:
		# violated unique constraint
		print_exception(e)
		store.rollback()
	except feedcache.exceptions.FeedFetchError, e:
		print_exception(e)
		store.rollback()
	except feedcache.exceptions.FeedParseError, e:
		print_exception(e)
		store.rollback()
		
store.close()

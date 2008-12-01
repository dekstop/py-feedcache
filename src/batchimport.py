#!/usr/bin/env python
#
# batchimport.py
#
# Loads a text file of feed URLs into the batchimports table.
#
# martind 2008-12-01, 19:01:41
#

import sys

import storm.locals

from feedcache.models.feeds import Batchimport

# ========
# = conf =
# ========

DSN = 'postgres://postgres:@localhost/feedcache'

# ===========
# = helpers =
# ===========

def load_batchimport_file(store, filename):
	
	FILE = open(filename, 'r')
	feedurls = filter(lambda fn: len(fn)>0, map(unicode, FILE.read().split("\n")))
	FILE.close()

	for url in feedurls:
		Batchimport.CreateIfMissing(store, url)

# ========
# = main =
# ========

if __name__ == '__main__':
	
	if len(sys.argv) == 1:
		print '<feed_urls.txt>'
		sys.exit(1)
	
	db = storm.database.create_database(DSN)
	store = storm.store.Store(db)

	for filename in sys.argv[1:]:
		load_batchimport_file(store, filename)

	store.close()

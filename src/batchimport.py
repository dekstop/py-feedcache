#!/usr/bin/env python
#
# batchimport.py
#
# Loads a text file of feed URLs into the batchimports table.
#
# martind 2008-12-01, 19:01:41
#

from optparse import OptionParser
import sys

import storm.locals

from feedcache.models.feeds import Batchimport

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
	
	usage = 'usage: %prog driver://user:password@host/database <feed_urls.txt>'
	parser = OptionParser(usage)
	
	(options, args) = parser.parse_args()

	if len(args) <= 1:
		parser.error('incorrect number of arguments')
	dsn = args[0]

	db = storm.database.create_database(dsn)
	store = storm.store.Store(db)

	for filename in args[1:]:
		load_batchimport_file(store, filename)

	store.close()

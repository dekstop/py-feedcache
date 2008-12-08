#!/usr/bin/env python
#
# search.py
#
# ...
#
# martind 2008-12-08, 19:55:50
#

from optparse import OptionParser
import sys

import storm.locals

from feedcache.models.feeds import Entry
from feedcache.search import Searcher
import feedcache.util as util

# ===========
# = helpers =
# ===========

def search(store, terms):
	return Searcher.Entries(store, 
		terms,
	)

# ========
# = main =
# ========

if __name__ == '__main__':
	
	usage = 'usage: %prog driver://user:password@host/database <term1> <term2> ...'
	parser = OptionParser(usage)
	
	(options, args) = parser.parse_args()

	if len(args) <= 1:
		parser.error('incorrect number of arguments')
	dsn = args[0]
	terms = args[1:]

	db = storm.database.create_database(dsn)
	store = storm.store.Store(db)
	
	for entry in search(store, terms):
		print entry.link, entry.date_published
		print util.excerpt(entry.title, 100)
		print util.excerpt(entry.content or entry.summary, 100)
		print

	store.close()


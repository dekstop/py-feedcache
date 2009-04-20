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
from examples.searcher import Searcher
import feedcache.util as util

# ===========
# = helpers =
# ===========

def encode(str):
	if str==None:
		return None
	return str.encode('utf8')

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
	
	parser.add_option('-l', '--limit', 
		dest='limit', 
		action='store', 
		help='limit number of results')
	parser.add_option('-s', '--log-sql', 
		dest='log_sql', 
		action='store_true', 
		help='enable logging of SQL statements')

	(options, args) = parser.parse_args()

	if len(args) <= 1:
		parser.error('incorrect number of arguments')
	dsn = args[0]
	terms = args[1:]

	db = storm.database.create_database(dsn)
	store = storm.store.Store(db)
	
	limit = None
	if options.limit:
		limit = int(options.limit)
	
	if options.log_sql:
		from storm.tracer import debug
		debug(True, stream=sys.stdout)
	
	for entry in search(store, terms)[:limit]:
		print encode(entry.link), entry.date_published
		print encode(entry.title)
		print encode(util.excerpt(entry.content or entry.summary, 2000))
		print '==============='

	store.close()


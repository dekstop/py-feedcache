#!/usr/bin/env python
#
# stop.py
#
# ...
#
# martind 2008-12-01, 22:55:52
#

from optparse import OptionParser
import sys

import storm.locals

from feedcache.models.semaphores import Semaphore

# ========
# = main =
# ========

if __name__ == '__main__':
	
	usage = 'usage: %prog driver://user:password@host/database <feed_urls.txt>'
	parser = OptionParser(usage)
	
	(options, args) = parser.parse_args()

	if len(args) != 1:
		parser.error('incorrect number of arguments')
	dsn = args[0]

	db = storm.database.create_database(dsn)
	store = storm.store.Store(db)

	store.execute(storm.expr.Update({Semaphore.shutdown_requested: True}))
	store.commit()

	store.close()

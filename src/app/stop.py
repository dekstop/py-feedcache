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
	
	parser = OptionParser(
		usage='usage: %prog driver://user:password@host/database', 
		description='Exit status is 1 if no workers are currently market as active; 0 otherwise.')
	(options, args) = parser.parse_args()

	if len(args) != 1:
		parser.error('incorrect number of arguments')
	dsn = args[0]

	db = storm.database.create_database(dsn)
	store = storm.store.Store(db)
	
	num = store.find(Semaphore, Semaphore.shutdown_requested==False).count()
	if num==0:
		print 'No active workers found.'
		store.close()
		exit(1)

	print 'Asking %d workers to stop...' % num

	store.execute(storm.expr.Update({Semaphore.shutdown_requested: True}))
	store.commit()

	store.close()

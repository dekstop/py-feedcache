#!/usr/bin/env python
#
# batchimport.py
#
# Loads a text file of feed URLs into the batchimports table,
# optionally joins a list of feeds with a user account.
#
# martind 2008-12-01, 19:01:41
#

from optparse import OptionParser
import os.path
import sys

import storm.locals

from feedcache.models.feeds import Batchimport, Feed
from feedcache.models.users import User

# ===========
# = helpers =
# ===========

def load_urls_from_file(filename):
	FILE = open(filename, 'r')
	feedurls = filter(lambda fn: len(fn)>0, map(unicode, FILE.read().split("\n")))
	FILE.close()

	return feedurls

def load_batchimports(store, feedurls, user):
	for url in feedurls:
		Batchimport.CreateIfMissing(store, url, user)

# ========
# = main =
# ========

if __name__ == '__main__':
	
	usage = 'usage: %prog driver://user:password@host/database <feed_urls.txt> | <feed URL>'
	parser = OptionParser(usage)
	
	parser.add_option('-u', '--user', 
		dest='user', 
		type='string',
		help='feedcache user in whose name to import')
	
	(options, args) = parser.parse_args()
	username = options.user

	if len(args) <= 1:
		parser.error('incorrect number of arguments')
	dsn = args[0]

	db = storm.database.create_database(dsn)
	store = storm.store.Store(db)
	
	feedurls = []
	
	for n in args[1:]:
		if os.path.exists(n) and os.path.isfile(n):
			feedurls += load_urls_from_file(n)
		else:
			feedurls += [unicode(n)]
	
	user = None
	if username!=None:
		user = User.FindByName(store, unicode(username))
		if user==None:
			parser.error('Unknown username %s' % (username))
	
	for filename in args[1:]:
		load_batchimports(store, feedurls, user)

	store.close()

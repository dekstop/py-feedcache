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
import sys

import storm.locals

from feedcache.models.feeds import Batchimport, Feed
from feedcache.models.users import User

# ===========
# = helpers =
# ===========

def load_batchimports(store, filename):
	
	FILE = open(filename, 'r')
	feedurls = filter(lambda fn: len(fn)>0, map(unicode, FILE.read().split("\n")))
	FILE.close()

	for url in feedurls:
		Batchimport.CreateIfMissing(store, url)

def load_feeds(store, filename, user):
	
	FILE = open(filename, 'r')
	feedurls = filter(lambda fn: len(fn)>0, map(unicode, FILE.read().split("\n")))
	FILE.close()

	i = 0

	for url in feedurls:
		try:
			f = Feed.Load(store, url)
			if (!user.feeds.contains(f)):
				user.feeds.add(f)
				store.commit()
			i += 1
		except:
			store.rollback()
			et = sys.exc_info()[0]
			e = sys.exc_info()[1]
			print et, e
	print "Imported %d feeds" % i

# ========
# = main =
# ========

if __name__ == '__main__':
	
	usage = 'usage: %prog driver://user:password@host/database <feed_urls.txt>'
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
	
	user = None
	if username!=None:
		user = User.FindByName(store, unicode(username))
		if user==None:
			parser.error('Unknown username %s' % (username))
		for filename in args[1:]:
			load_feeds(store, filename, user)
	else:
		for filename in args[1:]:
			load_batchimports(store, filename)

	store.close()

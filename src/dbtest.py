#!/usr/bin/env python
#
# dbtest.py
#
# ...
#
# martind 2008-10-27, 23:11:05
#

import sys

import storm.locals

# from storm.locals import *
# from storm.exceptions import *

from feedcache.models.feeds import Batchimport, Feed, Entry

#import storm

db = storm.database.create_database("postgres://postgres:@localhost/feedcache")
store = storm.store.Store(db)

# adding new item; handling a constraint violation
try:
	b = Batchimport(u'http://dsaasdgfawsdg.dsf/dsfadf')
	store.add(b)
	store.flush()
except storm.exceptions.IntegrityError, e:
	# constraint violation
	print e.message
	store.rollback()

# finding items
result = Batchimport.FindByUrl(store, u'http://dsaasdgfawsdg.dsf/dsfadf')
print result.feed_url, result.imported

result = Batchimport.Queue(store)
print [item.feed_url for item in result]

result = Feed.FindByUrl(store, u'http://dsaasdgfawsdg.dsf/dsfadf')
print result

# cleanup
store.close

#!/usr/bin/env python
#
# modeltest.py
#
# ...
#
# martind 2008-10-27, 23:11:05
#

import sys

import feedparser
import storm.locals

from feedcache.models.feeds import Batchimport, Feed, Entry
import feedcache.exceptions

# helpers

def encode(str):
	if str==None:
		return None
	else:
		return str.encode('utf-8')


# conf
feedparser.USER_AGENT = feedparser.USER_AGENT + ' feedcache'

# setup
db = storm.database.create_database("postgres://postgres:@localhost/test")
store = storm.store.Store(db)

# main
feedurl = u'/Users/mongo/Documents/code/_aggregator/python/data/feeds/contexts/myslef/dekstop.de_weblog_index.xml_dks'
feed = Feed.FindByUrl(store, feedurl)
if (feed==None):
	feed = Feed.LoadFromUrl(feedurl)
	store.add(feed)
	store.flush()

print encode(feed.title)
print encode(feed.description)
print encode(feed.link)
print feed.date_added
print feed.date_last_fetched
print feed.date_updated
for entry in feed.entries:
	print encode(entry.title)
	print encode(entry.link)
	print encode(entry.content)
	print encode(entry.summary)
	print entry.date_published
	print entry.date_updated
	
# cleanup
store.close

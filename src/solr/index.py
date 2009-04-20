#!/usr/bin/env python
#
# index.py
#
# ...
#
# martind 2009-04-19, 14:20:46
#

import datetime
from optparse import OptionParser
import sys
import time

import storm.locals
from pysolr import Solr

from feedcache.models.conf import Conf
from feedcache.models.feeds import Entry
import feedcache.util as util

# ========
# = conf =
# ========

solrUrl = u'http://127.0.0.1:8080/solr/'
CONF_SOLR_URL = u'solr.url'

entriesPerPost = 10 # to batch-submit entries
CONF_ENTRIES_PER_POST = u'solr.index.entriesPerPost'

transactionSize = 100 # number of entries posted between commits
CONF_TRANSACTION_SIZE = u'solr.index.transactionSize'

lastIndexDateTime = datetime.datetime(2009, 01, 01, 12, 00, 0000)
CONF_LAST_INDEX_DATETIME = u'solr.index.lastIndexDateTime'

# ===========
# = helpers =
# ===========

def log(message):
	"""
	Logger for debug messages.
	"""
	print "%s %s" % (
		util.now().isoformat(), 
		message)

def createdoc(entry):
	"""Formats a feed entry as Solr document hash"""
	return {
		'id' : entry.id,
		
		'feed_id' : entry.feed.id,
		'feed_title' : entry.feed.title,
		'feed_description' : entry.feed.description,
		'feed_link' : entry.feed.link,
		
		'date_added' : entry.date_added,
		'date_published' : entry.date_published,
		
		'title' : entry.title,
		'content' : entry.content,
		'summary' : entry.summary,
		'link' : entry.link,
		
		'author' : get_authors(entry),
		
		'category' : get_categories(entry),
		'category_scheme' : get_category_schemes(entry),
		
		'enclosure_url' : get_enclosure_urls(entry),
		'enclosure_mimetype' : get_enclosure_mimetypes(entry),
		
		#'tag' : get_tags(entry)
	}

def get_authors(entry):
	return [a.name for a in entry.authors]

def get_categories(entry):
	return [c.term for c in entry.categories]

def get_category_schemes(entry):
	return [c.scheme for c in entry.categories]

def get_enclosure_urls(entry):
	return [e.url for e in entry.enclosures]

def get_enclosure_mimetypes(entry):
	return [e.type for e in entry.enclosures]

# ========
# = main =
# ========

if __name__ == '__main__':
	
	usage = 'usage: %prog [options] driver://user:password@host/database'
	parser = OptionParser(usage)
	
	parser.add_option('-s', '--log-sql', 
		dest='log_sql', 
		action='store_true', 
		help='enable logging of SQL statements')

	(options, args) = parser.parse_args()

	if len(args) != 1:
		parser.error('incorrect number of arguments')
	dsn = args[0]
	
	db = storm.database.create_database(dsn)
	store = storm.store.Store(db)
	
	if options.log_sql:
		from storm.tracer import debug
		debug(True, stream=sys.stdout)
		
	solrUrl = Conf.Get(store, CONF_SOLR_URL, solrUrl)
	entriesPerPost = Conf.GetInt(store, CONF_ENTRIES_PER_POST, entriesPerPost)
	transactionSize = Conf.GetInt(store, CONF_TRANSACTION_SIZE, transactionSize)
	lastIndexDateTime = Conf.GetDateTime(store, CONF_LAST_INDEX_DATETIME, lastIndexDateTime)
	
	solr = Solr(str(solrUrl))
	
	# =======
	# = run =
	# =======
		
	start_time = util.now()
	
	entries = store.find(
		Entry,
		storm.expr.Or(
			Entry.date_added >= lastIndexDateTime,
			Entry.date_modified >= lastIndexDateTime
		)
	)
	
	docs = []
	num = 0
	for entry in entries:
		log("Adding Entry with id %d" % entry.id)
		docs.append(createdoc(entry))
		num += 1
		if num % entriesPerPost == 0:
			solr.add(docs, False)
			docs = []
		if num % transactionSize == 0:
			log("Committing...")
			solr.commit()
	
	if len(docs) > 0:
		solr.add(docs)
	
	solr.commit()

	end_time = util.now()
	
	# Always do this last. 
	# After a program crash we'd rather index stuff twice than not at all.
	Conf.SetDateTime(store, CONF_LAST_INDEX_DATETIME, start_time)
	store.commit()

	# ==========
	# = finish =
	# ==========
	
	store.close()
	
	print 'Done, elapsed time: %s' % (end_time-start_time,)

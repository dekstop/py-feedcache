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
import re
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

entriesPerPost = 20 # to batch-submit entries
CONF_ENTRIES_PER_POST = u'solr.index.entriesPerPost'

transactionSize = 1000 # number of entries posted between commits
CONF_TRANSACTION_SIZE = u'solr.index.transactionSize'

NEVER = datetime.datetime(2009, 01, 01, 12, 00, 0000)

lastIndexDateTime = NEVER
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

def load_int_file(filename):
	"""
	Loads a list of integers fron a newline-separated text file.
	"""
	result = []
	file = open(filename)
	while 1:
		line = file.readline()
		if not line:
			break
		line = line.strip()
		if len(line) > 0:
			result += [int(line)]
	return result


def build_nonxml_chars_re():
	"""From http://boodebr.org/main/python/all-about-python-and-unicode"""
	expr = u'([\u0000-\u0008\u000b-\u000c\u000e-\u001f\ufffe-\uffff])'
	expr += u"|"
	expr += u'([%s-%s][^%s-%s])|([^%s-%s][%s-%s])|([%s-%s]$)|(^[%s-%s])' % \
		(unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff),
		unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff),
		unichr(0xd800),unichr(0xdbff),unichr(0xdc00),unichr(0xdfff))
	return re.compile(expr)

nonxml_chars_re = build_nonxml_chars_re()

def strip_invalid_chars(string):
	"""
	pysolr doesn't seem to remove invalid XML characters, so we have to do it ourselves.
	This prevents a 'com.ctc.wstx.exc.WstxUnexpectedCharException: Illegal character' on the Solr
	server. Cf http://www.w3.org/TR/REC-xml/#charsets
	
	This also makes sure we're not sending "None" strings -- evidently pysolr sends these for null
	values, so I found it in the top terms list...
	"""
	if string==None:
		return u''
	return nonxml_chars_re.sub(u' ', string)

def createdoc(entry):
	"""Formats a feed entry as Solr document hash"""
	return {
		'id' : entry.id,
		
		'feed_id' : entry.feed.id,
		'feed_id_facet' : entry.feed.id,
		'feed_title' : strip_invalid_chars(entry.feed.title),
		'feed_description' : strip_invalid_chars(entry.feed.description),
		'feed_link' : strip_invalid_chars(entry.feed.link),
		
		'date' : entry.date,
		'date_added' : entry.date_added,
		'date_published' : entry.date_published,
		
		'title' : strip_invalid_chars(entry.title),
		'content' : strip_invalid_chars(entry.content),
		'summary' : strip_invalid_chars(entry.summary),
		'link' : strip_invalid_chars(entry.link),
		
		'author' : get_authors(entry),
		
		'category' : get_categories(entry),
		'category_scheme' : get_category_schemes(entry),
		
		'enclosure_url' : get_enclosure_urls(entry),
		'enclosure_mimetype' : get_enclosure_mimetypes(entry),
		
		#'tag' : get_tags(entry)
	}

def get_authors(entry):
	return [strip_invalid_chars(a.name) for a in entry.authors]

def get_categories(entry):
	return [strip_invalid_chars(c.term) for c in entry.categories]

def get_category_schemes(entry):
	return [strip_invalid_chars(c.scheme) for c in entry.categories]

def get_enclosure_urls(entry):
	return [strip_invalid_chars(e.url) for e in entry.enclosures]

def get_enclosure_mimetypes(entry):
	return [strip_invalid_chars(e.type) for e in entry.enclosures]

# ========
# = main =
# ========

if __name__ == '__main__':
	
	usage = 'usage: %prog [options] driver://user:password@host/database'
	parser = OptionParser(usage)
	
	parser.add_option('-c', '--clear-index', 
		dest='clear_index', 
		action='store_true', 
		help='clear index before starting')
	parser.add_option('-f', '--file', 
		dest='input_file', 
		help='text file with newline-separated list of entries to update')
	parser.add_option('-o', '--optimize', 
		dest='optimize', 
		action='store_true', 
		help='optimize index after indexing is completed')
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
	
	if options.clear_index:
		lastIndexDateTime = NEVER
	
	solr = Solr(str(solrUrl))
	
	# =======
	# = run =
	# =======
	
	if options.clear_index:
		log("Clearing index...")
		solr.delete('*')
	
	start_time = util.now()
	
	log("Loading entry IDs...")
	entry_ids = ()
	if options.input_file:
		entry_ids = load_int_file(options.input_file)
	else:
		entry_ids = store.find(Entry,
			storm.expr.Or(
				Entry.date_added >= lastIndexDateTime,
				Entry.date_modified >= lastIndexDateTime
			)
		).order_by(Entry.id).values(Entry.id)
#	entry_ids = [156805]
	
	docs = []
	num = 0
	for entry_id in entry_ids:
		entry = store.find(Entry, Entry.id==entry_id)[0]
		
		log("Adding Entry with id %d" % entry.id)
		docs.append(createdoc(entry))
		num += 1
		if num % entriesPerPost == 0:
			solr.add(docs, False)
			docs = []
		if num % transactionSize == 0:
			log("Committing...")
			try:
				solr.commit()
			except pysolr.SolrError, e:
				log('%s, skipping last batch...' % str(e).strip())
			
	
	if len(docs) > 0:
		solr.add(docs)
	
	solr.commit()

	end_time = util.now()
	
	if not options.input_file:
		# Always do this last. 
		# After a program crash we'd rather index stuff twice than not at all.
		Conf.SetDateTime(store, CONF_LAST_INDEX_DATETIME, start_time)
	
	store.commit()
	
	# ==========
	# = finish =
	# ==========
	
	store.close()
	
	log('Done, elapsed time: %s' % (end_time-start_time,))

	if options.optimize:
		log("Optimizing...")
		start_time = util.now()

		solr.optimize()

		end_time = util.now()
		log('Done, elapsed time: %s' % (end_time-start_time,))

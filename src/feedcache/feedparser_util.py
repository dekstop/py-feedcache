# feedparser_util.py
#
# Misc static helpers to handle feedparser-specific data structures.
#
# martind 2008-11-22, 16:12:53
#

import httplib as HTTP

import feedparser

import feedcache.conf as conf
import feedcache.util as util
from feedcache.exceptions import FeedFetchError, FeedParseError

__all__ = [
	'fetch_feed',
	'http_status_not_modified', 'http_status_error', 'http_status_permanent_redirect',
	'build_author_tuple', 'build_category_tuple',
	'select_preferred_entry_content',
]

def fetch_feed(url, etag=None, modified=None, agent=None):
	"""
	Fetches a feed and returns a feedparser document. If no exception is thrown
	callers can assume that the returned object contains a valid feed.

	Raises a FeedFetchError if the HTTP request fails.
	Raises a FeedParseError if the returned document is in an unsupported format.
	"""
	d = None
	try:
		d = feedparser.parse(url, etag=etag, modified=modified, agent=conf.USER_AGENT)
	except LookupError, e:
		raise FeedParseError(url, None, 'Broken Character Encoding', e)

	# TODO: do we want to check the bozo bit?

	# check HTTP status for error states
	if http_status_not_modified(d):
		return d
	elif http_status_error(d):
		raise FeedFetchError(url, d, 'HTTP status code %d: %s' % (d.status, HTTP.responses[d.status]))

	# we received a full document. Check if we could parse it
	if d.version==None or d.version=='':
		# TODO: no idea how to get real feedback on whether parsing worked or not. check feedparser docs again
		raise FeedParseError(url, d, 'Unsupported Document Type')

	return d

def http_status_not_modified(fp_d):
	"""
	Evaluates the HTTP status code of a feedparser document.
	Returns true if the status code equals 304, NOT MODIFIED.
	"""
	return fp_d.get('status', 0)==HTTP.NOT_MODIFIED

def http_status_error(fp_d):
	"""
	Evaluates the HTTP status code of a feedparser document.
	Returns true if the status code signifies a failure, and
	further processing should be stopped.
	"""
	return fp_d.get('status', HTTP.OK) not in (
		HTTP.OK, # 200
		HTTP.MOVED_PERMANENTLY, # 301
		HTTP.FOUND, # 302
		HTTP.NOT_MODIFIED, # 304
		HTTP.TEMPORARY_REDIRECT, # 307
	)

def http_status_permanent_redirect(fp_d):
	"""
	Evaluates the HTTP status code of a feedparser document.
	Returns true if the status code equals 301, MOVED PERMANENTLY.
	"""
	return fp_d.get('status', 0)==HTTP.MOVED_PERMANENTLY

def build_author_tuple(fp_author):
	"""
	Takes a feedparser-style author tuple and makes it nice (e.g. gets rid of empty strings.)
	"""
	name = None
	email = None
	href = None
	if fp_author.has_key('name') and len(fp_author.name)>0:
		name = util.transcode(fp_author.name)
	if fp_author.has_key('email') and len(fp_author.email)>0:
		email = util.transcode(fp_author.email)
	if fp_author.has_key('href') and len(fp_author.href)>0:
		href = util.transcode(fp_author.href)
	if name==None:
		# e.g. managingEditor in RSS 2.0
		name = email
	if name==None:
		# last attempt, for invalid feeds. 
		# this should not be needed for valid feeds ('atom:name' is required, and rss has email instead)
		name = href
	return (name, email, href)

def build_category_tuple(fp_category):
	"""
	Takes a feedparser-style category (tag) tuple and makes it nice (e.g. gets rid of empty strings.)
	"""
	term = None
	scheme = None
	label = None
	if fp_category.has_key('term') and fp_category.term!='':
		term = util.transcode(fp_category.term)
	if fp_category.has_key('scheme') and fp_category.scheme!='':
		scheme = util.transcode(fp_category.scheme)
	if fp_category.has_key('label') and fp_category.label!='':
		label = util.transcode(fp_category.label)
	if term==None:
		# can this happen? if yes -> try term = label
		pass
	return (term, scheme, label)

def build_enclosure_tuple(fp_enclosure):
	"""
	Takes a feedparser-style category (tag) tuple and makes it nice (e.g. gets rid of empty strings.)
	"""
	url = None
	length = None
	type = None
	if fp_enclosure.has_key('href') and fp_enclosure.href!='':
		url = util.transcode(fp_enclosure.href)
	if fp_enclosure.has_key('length') and fp_enclosure.length!='':
		try:
			length = int(fp_enclosure.length)
		except ValueError, e:
			pass
	if fp_enclosure.has_key('type') and fp_enclosure.type!='':
		type = util.transcode(fp_enclosure.type)
	if url==None:
		# can this happen? if yes -> ignore enclosure
		pass
	return (url, length, type)

def select_preferred_entry_content(entries, 
	preferredContentTypes=['text/plain', 'text/html', 'application/xhtml+xml']):
	"""
	Picks one of the elements in feedparser's entries[i].content field (a list of dictionaries.)
	"""
	for type in preferredContentTypes:
		for entry in entries:
			if hasattr(entry, 'type') and entry.type==type:
				return entry.value
	# otherwise simply pick the first one
	return entries[0].value

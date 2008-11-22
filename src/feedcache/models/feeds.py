# feeds.py
#
# This code doesn't commit, it only flushes; this allows you to wrap your use 
# of this class in a transaction, and roll back changes in case of an exception
# during feed import/update. 
#
# The drawback is that you need to make sure to commit before your program 
# finishes (or gets killed, or exits with an exception), because otherwise all 
# changes are lost.
#
# Additionally, all causes for exceptions in this class are documented and 
# in the parsing stage, which is finished by the time it starts writing to the 
# database; any exceptions after that are bugs. (The only exception to this
# are SQL constraint violations that may get thrown while writing data.)
#
# In other words, a failure to fetch or parse a feed will not result in
# incomplete or orphaned database records.
#
# martind 2008-11-01, 11:17:11
#

import datetime
import hashlib
import httplib as HTTP
import time

import feedparser
import storm.locals as storm

from feedcache.exceptions import FeedFetchError, FeedParseError
from authors import Author, FeedAuthor, EntryAuthor
from categories import Category, FeedCategory, EntryCategory

__all__ = [
	'Batchimport',
	'Feed', 'Entry'
]

# =================
# = Configuration =
# =================

VERSION = '0.1'
USER_AGENT = feedparser.USER_AGENT + ' feedcache ' + VERSION + ', feedcache@dekstop.de'

preferredContentTypes = ['text/plain', 'text/html', 'application/xhtml+xml']

# ===========
# = Helpers =
# ===========

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

def transcode(str):
	"""
	Preprocessing for every single text string we store. Returns valid Unicode (NOT UTF-8).
	"""
	return unicode(str)#.encode('utf-8')

def to_datetime(_9tuple):
	"""
	Takes a 9-tuple as generated by feedparser, converts it into a
	UTC timestamp (a floating point number as generated by time.mktime.)
	"""
	# FIXME: would love to have a UTC equivalent...
	return time.mktime(_9tuple)

def from_datetime(datetime):
	"""
	Takes a UTC timestamp (a datetime object)
	and converts it into a 9-tuple to be used by feedparser.
	"""
	if datetime==None:
		return None
	# FIXME: we're using localtime instead of gmtime since there's no UTC equivalent for mktime
	return datetime.utctimetuple()

def datetime_now():
	"""
	Creates a UTC timestamp.
	"""
	return datetime.datetime.utcnow()

def build_author_tuple(fp_author):
	"""
	Takes a feedparser-style author tuple and makes it nice (e.g. gets rid of empty strings.)
	"""
	name = None
	email = None
	href = None
	if fp_author.has_key('name') and len(fp_author.name)>0:
		name = transcode(fp_author.name)
	if fp_author.has_key('email') and len(fp_author.email)>0:
		email = transcode(fp_author.email)
	if fp_author.has_key('href') and len(fp_author.href)>0:
		href = transcode(fp_author.href)
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
		term = transcode(fp_category.term)
	if fp_category.has_key('scheme') and fp_category.scheme!='':
		scheme = transcode(fp_category.scheme)
	if fp_category.has_key('label') and fp_category.label!='':
		label = transcode(fp_category.label)
	if term==None:
		# can this happen? if yes -> try term = label
		pass
	return (term, scheme, label)


def select_preferred_entry_content(entries):
	"""
	Picks one of the elements in feedparser's entries[i].content field (a list of dictionaries.)
	"""
	for type in preferredContentTypes:
		for entry in entries:
			if hasattr(entry, 'type') and entry.type==type:
				return entry.value
	# otherwise simply pick the first one
	return entries[0].value

def generate_entry_uid(*fields):
	"""
	TODO: stopgap measure. need to audit this.
	"""
	m = hashlib.sha1()
	for field in fields:
		if field!=None:
			m.update(field.encode('utf-8'))
	return u'generated:' + m.hexdigest()

def fetch_feed(url, etag=None, modified=None, agent=None):
	"""
	Fetches a feed and returns a feedparser document. If no exception is thrown
	callers can assume that the returned object contains a valid feed.
	
	Raises a FeedFetchError if the HTTP request fails.
	Raises a FeedParseError if the returned document is in an unsupported format.
	"""
	d = None
	try:
		d = feedparser.parse(url, etag=etag, modified=modified, agent=USER_AGENT)
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

# ===============
# = Batchimport =
# ===============

class Batchimport(object):
	__storm_table__ = 'batchimports'
	id = storm.Int(primary=True)

	feed_url = storm.Unicode()
	imported = storm.Bool()

	date_added = storm.DateTime()
	date_last_fetched = storm.DateTime()
	fail_count = storm.Int()
	
	def __init__(self, feed_url):
		self.feed_url = transcode(feed_url)
	
	def Queue(store, cutoff_time=datetime_now()):
		"""
		Static method, returns a ResultSet of zero or more Batchimport instances
		that were added before cutoff_time and haven't been imported.
		"""
		return store.find(Batchimport, 
			Batchimport.imported==False, 
			Batchimport.date_added<cutoff_time)
	
	def GetOne(store, cutoff_time=datetime_now(), retry_cutoff_time=datetime_now()):
		"""
		Returns a random non-imported Batchimport that was added before cutoff_time,
		and (if the last attempt failed) last fetched before retry_cutoff_time.
		
		This is NOT treadsafe! Multiple parralel workers may receive the same entry.
		"""
		return store.find(Batchimport, 
			Batchimport.imported==False, 
			storm.And(
				Batchimport.date_added<cutoff_time,
				storm.Or(
					Batchimport.fail_count == 0,
					storm.And(
						Batchimport.fail_count > 0,
						Batchimport.date_last_fetched<retry_cutoff_time,
					)
				)
			)).any()
	
	def FindByUrl(store, feed_url):
		"""
		Static method, returns a Batchimport intance, or None.
		Note that the entry may or may not have been imported -- so check
		its 'imported' property.
		"""
		return store.find(Batchimport, Batchimport.feed_url==feed_url).any()
	
	def CreateIfMissing(store, feed_url):
		"""
		Returns a new Batchimport entry if FindByUrl for this URL comes up empty.
		Returns None otherwise.
		"""
		if Batchimport.FindByUrl(store, feed_url):
			return None
		return Batchimport(feed_url)
	
	def import_feed(self, store):
		"""
		Attempts to fetch and import feed_url, returns a Feed instance on success,
		or throws an exception on failue. Always updates the date_last_fetched and fail_count 
		properties, even on exceptions.
		
		Raises a FeedFetchError if the HTTP request fails.
		Raises a FeedParseError if the returned document is in an unsupported format.
		"""
		self.date_last_fetched = datetime_now()
		try:
			feed = Feed.CreateFromUrl(store, self.feed_url)
			self.imported = True
			self.fail_count = 0
			return feed
		except:
			self.fail_count += 1
			raise
	
	Queue = staticmethod(Queue)
	GetOne = staticmethod(GetOne)
	FindByUrl = staticmethod(FindByUrl)
	CreateIfMissing = staticmethod(CreateIfMissing)

# ========
# = Feed =
# ========

class Feed(object):
	__storm_table__ = 'feeds'
	id = storm.Int(primary=True)
	
	active = storm.Bool()
	initial_url = storm.Unicode()
	actual_url = storm.Unicode()
	
	date_added = storm.DateTime()
	date_last_fetched = storm.DateTime()
	fail_count = storm.Int()
	
	http_last_modified = storm.DateTime()
	http_etag = storm.Unicode()
	
	title = storm.Unicode()
	description = storm.Unicode()
	link = storm.Unicode()
	ttl = storm.Int()
	date_updated = storm.DateTime()
	
	def Load(store, url):
		"""
		Static convenience method for testing. Tries to find the feed in the DB cache first,
		and on failure fetches it from its URL instead and places it in the cache.
		"""
		feed = Feed.FindByUrl(store, url)
		if (feed==None):
			feed = Feed.CreateFromUrl(store, url)
		return feed
	
	def FindById(store, id):
		"""
		Static method, returns a Feed instance or None.
		"""
		return store.find(Feed, Feed.id==id).any()
	
	def FindByUrl(store, url):
		"""
		Static method, returns a Feed instance or None. Accesses the DB cache, does not
		attempt to load the feed from its URL. Only matches against the feed's
		'initial_url' property, which uniquely identifies a feed.
		"""
		return store.find(Feed, Feed.initial_url==url).any()
	
	def FindByAnyUrl(store, url):
		"""
		Static method, returns a ResultSet of zero or more Feed instances that
		have 'feed_url' as their 'initial_url', 'actual_url' or 'link' property.
		"""
		return store.find(Feed, 
			storm.Or(
				Feed.initial_url==url, 
				Feed.actual_url==url, 
				Feed.link==url))

	def CreateFromUrl(store, url):
		"""
		Static method, constructs a Feed instance from a feed URL (or local file path.)
		This is always an uncached request, and on success will add the feed to the database.
		
		Raises a FeedFetchError if the HTTP request fails.
		Raises a FeedParseError if the returned document is in an unsupported format.
		May raise an IntegrityError (constraint violation) if the feed URL is already known.
		"""
		d = fetch_feed(url)
		feed = Feed()
		store.add(feed)
		feed.initial_url = transcode(url)
		feed._update_redirect_url(feed.initial_url, d)
		feed._apply_feed_document(store, d)
		
		return feed
	
	def GetOneForUpdate(store, cutoff_time=datetime_now(), retry_cutoff_time=datetime_now()):
		"""
		Returns a random non-imported Batchimport that was last fetched before cutoff_time,
		and (if the last attempt failed) last fetched before retry_cutoff_time.
		
		This is NOT treadsafe! Multiple parralel workers may receive the same entry.
		"""
		return store.find(Feed, 
			Feed.active==True, 
			storm.And(
				Feed.date_last_fetched<cutoff_time,
				storm.Or(
					Feed.fail_count == 0,
					storm.And(
						Feed.fail_count > 0,
						Feed.date_last_fetched<retry_cutoff_time,
					)
				)
			)).any()
	
	def update(self, store):
		"""
		Fetches a known feed again and applies updates. Always updates the 
		'date_last_fetched' and 'fail_count' properties, even on failure.
		
		Raises a FeedFetchError if the HTTP request fails.
		Raises a FeedParseError if the returned document is in an unsupported format.
		"""
		url = self.initial_url
		self._update_last_fetched()
		try:
			d = fetch_feed(url, etag=self.http_etag, modified=from_datetime(self.http_last_modified))
			self.fail_count = 0
			if http_status_not_modified(d):
				pass
			else:
				self._update_redirect_url(self.initial_url, d)
				self._apply_feed_document(store, d)
		except:
			self.fail_count += 1
			raise
	
	def _update_last_fetched(self):
		self.date_last_fetched = datetime_now()
	
	def _update_redirect_url(self, initial_url, d):
		# TODO: properly handle redirects
		if http_status_permanent_redirect(d) and d.feed.has_key('href'):
			self.actual_url = transcode(d.feed.href)
		else:
			self.actual_url = initial_url
	
	def _apply_feed_document(self, store, d):
		self._update_http_vars(d)
		self._update_properties(d)
		
		self._update_authors(store, d)
		self._update_categories(store, d)

		# this assumes that storm does proper 'dirty' checking and only writes on changes; 
		# otherwise this would be wasteful on every call
		store.flush()

		self._update_entries(store, d.entries)
	
	def _update_http_vars(self, d):
		if d.has_key('modified'):
			# TODO: we may have to parse this, this probably returns a string. should convert to UTC in that case.
			self.http_last_modified = to_datetime(d.modified)
		if d.has_key('etag'):
			self.http_etag = transcode(d.etag)
	
	def _update_properties(self, d):
		#if d.feed.has_key('title') and len(d.feed.title) > 0:
		self.title = transcode(d.feed.title)
		self.link = transcode(d.feed.link)
		if d.feed.has_key('subtitle'):
			self.description = transcode(d.feed.subtitle)
		if d.feed.has_key('id'):
			self.unique_id = transcode(d.feed.id)
		if d.feed.has_key('ttl'):
			self.ttl = int(d.feed.ttl)
		if d.feed.has_key('updated') and len(d.feed.updated)>0 and d.feed.has_key('updated_parsed'):
			self.date_updated = to_datetime(d.feed.updated_parsed)
	
	def _update_authors(self, store, d):
		fp_authors = []
		if d.feed.has_key('publisher_detail'):
			fp_authors.append(d.feed.publisher_detail)
		if d.feed.has_key('author_detail'):
			fp_authors.append(d.feed.author_detail)
		if d.feed.has_key('contributors'):
			for fp_author in d.feed.contributors:
				fp_authors.append(fp_author)
		for fp_author in fp_authors:
			name, email, link = build_author_tuple(fp_author)
			author = Author.FindOrCreate(store, name, email, link)
			if (author in self.authors)==False:
				self.authors.add(author)
	
	def _update_categories(self, store, d):
		if d.feed.has_key('tags'):
			for fp_category in d.feed.tags:
				term, scheme, label = build_category_tuple(fp_category)
				category = Category.FindOrCreate(store, term, scheme, label)
				if (category in self.categories)==False:
					self.categories.add(category)

	def _update_entries(self, store, feedparser_entries):
		# process from end to start to maintain entry order in storage
		# (this assumes that new feed entries come at the top of the feed)
		feedparser_entries.reverse()
		for fp_entry in feedparser_entries:
			Entry.CreateOrUpdate(store, self, fp_entry)
	
	FindById = staticmethod(FindById)
	FindByUrl = staticmethod(FindByUrl)
	FindByAnyUrl = staticmethod(FindByAnyUrl)
	CreateFromUrl = staticmethod(CreateFromUrl)
	GetOneForUpdate = staticmethod(GetOneForUpdate)
	Load = staticmethod(Load)

# =========
# = Entry =
# =========

class Entry(object):
	__storm_table__ = 'entries'
	id = storm.Int(primary=True)
	
	feed_id = storm.Int()
	feed = storm.Reference(feed_id, Feed.id)
	
	date_added = storm.DateTime()
	unique_id = storm.Unicode()
	title = storm.Unicode()
	content = storm.Unicode()
	summary = storm.Unicode()
	link = storm.Unicode()
	date_published = storm.DateTime()
	date_updated = storm.DateTime()
	
	def FindByUniqueId(store, feed, unique_id):
		"""
		Static method, returns an Entry instance or None.
		"""
		return store.find(Entry, Entry.feed==feed, Entry.unique_id==unique_id).any()
	
	def CreateOrUpdate(store, feed, feedparser_entry):
		# extract fields
		title = transcode(feedparser_entry.title)
		link = transcode(feedparser_entry.link)
		content = None
		if feedparser_entry.has_key('content'):
			content = transcode(select_preferred_entry_content(feedparser_entry.content))
		summary = None
		if feedparser_entry.has_key('summary'):
			summary = transcode(feedparser_entry.summary)
		date_published = None
		if feedparser_entry.has_key('published') and len(feedparser_entry.published)>0 and feedparser_entry.has_key('published_parsed'):
			date_published = to_datetime(feedparser_entry.published_parsed)
		date_updated = None
		if feedparser_entry.has_key('updated') and len(feedparser_entry.updated)>0 and feedparser_entry.has_key('updated_parsed'):
			date_updated = to_datetime(feedparser_entry.updated_parsed)
		
		# extract identity
		unique_id = None
		if feedparser_entry.has_key('id'):
			unique_id = transcode(feedparser_entry.id)
		else:
			unique_id = transcode(generate_entry_uid(title, link, content, summary))
		
		# store or update
		entry = Entry.FindByUniqueId(store, feed, unique_id)
		if (entry==None):
			# not in cache
			entry = Entry()
			entry.feed = feed
			entry.unique_id = unique_id
			
		entry.title = title
		entry.link = link
		entry.content = content
		entry.summary = summary
		entry.date_published = date_published
		entry.date_updated = date_updated
		
		entry._update_authors(store, feedparser_entry)
		entry._update_categories(store, feedparser_entry)
		
		# this assumes that storm does proper 'dirty' checking and only writes on changes; 
		# otherwise this would be wasteful on every call
		#store.add(entry)
		store.flush()
		
		return entry

	def _update_authors(self, store, feedparser_entry):
		fp_authors = []
		if feedparser_entry.has_key('author_detail'):
			fp_authors.append(feedparser_entry.author_detail)
		if feedparser_entry.has_key('contributors'):
			for fp_author in feedparser_entry.contributors:
				fp_authors.append(fp_author)
		for fp_author in fp_authors:
			name, email, link = build_author_tuple(fp_author)
			author = Author.FindOrCreate(store, name, email, link)
			if (author in self.authors)==False:
				self.authors.add(author)
				
	def _update_categories(self, store, feedparser_entry):
		if feedparser_entry.has_key('tags'):
			for fp_category in feedparser_entry.tags:
				term, scheme, label = build_category_tuple(fp_category)
				category = Category.FindOrCreate(store, term, scheme, label)
				if (category in self.categories)==False:
					self.categories.add(category)

	FindByUniqueId = staticmethod(FindByUniqueId)
	CreateOrUpdate = staticmethod(CreateOrUpdate)

# ==============
# = References =
# ==============

# many-to-one references
Feed.entries = storm.ReferenceSet(Feed.id, Entry.feed_id)

# many-to-many references
Feed.authors = storm.ReferenceSet(Feed.id, FeedAuthor.feed_id, FeedAuthor.author_id, Author.id)
Entry.authors = storm.ReferenceSet(Entry.id, EntryAuthor.entry_id, EntryAuthor.author_id, Author.id)

Feed.categories = storm.ReferenceSet(Feed.id, FeedCategory.feed_id, FeedCategory.category_id, Category.id)
Entry.categories = storm.ReferenceSet(Entry.id, EntryCategory.entry_id, EntryCategory.category_id, Category.id)

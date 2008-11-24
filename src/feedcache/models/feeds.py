# feeds.py
#
# This code does its own transaction handling for calls to Batchimport.import_feed() and 
# Feed.update():
# - it assumes that previous DB changes have been committed; otherwise they will be
#   lost on failure.
# - it commits on success
# - it colls back on failure, increases fail_count, sets date_last_fetched, commits.
#
# All causes for exceptions in this class are documented and mostly in the parsing 
# stage, which is finished by the time it starts writing to the database; any exceptions 
# after that are probably design bugs. (The only exception to this are SQL constraint 
# violations that may get thrown while writing data.)
#
# In other words, a failure to fetch or parse a feed will not result in
# incomplete or orphaned database records.
#
# martind 2008-11-01, 11:17:11
#

import sys

import storm.locals as storm

import feedcache.util as util
import feedcache.feedparser_util as fputil
from authors import Author, FeedAuthor, EntryAuthor
from categories import Category, FeedCategory, EntryCategory
from semaphores import Semaphore

__all__ = [
	'Batchimport',
	'Feed', 'Entry'
]

# ===============
# = Batchimport =
# ===============

class Batchimport(object):
	__storm_table__ = 'batchimports'
	id = storm.Int(primary=True)

	semaphore_id = storm.Int()
	semaphore = storm.Reference(semaphore_id, Semaphore.id)
	date_locked = storm.DateTime()

	url = storm.Unicode()
	imported = storm.Bool()

	date_added = storm.DateTime()
	date_last_fetched = storm.DateTime()
	fail_count = storm.Int()
	
	def __init__(self, url):
		self.url = util.transcode(url)
	
	def GetOne(store, cutoff_time=util.datetime_now(), retry_cutoff_time=util.datetime_now()):
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
	
	def FindByUrl(store, url):
		"""
		Static method, returns a Batchimport intance, or None.
		Note that the entry may or may not have been imported -- so check
		its 'imported' property.
		"""
		return store.find(Batchimport, Batchimport.url==url).any()
	
	def CreateIfMissing(store, url):
		"""
		Returns a Batchimport instance.
		Creates a new Batchimport entry if FindByUrl for this URL comes up empty,
		then commits.
		"""
		b = Batchimport.FindByUrl(store, url)
		if b:
			return b
		b = Batchimport(url)
		store.add(b)
		store.commit()
		return b
	
	def import_feed(self, store):
		"""
		Attempts to fetch and import the feed, returns a Feed instance on success,
		or throws an exception on failue. Always updates the date_last_fetched and fail_count 
		properties, even on exceptions. Will log a BatchimportMessage in the event of
		an exception.
		
		Raises a FeedFetchError if the HTTP request fails.
		Raises a FeedParseError if the returned document is in an unsupported format.
		"""
		fetch_date = util.datetime_now()
		self.date_last_fetched = fetch_date
		try:
			feed = Feed.CreateFromUrl(store, self.url)
			self.imported = True
			self.fail_count = 0
			store.commit()
			return feed
		except:
			store.rollback()
			self.fail_count += 1
			self.date_last_fetched = fetch_date
			e = sys.exc_info()[1]
			b = BatchimportMessage.FromException(store, self, e)
			store.add(b)
			store.commit()
			raise
	
	GetOne = staticmethod(GetOne)
	FindByUrl = staticmethod(FindByUrl)
	CreateIfMissing = staticmethod(CreateIfMissing)

# ========
# = Feed =
# ========

class Feed(object):
	__storm_table__ = 'feeds'
	id = storm.Int(primary=True)
	
	semaphore_id = storm.Int()
	semaphore = storm.Reference(semaphore_id, Semaphore.id)
	date_locked = storm.DateTime()

	active = storm.Bool()
	url = storm.Unicode()
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
		'url' property, which uniquely identifies a feed.
		"""
		return store.find(Feed, Feed.url==url).any()
	
	def FindByAnyUrl(store, url):
		"""
		Static method, returns a ResultSet of zero or more Feed instances that
		have 'url' as their 'url', 'actual_url' or 'link' property.
		"""
		return store.find(Feed, 
			storm.Or(
				Feed.url==url, 
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
		try:
			d = fputil.fetch_feed(url)
			feed = Feed()
			store.add(feed)
			feed.url = util.transcode(url)
			feed._update_redirect_url(feed.url, d)
			feed._apply_feed_document(store, d)
			store.commit()
		except:
			store.rollback()
			raise
		
		return feed
	
	def GetOneForUpdate(store, cutoff_time=util.datetime_now(), retry_cutoff_time=util.datetime_now()):
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
		Will log a BatchimportMessage in the event of an exception.
		
		Raises a FeedFetchError if the HTTP request fails.
		Raises a FeedParseError if the returned document is in an unsupported format.
		"""
		fetch_date = util.datetime_now()
		self.date_last_fetched = fetch_date
		try:
			d = fputil.fetch_feed(self.url, 
				etag=self.http_etag, 
				modified=util.from_datetime(self.http_last_modified))
			self.fail_count = 0
			if fputil.http_status_not_modified(d):
				pass
			else:
				self._update_redirect_url(self.url, d)
				self._apply_feed_document(store, d)
			store.commit()
		except:
			store.rollback()
			self.fail_count += 1
			self.date_last_fetched = fetch_date
			e = sys.exc_info()[0]
			f = FeedMessage.FromException(store, self, e)
			store.add(f)
			store.commit()
			raise
	
	def _update_redirect_url(self, url, d):
		# TODO: properly handle redirects
		if fputil.http_status_permanent_redirect(d) and d.feed.has_key('href'):
			self.actual_url = util.transcode(d.feed.href)
		else:
			self.actual_url = url
	
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
			self.http_last_modified = util.to_datetime(d.modified)
		if d.has_key('etag'):
			self.http_etag = util.transcode(d.etag)
	
	def _update_properties(self, d):
		#if d.feed.has_key('title') and len(d.feed.title) > 0:
		self.title = util.transcode(d.feed.title)
		self.link = util.transcode(d.feed.link)
		if d.feed.has_key('subtitle'):
			self.description = util.transcode(d.feed.subtitle)
		if d.feed.has_key('id'):
			self.unique_id = util.transcode(d.feed.id)
		if d.feed.has_key('ttl'):
			self.ttl = int(d.feed.ttl)
		if d.feed.has_key('updated') and len(d.feed.updated)>0 and d.feed.has_key('updated_parsed'):
			self.date_updated = util.to_datetime(d.feed.updated_parsed)
	
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
			name, email, link = fputil.build_author_tuple(fp_author)
			author = Author.FindOrCreate(store, name, email, link)
			if (author in self.authors)==False:
				self.authors.add(author)
	
	def _update_categories(self, store, d):
		if d.feed.has_key('tags'):
			for fp_category in d.feed.tags:
				term, scheme, label = fputil.build_category_tuple(fp_category)
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
		title = util.transcode(feedparser_entry.title)
		link = util.transcode(feedparser_entry.link)
		content = None
		if feedparser_entry.has_key('content'):
			content = util.transcode(fputil.select_preferred_entry_content(feedparser_entry.content))
		summary = None
		if feedparser_entry.has_key('summary'):
			summary = util.transcode(feedparser_entry.summary)
		date_published = None
		if feedparser_entry.has_key('published') and len(feedparser_entry.published)>0 and feedparser_entry.has_key('published_parsed'):
			date_published = util.to_datetime(feedparser_entry.published_parsed)
		date_updated = None
		if feedparser_entry.has_key('updated') and len(feedparser_entry.updated)>0 and feedparser_entry.has_key('updated_parsed'):
			date_updated = util.to_datetime(feedparser_entry.updated_parsed)
		
		# extract identity
		unique_id = None
		if feedparser_entry.has_key('id'):
			unique_id = util.transcode(feedparser_entry.id)
		else:
			unique_id = util.transcode(util.generate_entry_uid(title, link, content, summary))
		
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
			name, email, link = fputil.build_author_tuple(fp_author)
			author = Author.FindOrCreate(store, name, email, link)
			if (author in self.authors)==False:
				self.authors.add(author)
				
	def _update_categories(self, store, feedparser_entry):
		if feedparser_entry.has_key('tags'):
			for fp_category in feedparser_entry.tags:
				term, scheme, label = fputil.build_category_tuple(fp_category)
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

# moved this to the end because this include establishes a circular reference between modules:
from messages import BatchimportMessage, FeedMessage

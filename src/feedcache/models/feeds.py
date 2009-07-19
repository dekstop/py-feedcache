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
# In other words, a failure to fetch or parse a feed will not result in incomplete or 
# orphaned database records.
#
# martind 2008-11-01, 11:17:11
#

import sys

import storm.locals as storm

import feedcache.util as util
import feedcache.feedparser_util as fputil
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

	active = storm.Bool()
	url = storm.Unicode()
	user_id = storm.Int()
	imported = storm.Bool()

	date_added = storm.DateTime()
	date_last_fetched = storm.DateTime()
	fail_count = storm.Int()
	
	def __init__(self, url):
		self.url = util.transcode(url)
	
	def FindByUrl(store, url):
		"""
		Static method, returns a Batchimport intance, or None.
		Note that the entry may or may not have been imported -- so check
		its 'imported' property.
		"""
		return store.find(Batchimport, Batchimport.url==url).any()
	
	def CreateIfMissing(store, url, user=None):
		"""
		Returns a Batchimport instance.
		Creates a new Batchimport entry if FindByUrl for this URL comes up empty,
		then commits.
		If the URL already exists in the Batchimport queue the entry will be activated
		(if it had been deactivated), and fail_count will be set to 0.
		"""
		b = Batchimport.FindByUrl(store, url)
		if b:
			b.active = true
			b.fail_count = 0
		else:
			b = Batchimport(url)
		if user:
			# FIXME: current DB schema only allows one user per batchimport
			b.user_id = user.id
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
		fetch_date = util.now()
		self.date_last_fetched = fetch_date
		try:
			feed = Feed.Load(store, self.url)
			self.imported = True
			self.fail_count = 0

			if self.user_id:
				from feedcache.models.users import User
				user = store.find(User, User.id==self.user_id).any()
				if not (feed in user.feeds):
					user.feeds.add(feed)

			store.commit()
			return feed
		except KeyboardInterrupt:
			raise
		except:
			store.rollback()
			self.fail_count += 1
			self.date_last_fetched = fetch_date
			e = sys.exc_info()[1]
			b = BatchimportMessage.FromException(store, self, e)
			store.add(b)
			store.commit()
			raise
	
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
	
	def update(self, store):
		"""
		Fetches a known feed again and applies updates. Always updates the 
		'date_last_fetched' and 'fail_count' properties, even on failure.
		Will log a BatchimportMessage in the event of an exception.
		
		Raises a FeedFetchError if the HTTP request fails.
		Raises a FeedParseError if the returned document is in an unsupported format.
		"""
		fetch_date = util.now()
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
		except KeyboardInterrupt:
			raise
		except:
			store.rollback()
			self.fail_count += 1
			self.date_last_fetched = fetch_date
			e = sys.exc_info()[1]
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
		# otherwise it would be wasteful to override every field on every call
		store.flush()

		self._update_entries(store, d.entries)
	
	def _update_http_vars(self, d):
		if d.has_key('modified'):
			# TODO: we may have to parse this, this probably returns a string. should convert to UTC in that case.
			self.http_last_modified = util.to_datetime(d.modified)
		if d.has_key('etag'):
			self.http_etag = util.transcode(d.etag)
	
	def _update_properties(self, d):
		if d.feed.has_key('title') and len(d.feed.title) > 0:
			self.title = util.transcode(d.feed.title)
		else:
			self.title = self.url
		if d.feed.has_key('link') and len(d.feed.link) > 0:
			self.link = util.transcode(d.feed.link)
		else:
			self.link = self.url
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
			if name!=None:
				author = Author.FindOrCreate(store, self, name, email, link)
				if (author in self.authors)==False:
					self.authors.add(author)
	
	def _update_categories(self, store, d):
		if d.feed.has_key('tags'):
			for fp_category in d.feed.tags:
				term, scheme, label = fputil.build_category_tuple(fp_category)
				if term!=None:
					category = Category.FindOrCreate(store, self, term, scheme, label)
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
	Load = staticmethod(Load)

# =========
# = Entry =
# =========

class Entry(object):
	__storm_table__ = 'entries'
	id = storm.Int(primary=True)
	date_modified = storm.DateTime()
	
	feed_id = storm.Int()
	feed = storm.Reference(feed_id, Feed.id)
	
	date_added = storm.DateTime()
	unique_id = storm.Unicode()
	title = storm.Unicode()
	content = storm.Unicode()
	summary = storm.Unicode()
	link = storm.Unicode()

	date = storm.DateTime()
	date_published = storm.DateTime()
	date_updated = storm.DateTime()
	
	def FindByUniqueId(store, feed, unique_id):
		"""
		Static method, returns an Entry instance or None.
		"""
		return store.find(Entry, Entry.feed==feed, Entry.unique_id==unique_id).any()
	
	def CreateOrUpdate(store, feed, feedparser_entry):
		# extract fields
		link = None
		if feedparser_entry.has_key('link') and len(feedparser_entry.link)>0:
			link = util.transcode(feedparser_entry.link)
		content = None
		if feedparser_entry.has_key('content') and len(feedparser_entry.content)>0:
			content = util.transcode(fputil.select_preferred_entry_content(feedparser_entry.content))
		summary = None
		if feedparser_entry.has_key('summary') and len(feedparser_entry.summary)>0:
			summary = util.transcode(feedparser_entry.summary)
		title = None
		if feedparser_entry.has_key('title') and len(feedparser_entry.title)>0:
			title = util.transcode(feedparser_entry.title)
		else:
			# bradfitz has those...
			title = util.transcode(util.excerpt(util.strip_html(summary or content), 100))

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
		
		dates = [util.now()]
		if entry.date_published:
			dates += [entry.date_published]
		if entry.date_updated:
			dates += [entry.date_updated]
		entry.date = min(dates)

		# this assumes that storm does proper 'dirty' checking and only writes on changes; 
		# otherwise it would be wasteful to override every field on every call
		#store.add(entry)		
		store.flush()
		
		entry._update_authors(store, feedparser_entry)
		entry._update_categories(store, feedparser_entry)
		entry._update_enclosures(store, feedparser_entry)
		
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
			if name!=None:
				author = Author.FindOrCreate(store, self.feed, name, email, link)
				if (author in self.authors)==False:
					self.authors.add(author)
				
	def _update_categories(self, store, feedparser_entry):
		if feedparser_entry.has_key('tags'):
			for fp_category in feedparser_entry.tags:
				term, scheme, label = fputil.build_category_tuple(fp_category)
				if term!=None:
					category = Category.FindOrCreate(store, self.feed, term, scheme, label)
					if (category in self.categories)==False:
						self.categories.add(category)

	def _update_enclosures(self, store, feedparser_entry):
		if feedparser_entry.has_key('enclosures'):
			for fp_enclosure in feedparser_entry.enclosures:
				url, length, type = fputil.build_enclosure_tuple(fp_enclosure)
				enclosure = Enclosure.FindOrCreate(store, self.feed, url, length, type)
				if (enclosure in self.enclosures)==False:
					self.enclosures.add(enclosure)

	FindByUniqueId = staticmethod(FindByUniqueId)
	CreateOrUpdate = staticmethod(CreateOrUpdate)

# ==============
# = References =
# ==============

# FIXME: had to move this to the end because these includes establish a circular reference between modules.
from messages import BatchimportMessage, FeedMessage
from authors import Author, EntryAuthor
from categories import Category, EntryCategory
from enclosures import Enclosure, EntryEnclosure

# many-to-one references
Feed.entries = storm.ReferenceSet(Feed.id, Entry.feed_id)

# many-to-many references
Feed.authors = storm.ReferenceSet(Feed.id, Author.feed_id, Author.id)
Entry.authors = storm.ReferenceSet(Entry.id, EntryAuthor.entry_id, EntryAuthor.author_id, Author.id)

Feed.categories = storm.ReferenceSet(Feed.id, Category.feed_id, Category.id)
Entry.categories = storm.ReferenceSet(Entry.id, EntryCategory.entry_id, EntryCategory.category_id, Category.id)

Feed.enclosures = storm.ReferenceSet(Feed.id, Enclosure.feed_id, Enclosure.id)
Entry.enclosures = storm.ReferenceSet(Entry.id, EntryEnclosure.entry_id, EntryEnclosure.enclosure_id, Enclosure.id)

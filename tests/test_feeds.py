import collections
import os
import shutil
import tempfile
import unittest

import storm.locals

from feedcache.models.feeds import Feed, Entry
import feedcache.exceptions

import conf as TEST
from base import *

# =========
# = tests =
# =========


class BasicParserTest(DBTestBase):
	
	def testLoadFeed(self):
		"""fetches a new (uncached) feed and verifies some fields."""
		feed = Feed.Load(self.store, TEST.fixture(u'dekstop.de_weblog_index.xml'))
		
		self.assertEquals(u'dekstop weblog', feed.title)
		self.assertEquals(u'http://dekstop.de/weblog/', feed.link)
		self.assertEquals(15, feed.entries.count())
	
	def testFeedEntryOrder(self):
		"""feed entries must be stored in reverse feed order"""
		feed = Feed.Load(self.store, TEST.fixture(u'dekstop.de_weblog_index.xml'))
		entries = feed.entries.order_by(Entry.id)
		
		entry1 = entries.first()
		self.assertEquals(u'2007-05-27T22:47:55', entry1.date_updated.isoformat())
		self.assertEquals(u'http://dekstop.de/weblog/2007/05/ipod_offline_feed_reader/', entry1.link)
		self.assertEquals(u'Teaser: Offline Feed Reader for Your iPod', entry1.title)

		entry2 = entries.last()
		self.assertEquals(u'2008-09-11T01:28:08', entry2.date_updated.isoformat())
		self.assertEquals(u'http://dekstop.de/weblog/2008/09/google_news_almost_bankrupts_multinational/', entry2.link)
		self.assertEquals(u'Google News Almost Bankrupts Multinational', entry2.title)
	
class AuthorTest(DBTestBase):
	
	def testFeedAuthor(self):
		"""must properly detect feed author(s)"""
		feed = Feed.Load(self.store, TEST.fixture(u'www.dot-alt.blogspot.com_atom.xml'))
		self.assertEquals(1, feed.authors.count())
		self.assertEquals(u'Alex Bok Bok', feed.authors.any().name)
		self.assertEquals(u'noreply@blogger.com', feed.authors.any().email)
		self.assertEquals(u'http://www.blogger.com/profile/15625196533865711283', feed.authors.any().link)

	def testEntryAuthor(self):
		"""must properly detect entry author(s)"""
		feed = Feed.Load(self.store, TEST.fixture(u'www.dot-alt.blogspot.com_atom.xml'))
		counters = collections.defaultdict(int)
		# verify that entries have full author metadata
		for entry in feed.entries:
			self.assertEquals(1, entry.authors.count())
			author = entry.authors.any()
			counters[author.name] += 1
			self.assertTrue(author.name in [
				u'Dope Game Tom',
				u'Fasting Eddie',
				u'dan hancox',
				u'Alex Bok Bok',
			])
			self.assertEquals(u'noreply@blogger.com', author.email)
			self.assertTrue(author.link in [
				u'http://www.blogger.com/profile/00877774752980602832',
				u'http://www.blogger.com/profile/09210625737432818809',
				u'http://www.blogger.com/profile/14335192225001443427',
				u'http://www.blogger.com/profile/15625196533865711283'
			])
		# verify author posting histogram
		self.assertEquals(4, len(counters.keys()))
		self.assertEquals(7, counters[u'dan hancox'])
		self.assertEquals(1, counters[u'Fasting Eddie'])
		self.assertEquals(15, counters[u'Alex Bok Bok'])
		self.assertEquals(2, counters[u'Dope Game Tom'])

class CategoryTest(DBTestBase):
	
	def testEntryCategory(self):
		"""must properly detect entry author(s)"""
		feed = Feed.Load(self.store, TEST.fixture(u'www.dot-alt.blogspot.com_atom.xml'))
		
		counters = collections.defaultdict(int)
		# verify that entries have full author metadata
		for entry in feed.entries:
			for category in entry.categories:
				counters[category.term] += 1
				self.assertTrue(category.term in [
					u'1xtra', u'2012', u'7 year glitch', u'Afro House', u'Dennis Ferrer', 
					u'Essential Mix', u'Jammer', u'Pop', u'R\'n\'B', u'Rap', u'Rinse', u'Siji', 
					u'Spyro', u'UPZ', u'Wiley', u'audio', u'badness', u'baltimore', u'ben ufo', 
					u'birthday', u'black plague', u'blaqstarr', u'bmore', u'bok bok', 
					u'carnival', u'chockablock', u'club', u'club vortex', u'd-malice', 
					u'deeptime', u'dev79', u'dizzee rascal', u'donaeo', u'dopegames', 
					u'download', u'drop the lime', u'dubchild', u'dubstep', u'dubstep forum', 
					u'eid', u'eid mubarak', u'electro', u'episode', u'fabric', u'flyer', 
					u'forums', u'frankie solar', u'funky', u'girl u no its true', u'grime', 
					u'grimetapes', u'hard house banton', u'hessle audio', u'house', 
					u'immediate sounds', u'k-swift', u'kingdom', u'kode9', u'kwaito', 
					u'l-vis 1990', u'london', u'majuva', u'mak10', u'manara', u'marcus nasty', 
					u'maximum', u'media', u'mixes', u'mp3', u'mr charisma', u'new york', 
					u'night', u'night slugs', u'no hats no hoods', u'nostalgia', u'nyc', 
					u'olympics', u'party', u'patchwork pirates', u'pirate', u'podcast', 
					u'race', u'radio', u'resonance', u'rip', u'rowdy', u'roy davis jr', 
					u'secret agent gel', u'silverlink', u'soca', u'starkey', u'sub fm', 
					u'the heatwave', u'the message is love', u'todd edwards', u'track', 
					u'trouble and bass', u'uk house', u'wfmu', u'youtube',
				])
				self.assertEquals('http://www.blogger.com/atom/ns#', category.scheme)
		# verify category histogram
		self.assertEquals(100, len(counters.keys()))
		self.assertEquals(10, counters[u'mp3'])
		self.assertEquals(8, counters[u'audio'])
		self.assertEquals(4, counters[u'Wiley'])
		self.assertEquals(4, counters[u'sub fm'])

class ParseErrorTest(DBTestBase):
	
	def testEmptyDocument(self):
		"""must throw a ParseException when encountering an empty document"""
		self.assertRaises(
			feedcache.exceptions.FeedParseError, 
			Feed.Load, self.store, TEST.fixture(u'empty.xml'))

	def testUnsupportedDocumentType(self):
		"""must throw a ParseException when encountering an unsuported document type"""
		self.assertRaises(
			feedcache.exceptions.FeedParseError, 
			Feed.Load, self.store, TEST.fixture(u'html_document.html'))

class TransactionTest(DBTestBase):
	
	def testTransactionRollback(self):
		"""a failed feed import must not result in orphaned records (unused author/entry/category/... rows)"""
		try:
			feed = Feed.Load(self.store, TEST.fixture(u'broken_encoding.xml')) # expected to throw a FeedParseError
			self.assertTrue(False)
		except feedcache.exceptions.FeedParseError, e:
			self.store.rollback()
		
		for tablename in TEST.tables():
			result = self.store.execute('select count(*) from ' + tablename)
			self.assertEquals(0, result.get_one()[0], 
				'table "%s" is not empty after rollback' % (tablename))

class SerialisationConsistencyTest(DBTestBase):
	
	def testTextSerialisationConsistency(self):
		"""text fields must be the same on first fetch and every consecutive update when the feed content doesn't change"""
		feed = Feed.Load(self.store, TEST.fixture(u'delicious_tag_feed.xml'))
		title = feed.title
		link = feed.link
		description = feed.description
		
		feed = Feed.FindByUrl(self.store, TEST.fixture(u'delicious_tag_feed.xml'))
		feed.update(self.store)
		
		feed = Feed.Load(self.store, TEST.fixture(u'delicious_tag_feed.xml'))
		self.assertEquals(feed.title, title)
		self.assertEquals(feed.link, link)
		self.assertEquals(feed.description, description)

	def testDateSerialisationConsistency(self):
		"""date fields must be the same on first fetch and every consecutive update when the feed content doesn't change"""
		feed = Feed.Load(self.store, TEST.fixture(u'delicious_tag_feed.xml'))
		entries = feed.entries.order_by(Entry.id)
		entry = entries.first()
		date_published = entry.date_published
		date_updated = entry.date_updated

		feed = Feed.FindByUrl(self.store, TEST.fixture(u'delicious_tag_feed.xml'))
		feed.update(self.store)

		feed = Feed.Load(self.store, TEST.fixture(u'delicious_tag_feed.xml'))
		entries = feed.entries.order_by(Entry.id)
		entry = entries.first()
		self.assertEquals(entry.date_published, date_published)
		self.assertEquals(entry.date_updated, date_updated)

class FeedFetchTimestampTest(DBTestBase):
	
	def testFeedAddedTimestamp(self):
		"""a feed's 'date_added' property must not change on consecutive feed updates"""
		feed = Feed.Load(self.store, TEST.fixture(u'delicious_tag_feed.xml'))
		date_added = feed.date_added

		feed = Feed.FindByUrl(self.store, TEST.fixture(u'delicious_tag_feed.xml'))
		feed.update(self.store)

		feed = Feed.Load(self.store, TEST.fixture(u'delicious_tag_feed.xml'))
		self.assertEquals(feed.date_added, date_added)
	
	def testFeedUpdateTimestamp(self):
		"""a feed's 'date_last_fetched' property must change on every feed update"""
		feed = Feed.Load(self.store, TEST.fixture(u'delicious_tag_feed.xml'))
		date_last_fetched = feed.date_last_fetched

		feed = Feed.FindByUrl(self.store, TEST.fixture(u'delicious_tag_feed.xml'))
		feed.update(self.store)

		feed = Feed.Load(self.store, TEST.fixture(u'delicious_tag_feed.xml'))
		self.assertNotEquals(feed.date_last_fetched, date_last_fetched)

class EntryUpdateTest(DBTestBase):
	
	# FIXME: since we don't have a good mocking mechanism we need to copy multiple
	# versions of the same data set to the same location instead
	feedurl = unicode(tempfile.mktemp(".xml"))

	def testCanCreateTempFile(self):
		"""check that we can create a temp file during testing"""
		shutil.copy(TEST.fixture(u'flickr_tag_feed.xml'), self.feedurl)
		self.assertTrue(os.path.isfile(self.feedurl))

	def testUpdateEntryCount(self):
		"""a feed update must not result in duplicate versions of old entries"""
		shutil.copy(TEST.fixture(u'flickr_tag_feed.xml'), self.feedurl)
		feed = Feed.Load(self.store, self.feedurl)
		oldcount = feed.entries.count()
		
		shutil.copy(TEST.fixture(u'flickr_tag_feed_updated.xml'), self.feedurl)
		feed = Feed.FindByUrl(self.store, self.feedurl)
		feed.update(self.store)
		self.assertEquals(feed.entries.count(), oldcount)

	def testUpdateEntryContent(self):
		"""must detect and store updated entry content"""
		shutil.copy(TEST.fixture(u'flickr_tag_feed.xml'), self.feedurl)
		feed = Feed.Load(self.store, self.feedurl)
		oldcontent = feed.entries.order_by(Entry.id).first().content
		
		shutil.copy(TEST.fixture(u'flickr_tag_feed_updated.xml'), self.feedurl)
		feed = Feed.FindByUrl(self.store, self.feedurl)
		feed.update(self.store)
		self.assertNotEquals(feed.entries.order_by(Entry.id).first().content, oldcontent)

class AddEntryTest(DBTestBase):

	# FIXME: since we don't have a good mocking mechanism we need to copy multiple
	# versions of the same data set to the same location instead	
	feedurl = unicode(tempfile.mktemp(".xml"))

	def testAddEntryCount(self):
		"""an additional entry after a feed update must increase the entry count by 1"""
		shutil.copy(TEST.fixture(u'flickr_tag_feed.xml'), self.feedurl)
		feed = Feed.Load(self.store, self.feedurl)
		oldcount = feed.entries.count()
		
		shutil.copy(TEST.fixture(u'flickr_tag_feed_added.xml'), self.feedurl)
		feed = Feed.FindByUrl(self.store, self.feedurl)
		feed.update(self.store)
		self.assertEquals(feed.entries.count(), oldcount + 1)

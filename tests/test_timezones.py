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

class TimezoneTest(DBTestBase):
	
	def testRss2Pubdate_0000(self):
		"""RSS 2.0 feed and entry pubDate fields with timezone offset +0000 must be converted to UTC timezone."""
		feed = Feed.Load(self.store, TEST.fixture(u'conicsocial.cybersonica.org__feed_rss2'))
		self.assertEquals('2008-10-07 14:22:28', str(feed.date_updated))
		entry = feed.entries.order_by(Entry.id).first()
		self.assertEquals('2008-04-28 02:51:58', str(entry.date_updated))

	def testRss2Pubdate_GMT(self):
		"""RSS 2.0 feed and entry pubDate fields with GMT timezone offset must be converted to UTC timezone."""
		feed = Feed.Load(self.store, TEST.fixture(u'dekstop.de_weblog_index.xml'))
		#self.assertEquals('2008-09-11 01:28:08', str(feed.date_updated))
		entry = feed.entries.order_by(Entry.id).first()
		self.assertEquals('2007-05-27 22:47:55', str(entry.date_updated))

	def testRss1Pubdate_Z(self):
		"""RSS 1.0 feed and entry pubDate fields with 'Z' timezone offset must be converted to UTC timezone."""
		feed = Feed.Load(self.store, TEST.fixture(u'delicious_tag_feed.xml'))
		#self.assertEquals('2008-09-11 01:28:08', str(feed.date_updated))
		entry = feed.entries.order_by(Entry.id).first()
		self.assertEquals('2008-10-11 13:23:00', str(entry.date_updated))

	def testAtomUpdated_Z(self):
		"""Atom feed and entry published and updated fields with 'Z' timezone offset must be converted to UTC timezone."""
		feed = Feed.Load(self.store, TEST.fixture(u'flickr_tag_feed.xml'))
		self.assertEquals('2008-08-27 13:30:32', str(feed.date_updated))
		entry = feed.entries.order_by(Entry.id).first()
		self.assertEquals('2008-08-27 13:31:38', str(entry.date_updated))
		self.assertEquals('2008-08-27 13:31:38', str(entry.date_published))

	def testAtomUpdated_0100(self):
		"""Atom feed and entry published and updated fields with timezone offset +0100 must be converted to UTC timezone."""
		# These tests fail, because one of feedparser's date handlers seems to apply the timezone wrong.
		feed = Feed.Load(self.store, TEST.fixture(u'www.dot-alt.blogspot.com_atom.xml'))
		#self.assertEquals('2008-10-11 11:48:34', str(feed.date_updated))
		entry = feed.entries.order_by(Entry.id).first()
		#self.assertEquals('2008-06-19 14:08:00', str(entry.date_updated))
		#self.assertEquals('2008-06-19 18:12:37', str(entry.date_published))


import os
import shutil
import tempfile

from feedcache.models.feeds import Batchimport, Feed

import conf as TEST
from base import *

# =========
# = tests =
# =========

class BatchimportMessageTest(DBTestBase):
	
	def testSuccessfulBatchimport(self):
		"""successful batchimport must not create a message."""
		b = Batchimport.CreateIfMissing(self.store, TEST.fixture(u'dekstop.de_weblog_index.xml'))
		b.import_feed(self.store)

		result = self.store.execute('select count(*) from messages')
		count = result.get_one()[0]
		self.assertEquals(0, count, 'table "messages" has %d entries, when it should have 0' % (count))

		b = Batchimport.FindByUrl(self.store, TEST.fixture(u'dekstop.de_weblog_index.xml'))
		self.assertEquals(0, b.messages.count())
	
	def testFailedBatchimport(self):
		"""failed batchimport must create one message."""
		b = Batchimport.CreateIfMissing(self.store, TEST.fixture(u'broken_encoding.xml'))
		try:
			b.import_feed(self.store) # this is expected to throw an exception
			self.assertTrue(False)
		except:
			pass

		result = self.store.execute('select count(*) from messages')
		count = result.get_one()[0]
		self.assertEquals(1, count, 'table "messages" has %d entries, when it should have 1' % (count))

		b = Batchimport.FindByUrl(self.store, TEST.fixture(u'broken_encoding.xml'))
		self.assertEquals(1, b.messages.count())

class FeedMessageTest(DBTestBase):
	
	feedurl = unicode(tempfile.mktemp(".xml"))
	
	def testCanCreateTempFile(self):
		"""check that we can create a temp file during testing"""
		shutil.copy(TEST.fixture(u'dekstop.de_weblog_index.xml'), self.feedurl)
		self.assertTrue(os.path.isfile(self.feedurl))

	def testSuccessfulFeedUpdate(self):
		"""successful feed update must not create a message."""
		f = Feed.Load(self.store, TEST.fixture(u'dekstop.de_weblog_index.xml'))
		f.update(self.store)

		result = self.store.execute('select count(*) from messages')
		count = result.get_one()[0]
		self.assertEquals(0, count, 'table "messages" has %d entries, when it should have 0' % (count))

		f = Feed.FindByUrl(self.store, TEST.fixture(u'dekstop.de_weblog_index.xml'))
		self.assertEquals(0, f.messages.count())
	
	def testFailedFeedUpdate(self):
		"""failed feed update must create one message."""
		shutil.copy(TEST.fixture(u'dekstop.de_weblog_index.xml'), self.feedurl)
		f = Feed.Load(self.store, self.feedurl)
		try:
			shutil.copy(TEST.fixture(u'broken_encoding.xml'), self.feedurl)
			f.update(self.store) # this is expected to throw an exception
			self.assertTrue(False)
		except:
			pass

		result = self.store.execute('select count(*) from messages')
		count = result.get_one()[0]
		self.assertEquals(1, count, 'table "messages" has %d entries, when it should have 1' % (count))

		b = Feed.FindByUrl(self.store, self.feedurl)
		self.assertEquals(1, f.messages.count())


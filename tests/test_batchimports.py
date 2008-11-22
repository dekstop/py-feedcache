from feedcache.models.feeds import Batchimport, Feed

import conf as TEST
from base import *

# =========
# = tests =
# =========

class BatchimportTest(DBTestBase):
	
	def testAddBatchimport(self):
		"""creating a Batchimport must add a row in batchimports table."""
		Batchimport.CreateIfMissing(self.store, TEST.fixture(u'dekstop.de_weblog_index.xml'))
		
		result = self.store.execute('select count(*) from batchimports')
		count = result.get_one()[0]
		self.assertEquals(1, count, 'table "batchimports" has %d entries, when 1 is expected' % (count))
		
		b = Batchimport.FindByUrl(self.store, TEST.fixture(u'dekstop.de_weblog_index.xml'))
		self.assertNotEquals(None, b)
		self.assertNotEquals(None, b.url)
		self.assertNotEquals(None, b.date_added)
		self.assertEquals(None, b.date_last_fetched)
		self.assertEquals(0, b.fail_count)
		self.assertEquals(False, b.imported)
		
	def testSuccessfulBatchimport(self):
		"""successful batchimport must update row in batchimports, and add a row to feeds."""
		b = Batchimport.CreateIfMissing(self.store, TEST.fixture(u'dekstop.de_weblog_index.xml'))
		b.import_feed(self.store)

		b = Batchimport.FindByUrl(self.store, TEST.fixture(u'dekstop.de_weblog_index.xml'))
		self.assertNotEquals(None, b)
		self.assertNotEquals(None, b.url)
		self.assertNotEquals(None, b.date_added)
		self.assertNotEquals(None, b.date_last_fetched)
		self.assertEquals(0, b.fail_count)
		self.assertEquals(True, b.imported)

		result = self.store.execute('select count(*) from feeds')
		count = result.get_one()[0]
		self.assertEquals(1, count, 'table "feeds" has %d entries, when 1 is expected' % (count))

		feed = Feed.Load(self.store, TEST.fixture(u'dekstop.de_weblog_index.xml'))
		self.assertNotEquals(None, feed)
		self.assertEquals(u'dekstop weblog', feed.title)
	
	def testFailedBatchimport(self):
		"""failed batchimport must update fail counter in batchimports, and not add a row to feeds."""
		b = Batchimport.CreateIfMissing(self.store, TEST.fixture(u'broken_encoding.xml'))
		try:
			b.import_feed(self.store) # this is expected to throw an exception
			self.assertTrue(False)
		except:
			pass

		b = Batchimport.FindByUrl(self.store, TEST.fixture(u'broken_encoding.xml'))
		self.assertNotEquals(None, b)
		self.assertNotEquals(None, b.date_last_fetched)
		self.assertEquals(1, b.fail_count)
		self.assertEquals(False, b.imported)

		result = self.store.execute('select count(*) from feeds')
		count = result.get_one()[0]
		self.assertEquals(0, count, 'table "feeds" has %d entries, when 0 is expected' % (count))

import datetime
import unittest

import storm.locals

from feedcache.models.conf import Conf

import conf as TEST
from base import *

# =========
# = tests =
# =========

class ConfTest(DBTestBase):
	
	def testDefaultValueNone(self):
		"""Ensures that the default value is None, even after repeated calls to Get()"""
		# property hasn't been set yet
		self.assertEquals(None, Conf.Get(self.store, u'testProperty'))
		# first call to Get() resulted in storing the default value
		self.assertEquals(None, Conf.Get(self.store, u'testProperty'))
		# same call, but now while providing a default value
		self.assertEquals(None, Conf.Get(self.store, u'testProperty', None))
	
	def testStringProperty(self):
		# set
		Conf.Set(self.store, u'stringProperty', u'abc')
		# read
		self.assertEquals(u'abc', Conf.Get(self.store, u'stringProperty'))
		# delete
		Conf.Set(self.store, u'stringProperty', None)
		# assert it's deleted
		self.assertEquals(None, Conf.Get(self.store, u'stringProperty'))
		# test default value
		self.assertEquals(u'def', Conf.Get(self.store, u'stringProperty2', 'def'))
	
	def testIntProperty(self):
		# set
		Conf.SetInt(self.store, u'intProperty', 123123)
		# read
		self.assertEquals(123123, Conf.GetInt(self.store, u'intProperty'))
		# delete
		Conf.SetInt(self.store, u'intProperty', None)
		# assert it's deleted
		self.assertEquals(None, Conf.GetInt(self.store, u'intProperty'))
		# test default value
		self.assertEquals(-1, Conf.GetInt(self.store, u'intProperty2', -1))
	
	def testLongProperty(self):
		# set
		Conf.SetLong(self.store, u'longProperty', 5634)
		# read
		self.assertEquals(5634, Conf.GetLong(self.store, u'longProperty'))
		# delete
		Conf.SetLong(self.store, u'longProperty', None)
		# assert it's deleted
		self.assertEquals(None, Conf.GetLong(self.store, u'longProperty'))
		# test default value
		self.assertEquals(-13, Conf.GetLong(self.store, u'intProperty2', -13))

	def testDateTimeProperty(self):
		# Note: Conf only supports precision of seconds
		date = datetime.datetime(2009, 01, 01, 12, 00, 00, 0000)
		
		# set
		Conf.SetDateTime(self.store, u'datetimeProperty', date)
		# read
		self.assertEquals(date, Conf.GetDateTime(self.store, u'datetimeProperty'))
		# delete
		Conf.SetDateTime(self.store, u'datetimeProperty', None)
		# assert it's deleted
		self.assertEquals(None, Conf.GetDateTime(self.store, u'datetimeProperty'))

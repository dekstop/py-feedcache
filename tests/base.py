import unittest

import storm.locals

import conf as TEST

__all__ = [
	'TestBase', 'DBTestBase'
]


class TestBase(unittest.TestCase):
	pass

class DBTestBase(TestBase):
	"""
	Relies on properties defined in the conf module.
	Subclasses have a 'store' property to access the db.
	"""
	store = None
	
	def setUp(self):
		"""
		Establishes a new db connection and truncates all tables.
		"""
		if DBTestBase.store==None:
			db = storm.database.create_database(TEST.dsn())
			DBTestBase.store = storm.store.Store(db)
		for tablename in TEST.tables():
			#print 'Truncating %s' % tablename
			self.store.execute('truncate ' + tablename)
		# make sure we can safely rollback on error in the next test without undoing the truncations:
		self.store.commit()
	
	def tearDown(self):
		# we're not actually interested in rolling back -- but for some reason storm
		# hangs between first and second test unless we commit or rollback between tests.
		#self.store.rollback()
		#self.store.close
		pass


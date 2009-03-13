#!/usr/bin/env python
#
# queues.py
#
# Queue classes with an implicit locking mechanism (transparent to clients):
# they act as generators of Feed or Batchimport instances, but lock each
# item before yielding it, and unlock it when the yield returns.
#
# martind 2008-12-01, 17:42:04
#

import datetime
import time

import psycopg2.extensions
import storm.locals

from feedcache.models.feeds import Batchimport, Feed
import feedcache.util as util

__all__ = [
	'BatchimportQueue', 'FeedQueue'
]

# ===========
# = helpers =
# ===========

def _expr_retry_timeout_expired(entity_type, retry_timeout):
	"""
	Storm query expression: entities where either the last request hasn't failed,
	or that have failed and are due for a retry.
	
	Parameters:
	entity_type:
		the entity type to match against (either Batchimport, or Feed)
	retry_timeout:
		a datetime.timedelta, time before retrying a failed fetch
	"""
	return storm.expr.Or(
		# hasn't failed
		entity_type.fail_count == 0,
		# OR last request has failed, but happened before retry_timeout
		storm.expr.And(
			entity_type.fail_count > 0,
			entity_type.date_last_fetched < (util.now() - retry_timeout),
		)
	)

def _expr_not_locked(entity_type, lock_timeout):
	"""
	Storm query expression: entities that either aren't locked, or where the lock
	has expired.
	
	Parameters:
	entity_type:
		the entity type to match against (either Batchimport, or Feed)
	lock_timeout:
		a datetime.timedelta, time before an acquired lock expires
	"""
	return storm.expr.Or(
		# is not locked
		entity_type.semaphore == None,
		# OR is locked, but lock has timed out
		entity_type.date_locked < (util.now() - lock_timeout)
	)


# ===========
# = classes =
# ===========

class EntityQueue(object):
	"""
	Base class for all queues.
	"""
	
	entity_type = None # class variable, contains a reference to either Batchimport or Feed
	
	def __init__(self, semaphore,
		lock_timeout=datetime.timedelta(hours=6), 
		update_timeout=datetime.timedelta(minutes=30),
		retry_timeout=datetime.timedelta(hours=1)):
		
		self.semaphore = semaphore
		self.lock_timeout = lock_timeout
		self.update_timeout = update_timeout
		self.retry_timeout = retry_timeout
		self.cutoff_time = None
		self.stats = dict()
	
	def log(self, message):
		"""
		Logger for debug messages.
		"""
		print "%s %s %s" % (
			self.semaphore and self.semaphore.id, # self.semaphore may be None
			util.now().isoformat(), 
			message)
	
	def inc(self, key, n=1):
		"""
		Helper to increment entries in the 'stats' dict. 
		We can't use a defaultdict because pp apparently  can't pickle those,
		hence this function to reduce code verbosity.
		"""
		if self.stats.has_key(key):
			self.stats[key] += n
		else:
			self.stats[key] = n
	
	def _acquire_locks(self, store, num_items=1, lock_retries=3, lock_retry_delay_in_seconds=5):
		"""
		Attempts to lock num_items items, returns them in a list.
		If this returns None then item locking failed more than lock_retries times.
		If this returns an empty list then there are no more items to process.
		"""
		try:
			self.log('Acquiring lock on %s...' % self.__class__.entity_type.__name__)
			store.execute(storm.expr.Update({
					self.__class__.entity_type.semaphore_id: self.semaphore.id, 
					self.__class__.entity_type.date_locked: util.now()
				}, 
				self.__class__.entity_type.id.is_in(
					storm.expr.Select(
						[self.__class__.entity_type.id],
						self._expr_available_items(store),
						self.__class__.entity_type,
						limit=num_items
					)
				),
				self.__class__.entity_type))
			store.commit()
			
			return store.find(self.__class__.entity_type, self.__class__.entity_type.semaphore == self.semaphore)
			
		except psycopg2.extensions.TransactionRollbackError, e:
			# Another worker acquired a lock on the same item before we could; -> retry
			# http://www.postgresql.org/docs/8.1/static/transaction-iso.html
			# https://bugs.launchpad.net/storm/+bug/149335
			store.rollback()
			if lock_retries>0:
				time.sleep(lock_retry_delay_in_seconds) # to avoid lock contention
				self.inc('num_lock_retries')
				self.log('%s, retrying...' % str(e).strip())
				return self._acquire_locks(store, num_items, lock_retries-1, lock_retry_delay_in_seconds*2)
			else:
				self.inc('num_lock_failures')
				self.log('%s, giving up.' % str(e).strip())
				return None
		except storm.exceptions.IntegrityError, e:
			# Violated unique constraint: another worker has already acquired the lock.
			# If this happens we failed at making Storm do an atomic INSERT .. SELECT
			raise
		
	def _release_lock(self, store, item):
		"""
		Releases the lock for a single item.
		"""
		self.log('unlocking %s with id %d' % (self.__class__.entity_type.__name__, item.id))
		store.execute(storm.expr.Update({
				self.__class__.entity_type.semaphore_id: None, 
				self.__class__.entity_type.date_locked: None
			}, 
			storm.expr.And(
				self.__class__.entity_type.id == item.id,
				self.__class__.entity_type.semaphore_id == self.semaphore.id
			), 
			self.__class__.entity_type))
		store.commit()
	
	def next(self, store, num_items=1):
		"""
		Returns a generator that acts as an iterator of entities, but that
		transparently takes care of locking entities before they're yielded,
		and releasing them afterwards.
		If this returns an empty list then there are no more items to process.
		"""
		if self.cutoff_time==None:
			# ignore entries that get added during this session
			self.cutoff_time = util.now()
		items = self._acquire_locks(store, num_items)
		if items:
			for item in items:
				self.log('Processing %s with id %d' % (self.__class__.entity_type.__name__, item.id))
				yield item
				self._release_lock(store, item)
		else:
			pass # no lock acquired -> yield nothing
			
	def _expr_available_items(self, store):
		"""
		A storm expression that selects items to process next.
		"""
		raise NotImplementedError("This method needs to be implemented in subclasses.")

class BatchimportQueue(EntityQueue):
	
	entity_type = Batchimport
	
	def _expr_available_items(self, store):
		"""
		Storm query expression: find Batchimport entries that are ready for importing.
		"""
		return storm.expr.And(
			# added before cutoff_time
			Batchimport.date_added < self.cutoff_time,
			# AND not marked as inactive
			Batchimport.active == True, 
			# AND not imported yet
			Batchimport.imported == False, 
			# AND last fetch hasn't failed, or due for failure retry
			_expr_retry_timeout_expired(Batchimport, self.retry_timeout),
			# AND not locked, or lock expired
			_expr_not_locked(Batchimport, self.lock_timeout)
		)

class FeedQueue(EntityQueue):
	
	entity_type = Feed
	
	def _expr_available_items(self, store):
		"""
		Storm query expression: find Feed entries that are ready for updating.
		"""
		return storm.expr.And(
			# last updated before cutoff_time-update_timeout
			Feed.date_last_fetched < self.cutoff_time - self.update_timeout,
			# AND not marked as inactive
			Feed.active == True, 
			# AND last fetch hasn't failed, or due for failure retry
			_expr_retry_timeout_expired(Feed, self.retry_timeout),
			# AND not locked, or lock expired
			_expr_not_locked(Feed, self.lock_timeout)
		)	

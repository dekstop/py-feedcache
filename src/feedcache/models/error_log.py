# error_log.py
#
# ...
#
# martind 2008-11-01, 11:17:11
#

import sys
import traceback

import storm.locals as storm

from feedcache.models.feeds import Batchimport, Feed
from feedcache.exceptions import FeedcacheError

__all__ = [
	'ErrorType', 'BatchimportErrorLog', 'FeedErrorLog'
]

# ===========
# = helpers =
# ===========

def get_instance(store, error_class, error_object, exception):
	'''
	error_class is one of BatchimportErrorLog, FeedErrorLog
	error_object is either a Batchimport or Feed instance
	exception is of type FeedcacheError, or any other exception
	
	returns an instance of the class specified with error_class
	'''
	if isinstance(exception, FeedcacheError):
		return error_class(
			error_object,
			ErrorType.FindOrCreate(store, unicode(exception.get_error_type())),
			unicode(exception.get_message()),
			unicode(exception.get_payload()))
	# FIXME: this code will break if not called from within an exception handler
	tb = traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2])
	msg = tb.pop()
	stacktrace = '%r : %s\n%s' % (type(exception), msg, '\n'.join(tb))
	
	return error_class(
		error_object,
		ErrorType.FindOrCreate(store, unicode(exception.__class__.__name__)),
		unicode(str(exception)),
		unicode(stacktrace)
	)
	

# ===========
# = classes =
# ===========

class ErrorType(object):
	__storm_table__ = 'error_types'
	id = storm.Int(primary=True)
	
	name = storm.Unicode()
	description = storm.Unicode()
	
	def __init__(self, name, description):
		self.name = name
		self.description = description

	def FindByName(store, name):
		return store.find(ErrorType, ErrorType.name==name).one()

	def FindOrCreate(store, name):
		error_type = ErrorType.FindByName(store, name)
		if (error_type==None):
			error_type = ErrorType(name, u'(Auto-inserted error type)')
			store.add(error_type)
			store.flush()
		return error_type
	
	FindByName = staticmethod(FindByName)
	FindOrCreate = staticmethod(FindOrCreate)


class BatchimportErrorLog(object):
	__storm_table__ = 'batchimports_errors'
	id = storm.Int(primary=True)

	batchimport_id = storm.Int()
	batchimport = storm.Reference(batchimport_id, Batchimport.id)
	error_type_id = storm.Int()
	error_type = storm.Reference(error_type_id, ErrorType.id)
	message = storm.Unicode()
	payload = storm.Unicode()
	
	def __init__(self, batchimport, error_type, message, payload):
		self.batchimport = batchimport
		self.error_type = error_type
		self.message = message
		self.payload = payload
	
	def __str__(self):
		return '%s: {error_type: "%s", url: "%s", message: "%s", payload: "%s"}' % (
			type(self).__name__,
			self.error_type.name, 
			self.batchimport.feed_url, 
			self.message, 
			self.payload)

	def FromException(store, batchimport, e):
		return get_instance(store, BatchimportErrorLog, batchimport, e)
	
	FromException = staticmethod(FromException)

class FeedErrorLog(object):
	__storm_table__ = 'feeds_errors'
	id = storm.Int(primary=True)

	feed_id = storm.Int()
	feed = storm.Reference(feed_id, Feed.id)
	error_type_id = storm.Int()
	error_type = storm.Reference(error_type_id, ErrorType.id)
	message = storm.Unicode()
	payload = storm.Unicode()
	
	def __init__(self, feed, error_type, message, payload):
		self.feed = feed
		self.error_type = error_type
		self.message = message
		self.payload = payload
	
	def __str__(self):
		return '%s: {error_type: "%s", url: "%s", message: "%s", payload: "%s"}' % (
			type(self).__name__,
			self.error_type.name, 
			self.feed.initial_url, 
			self.message, 
			self.payload)

	def FromException(store, feed, e):
		return get_instance(store, FeedErrorLog, feed, e)

	FromException = staticmethod(FromException)


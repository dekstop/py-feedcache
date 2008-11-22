# messages.py
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
	'MessageType', 'Message', 'BatchimportMessage', 'FeedMessage'
]

# ===========
# = helpers =
# ===========

def _get_instance(store, message_class, message_object, exception):
	'''
	message_class is one of BatchimportMessage, FeedMessage
	message_object is either a Batchimport or Feed instance
	exception is of type FeedcacheError, or any other exception
	
	returns an instance of the class specified with message_class
	'''
	if isinstance(exception, FeedcacheError):
		return message_class(
			message_object,
			MessageType.FindOrCreate(store, unicode(exception.get_message_type())),
			unicode(exception.get_message()),
			unicode(exception.get_payload()))
	# FIXME: this code will break if not called from within an exception handler
	tb = traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2])
	msg = tb.pop()
	stacktrace = '%r : %s\n%s' % (type(exception), msg, '\n'.join(tb))
	
	return message_class(
		message_object,
		MessageType.FindOrCreate(store, unicode(exception.__class__.__name__)),
		unicode(str(exception)),
		unicode(stacktrace)
	)
	

# ===========
# = classes =
# ===========

class MessageType(object):
	__storm_table__ = 'message_types'
	id = storm.Int(primary=True)
	
	name = storm.Unicode()
	description = storm.Unicode()
	
	def __init__(self, name, description):
		self.name = name
		self.description = description

	def FindByName(store, name):
		return store.find(MessageType, MessageType.name==name).one()

	def FindOrCreate(store, name):
		message_type = MessageType.FindByName(store, name)
		if (message_type==None):
			message_type = MessageType(name, u'(Auto-inserted message type)')
			store.add(message_type)
			store.flush()
		return message_type
	
	FindByName = staticmethod(FindByName)
	FindOrCreate = staticmethod(FindOrCreate)

class Message(object):
	__storm_table__ = 'messages'
	id = storm.Int(primary=True)

	message_type_id = storm.Int()
	message_type = storm.Reference(message_type_id, MessageType.id)
	message = storm.Unicode()
	payload = storm.Unicode()
	
	def __init__(self, message_type, message, payload):
		self.message_type = message_type
		self.message = message
		self.payload = payload

class BatchimportMessage(object):
	__storm_table__ = 'batchimports_messages'
	id = storm.Int(primary=True)
	
	batchimport_id = storm.Int()
	batchimport = storm.Reference(batchimport_id, Batchimport.id)
	message_id = storm.Int()
	message = storm.Reference(message_id, Message.id)
	
	def __init__(self, batchimport, message_type, message, payload):
		self.batchimport = batchimport
		self.message = Message(message_type, message, payload)
	
	def __str__(self):
		return '%s: {message_type: "%s", url: "%s", message: "%s", payload: "%s"}' % (
			type(self).__name__,
			self.message.message_type.name, 
			self.batchimport.url, 
			self.message.message, 
			self.message.payload)

	def FromException(store, batchimport, e):
		return _get_instance(store, BatchimportMessage, batchimport, e)
	
	FromException = staticmethod(FromException)

class FeedMessage(object):
	__storm_table__ = 'feeds_messages'
	id = storm.Int(primary=True)

	feed_id = storm.Int()
	feed = storm.Reference(feed_id, Feed.id)
	message_id = storm.Int()
	message = storm.Reference(message_id, Message.id)
	
	def __init__(self, feed, message_type, message, payload):
		self.feed = feed
		self.message = Message(message_type, message, payload)
	
	def __str__(self):
		return '%s: {message_type: "%s", url: "%s", message: "%s", payload: "%s"}' % (
			type(self).__name__,
			self.message.message_type.name, 
			self.feed.url, 
			self.message.message, 
			self.message.payload)

	def FromException(store, feed, e):
		return _get_instance(store, FeedMessage, feed, e)

	FromException = staticmethod(FromException)


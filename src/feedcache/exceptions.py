# exceptions.py
#
# ...
#
# martind 2008-11-01, 11:17:11
#

__all__ = [
	'FeedFetchError', 'FeedParseError'
]


class FeedcacheError(Exception):
	"""
	The get_message_type(), get_message() and get_payload() functions are used to
	log subclasses of these exceptions to the messages table.
	"""
	def __init__(self, url, document, message, cause=None):
		"""
		The 'cause' property can carry an exception.
		"""
		self.url = url
		self.document = document
		self.message = message
		self.cause = cause
	
	def __str__(self):
		if self.cause!=None:
			return "%s: %s (caused by %s)" % (self.message, self.url, self.cause)
		else:
			return "%s: %s" % (self.message, self.url)
	
	def get_message_type(self):
		return self.__class__.__name__
	
	def get_message(self):
		return str(self)
		
	def get_payload(self):
		return self.document

class FeedFetchError(FeedcacheError):
	pass
	
class FeedParseError(FeedcacheError):
	pass


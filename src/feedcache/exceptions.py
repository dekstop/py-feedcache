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
	The get_error_type(), get_message() and get_payload() functions are used to
	log subclasses of these exceptions to error tables.
	"""
	def __init__(self, feed_url, document, message, cause=None):
		"""
		The 'cause' property can carry an exception.
		"""
		self.feed_url = feed_url
		self.document = document
		self.message = message
		self.cause = cause
	
	def __str__(self):
		if self.cause!=None:
			return "%s: %s (caused by %s)" % (self.message, self.feed_url, self.cause)
		else:
			return "%s: %s" % (self.message, self.feed_url)
	
	def get_error_type(self):
		return self.__class__.__name__
	
	def get_message(self):
		return str(self)
		
	def get_payload(self):
		return self.document

class FeedFetchError(FeedcacheError):
	pass
	
class FeedParseError(FeedcacheError):
	pass


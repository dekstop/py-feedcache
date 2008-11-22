# util.py
#
# Misc static helpers.
#
# martind 2008-11-22, 16:12:53
#

import datetime
import hashlib
import time

__all__ = [
	'transcode', 'to_datetime', 'from_datetime', 'datetime_now',
	'generate_entry_uid'
]


def transcode(str):
	"""
	Preprocessing for every single text string we store. Returns valid Unicode (NOT UTF-8).
	"""
	return unicode(str)#.encode('utf-8')

def to_datetime(_9tuple):
	"""
	Takes a 9-tuple as generated by feedparser, converts it into a
	UTC timestamp (a floating point number as generated by time.mktime.)
	"""
	# FIXME: would love to have a UTC equivalent...
	return time.mktime(_9tuple)

def from_datetime(datetime):
	"""
	Takes a UTC timestamp (a datetime object)
	and converts it into a 9-tuple to be used by feedparser.
	"""
	if datetime==None:
		return None
	# FIXME: we're using localtime instead of gmtime since there's no UTC equivalent for mktime
	return datetime.utctimetuple()

def datetime_now():
	"""
	Creates a UTC timestamp.
	"""
	return datetime.datetime.utcnow()

def generate_entry_uid(*fields):
	"""
	TODO: stopgap measure. need to audit this.
	"""
	m = hashlib.sha1()
	for field in fields:
		if field!=None:
			m.update(field.encode('utf-8'))
	return u'generated:' + m.hexdigest()
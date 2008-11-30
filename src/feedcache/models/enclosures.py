# enclosures.py
#
# ...
#
# martind 2008-11-30, 14:40:08
#

import storm.locals as storm

from feedcache.models.feeds import Feed

__all__ = [
	'Enclosure', 'EntryEnclosure'
]

class Enclosure(object):
	__storm_table__ = 'enclosures'
	id = storm.Int(primary=True)
	
	feed_id = storm.Int()
	feed = storm.Reference(feed_id, Feed.id)
	url = storm.Unicode()
	length = storm.Int()
	type = storm.Unicode()
	
	def __init__(self, feed, url, length, type):
		self.feed = feed
		self.url = url
		self.length = length
		self.type = type
	
	def FindByProperties(store, feed, url, length=None, type=None):
		return store.find(Enclosure, Enclosure.feed==feed, Enclosure.url==url, 
			Enclosure.length==length, Enclosure.type==type).one()
	
	def FindOrCreate(store, feed, url, length=None, type=None):
		enclosure = Enclosure.FindByProperties(store, feed, url, length, type)
		if (enclosure==None):
			enclosure = Enclosure(feed, url, length, type)
			store.add(enclosure)
			store.flush()
		return enclosure
	
	FindByProperties = staticmethod(FindByProperties)
	FindOrCreate = staticmethod(FindOrCreate)

class EntryEnclosure(object):
	__storm_table__ = 'entries_enclosures'
	__storm_primary__ = 'entry_id', 'enclosure_id'
	
	entry_id = storm.Int()
	enclosure_id = storm.Int()

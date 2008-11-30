# authors.py
#
# ...
#
# martind 2008-11-01, 11:17:11
#

import storm.locals as storm

from feedcache.models.feeds import Feed

__all__ = [
	'Author', 'EntryAuthor'
]

class Author(object):
	__storm_table__ = 'authors'
	id = storm.Int(primary=True)
	
	feed_id = storm.Int()
	feed = storm.Reference(feed_id, Feed.id)
	name = storm.Unicode()
	email = storm.Unicode()
	link = storm.Unicode()
	
	def __init__(self, feed, name, email, link):
		self.feed = feed
		self.name = name
		self.email = email
		self.link = link
	
	def FindByProperties(store, feed, name, email=None, link=None):
		return store.find(Author, Author.feed==feed, Author.name==name, 
			Author.email==email, Author.link==link).one()
	
	def FindOrCreate(store, feed, name, email=None, link=None):
		author = Author.FindByProperties(store, feed, name, email, link)
		if (author==None):
			author = Author(feed, name, email, link)
			store.add(author)
			store.flush()
		return author
	
	FindByProperties = staticmethod(FindByProperties)
	FindOrCreate = staticmethod(FindOrCreate)

class EntryAuthor(object):
	__storm_table__ = 'entries_authors'
	__storm_primary__ = 'entry_id', 'author_id'
	
	entry_id = storm.Int()
	author_id = storm.Int()

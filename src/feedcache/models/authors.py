# authors.py
#
# ...
#
# martind 2008-11-01, 11:17:11
#

import storm.locals as storm

__all__ = [
	'Author', 'FeedAuthor', 'EntryAuthor'
]

class Author(object):
	__storm_table__ = 'authors'
	id = storm.Int(primary=True)
	
	name = storm.Unicode()
	email = storm.Unicode()
	link = storm.Unicode()
	
	def __init__(self, name, email, link):
		self.name = name
		self.email = email
		self.link = link
	
	def FindByProperties(store, name, email=None, link=None):
		return store.find(Author, Author.name==name, Author.email==email, Author.link==link).one()
	
	def FindOrCreate(store, name, email=None, link=None):
		author = Author.FindByProperties(store, name, email, link)
		if (author==None):
			author = Author(name, email, link)
			store.add(author)
			store.flush()
		return author
	
	FindByProperties = staticmethod(FindByProperties)
	FindOrCreate = staticmethod(FindOrCreate)

class FeedAuthor(object):
	__storm_table__ = 'feeds_authors'
	__storm_primary__ = 'feed_id', 'author_id'
	
	feed_id = storm.Int()
	author_id = storm.Int()

class EntryAuthor(object):
	__storm_table__ = 'entries_authors'
	__storm_primary__ = 'entry_id', 'author_id'
	
	entry_id = storm.Int()
	author_id = storm.Int()

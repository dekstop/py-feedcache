# categories.py
#
# ...
#
# martind 2008-11-01, 11:17:11
#

import storm.locals as storm

from feedcache.models.feeds import Feed

__all__ = [
	'Category', 'FeedCategory', 'EntryCategory'
]

class Category(object):
	__storm_table__ = 'categories'
	id = storm.Int(primary=True)
	
	feed_id = storm.Int()
	feed = storm.Reference(feed_id, Feed.id)
	term = storm.Unicode()
	scheme = storm.Unicode()
	label = storm.Unicode()
	
	def __init__(self, feed, term, scheme, label):
		self.feed = feed
		self.term = term
		self.scheme = scheme
		self.label = label
	
	def FindByProperties(store, feed, term, scheme=None, label=None):
		return store.find(Category, Category.feed==feed, Category.term==term, 
			Category.scheme==scheme, Category.label==label).one()
	
	def FindOrCreate(store, feed, term, scheme=None, label=None):
		category = Category.FindByProperties(store, feed, term, scheme, label)
		if (category==None):
			category = Category(feed, term, scheme, label)
			store.add(category)
			store.flush()
		return category
	
	FindByProperties = staticmethod(FindByProperties)
	FindOrCreate = staticmethod(FindOrCreate)

class EntryCategory(object):
	__storm_table__ = 'entries_categories'
	__storm_primary__ = 'entry_id', 'category_id'
	
	entry_id = storm.Int()
	category_id = storm.Int()

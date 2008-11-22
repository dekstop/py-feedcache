# categories.py
#
# ...
#
# martind 2008-11-01, 11:17:11
#

import storm.locals as storm

__all__ = [
	'Category', 'FeedCategory', 'EntryCategory'
]

class Category(object):
	__storm_table__ = 'categories'
	id = storm.Int(primary=True)
	
	term = storm.Unicode()
	scheme = storm.Unicode()
	label = storm.Unicode()
	
	def __init__(self, term, scheme, label):
		self.term = term
		self.scheme = scheme
		self.label = label
	
	def FindByProperties(store, term, scheme=None, label=None):
		return store.find(Category, Category.term==term, Category.scheme==scheme, Category.label==label).one()
	
	def FindOrCreate(store, term, scheme=None, label=None):
		category = Category.FindByProperties(store, term, scheme, label)
		if (category==None):
			category = Category(term, scheme, label)
			store.add(category)
			store.flush()
		return category
	
	FindByProperties = staticmethod(FindByProperties)
	FindOrCreate = staticmethod(FindOrCreate)

class FeedCategory(object):
	__storm_table__ = 'feeds_categories'
	__storm_primary__ = 'feed_id', 'category_id'
	
	feed_id = storm.Int()
	category_id = storm.Int()

class EntryCategory(object):
	__storm_table__ = 'entries_categories'
	__storm_primary__ = 'entry_id', 'category_id'
	
	entry_id = storm.Int()
	category_id = storm.Int()

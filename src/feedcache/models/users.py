# users.py
#
# ...
#
# martind 2008-12-07, 11:31:38
#

import storm.locals as storm

from feedcache.models.feeds import Feed

__all__ = [
	'User', 'UserFeed'
]

class User(object):
	__storm_table__ = 'users'
	id = storm.Int(primary=True)
	
	name = storm.Unicode()
	password = storm.Unicode()
	email = storm.Unicode()
	type = storm.RawStr()
	
	def __init__(self, name, password, email, type):
		self.name = name
		self.password = password
		self.email = email
		self.type = type
	
	def FindByName(store, name):
		return store.find(User, User.name==name).one()
	
	FindByName = staticmethod(FindByName)

class UserFeed(object):
	__storm_table__ = 'users_feeds'
	__storm_primary__ = 'user_id', 'feed_id'
	
	user_id = storm.Int()
	feed_id = storm.Int()

# ==============
# = References =
# ==============

User.feeds = storm.ReferenceSet(User.id, UserFeed.user_id, UserFeed.feed_id, Feed.id)

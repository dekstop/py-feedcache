# semaphores.py
#
# ...
#
# martind isodate
#

# import base64
# import datetime
# import hashlib
import uuid

import storm.locals as storm

#from feedcache.models.feeds import Batchimport, Feed

__all__ = [
	'Semaphore'
]

def generate_guid():
	#base64.b32encode(hashlib.sha1(str(datetime.datetime.now())).digest())
	#base64.urlsafe_b64encode(hashlib.sha1(str(datetime.datetime.now())).digest())
	#return unicode(uuid.uuid1()) # classic UUID, based on MAC address and timestamp
	return unicode(uuid.uuid4()) # random UUID

class Semaphore(object):
	__storm_table__ = 'semaphores'
	id = storm.Int(primary=True)
	
	date_created = storm.DateTime()
	guid = storm.Unicode()

	shutdown_requested = storm.Bool()
	
	def __init__(self):
		self.guid = generate_guid()
	
	def __str__(self):
		return 'semaphore{id: %d, guid: %s}' % (self.id, self.guid)
	
	
# ==============
# = references =
# ==============

# many-to-many
#Semaphore.batchimports = storm.ReferenceSet(Semaphore.id, Batchimport.semaphore_id)
#Semaphore.feeds = storm.ReferenceSet(Semaphore.id, Feed.semaphore_id)

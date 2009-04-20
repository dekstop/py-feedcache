# authors.py
#
# ...
#
# martind 2009-04-19, 15:34:27
#

import datetime

import storm.locals as storm

__all__ = [
	'Conf'
]

DATE_FORMAT = '%Y-%m-%dT%H:%M:%S+0000'

class Conf(object):
	__storm_table__ = 'conf'
	id = storm.Int(primary=True)
	
	key = storm.Unicode()
	value = storm.Unicode()
	
	def __init__(self, key, value):
		self.key = key
		self.value = value
	
	def FindByKey(store, key):
		"""Returns a Conf instance, or None"""
		return store.find(Conf, Conf.key==key).one()
	
	def FindOrCreate(store, key, defaultValue):
		"""Returns a Conf instance"""
		conf = Conf.FindByKey(store, key)
		if (conf==None):
			conf = Conf(key, defaultValue)
			store.add(conf)
			store.flush()
		return conf
	
	def Delete(store, key):
		conf = Conf.FindByKey(store, key)
		if conf:
			store.remove(conf)
			store.flush()
	
	def Get(store, key, defaultValue=None):
		"""Returns the current value, or defaultValue"""
		conf = Conf.FindByKey(store, key)
		if conf:
			return conf.value
		return defaultValue
	
	def Set(store, key, value):
		"""Returns the new value. The entry gets deleted if value==None."""
		if value==None:
			Conf.Delete(store, key)
			return None
		conf = Conf.FindOrCreate(store, key, value)
		if conf.value!=value:
			conf.value = value
			store.flush()
		return conf.value
	
	def GetInt(store, key, defaultValue=None):
		"""Returns the current value, or defaultValue if there is no current value or 
		the current value cannot be converted to an int."""
		try:
			conf = Conf.FindByKey(store, key)
			if conf:
				return int(conf.value)
			return defaultValue
		except ValueError:
			return defaultValue
	
	def SetInt(store, key, value):
		"""Returns the new value. The entry gets deleted if value==None."""
		if value==None:
			Conf.Delete(store, key)
			return None
		return Conf.Set(store, key, unicode(value))
	
	def GetLong(store, key, defaultValue=None):
		"""Returns the current value, or defaultValue if there is no current value or 
		the current value cannot be converted to a long."""
		try:
			conf = Conf.FindByKey(store, key)
			if conf:
				return long(conf.value)
			return defaultValue
		except ValueError:
			return defaultValue

	def SetLong(store, key, value):
		"""Returns the new value. The entry gets deleted if value==None."""
		if value==None:
			Conf.Delete(store, key)
			return None
		return Conf.Set(store, key, unicode(value))
	
	def GetDateTime(store, key, defaultValue=None):
		"""Returns the current value, or defaultValue if there is no current value or 
		the current value cannot be parsed to a datetime."""
		try:
			conf = Conf.FindByKey(store, key)
			if conf:
				return datetime.datetime.strptime(conf.value, DATE_FORMAT)
			return defaultValue
		except ValueError:
			return defaultValue

	def SetDateTime(store, key, value):
		"""Returns the new value. The entry gets deleted if value==None.
		Note that we only store at precision of seconds, cf http://bugs.python.org/issue1982"""
		if value==None:
			Conf.Delete(store, key)
			return None
		return Conf.Set(store, key, unicode(value.strftime(DATE_FORMAT)))
	
	FindByKey = staticmethod(FindByKey)
	FindOrCreate = staticmethod(FindOrCreate)

	Delete = staticmethod(Delete)
	Get = staticmethod(Get)
	Set = staticmethod(Set)

	GetInt = staticmethod(GetInt)
	SetInt = staticmethod(SetInt)
	GetLong = staticmethod(GetLong)
	SetLong = staticmethod(SetLong)
	GetDateTime = staticmethod(GetDateTime)
	SetDateTime = staticmethod(SetDateTime)

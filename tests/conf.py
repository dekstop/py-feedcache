"""
Has static properties that are used to configure subclasses:
- FIXTURES_PATH: a local path to fixtures (files with test data)
- DSN: a DB connection URI (a string)
- TABLES: a list of table names, these tables will be truncated before every test
"""
import unittest

import storm.locals

__all__ = [
	'TestBase', 'DBTestBase',
	'FIXTURES_ROOT', 'DSN', 'TABLES',
	'fixture', 'get_dsn', 'get_tables'
]


FIXTURES_ROOT = u'data/fixtures/'
WEBROOT = u'data/fixtures/'
HTTP_FIXTURES_ROOT = u'http://127.0.0.1/'

# Connection URI
DSN = u'postgres://postgres:@localhost/feedcache_test'

# These will be truncated between tests, which is used for e.g.
# transaction rollback testing:
TABLES = [
	'batchimports', 'feeds', 'entries', 
	'messages', 'batchimports_messages', 'feeds_messages',
	'authors', 'feeds_authors', 'entries_authors', 
	'categories', 'feeds_categories', 'entries_categories',
	'semaphores'
]


def fixture(filename):
	return FIXTURES_ROOT + filename

def http_fixture(filename):
	return HTTP_FIXTURES_ROOT + filename

def dsn():
	return DSN

def tables():
	return TABLES

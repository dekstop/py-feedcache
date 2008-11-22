import BaseHTTPServer
import httplib as HTTP
import re
import unittest
from threading import *

import storm.locals

from feedcache.models.feeds import Feed, Entry
import feedcache.exceptions

import conf as TEST
from base import *

# ========
# = conf =
# ========

PORT = 8123

LAST_MODIFIED_VALUE = 'Sat, 20 Nov 2004 20:16:24 GMT'
ETAG_VALUE = '"15a4a-94-3e9564c23b600"'

def get_port():
	"""
	Every test runs its own server. To allow the TCP stack enough time to
	close each session we run each test on a separate port.
	TODO: figure out why TCPServer.allow_reuse_address = True seems to have no effect
	"""
	global PORT
	PORT = PORT + 1
	TEST.HTTP_FIXTURES_ROOT = u'http://127.0.0.1:%d/' % PORT
	return PORT

# ===========
# = helpers =
# ===========

class FeedcacheTestHTTPHandler(BaseHTTPServer.BaseHTTPRequestHandler):
	"""
	Only implements GET. Returns different results based on the first path element 
	of the requested resource:
	- a /fixture/ prefix serves files from TEST.WEBROOT (sending fake last-modified and 
	  etag headers for status 304 tests.)
	- a /301/ and /302/ prefix will redirect to a fixture of the same name
	- a /404/ prefix will always returns HTTP status 404 (the same is true for
	  other numbers too.)
	"""	
	request_header = dict()
	
	def log_message(self, format, *args):
		"""Overrides BaseHTTPRequestHandler.log_message to suppress all logging"""
		pass
		
	def header(self, status, headers=dict()):
		self.send_response(status)
		# self.send_header("Content-Type", "text/html")
		# self.send_header('Connection', 'close')
		for k,v in headers.items():
			self.send_header(k, v)
		self.end_headers()
	
	def defaultpage(self, status, headers=dict()):
		self.header(status, headers)
		if self.command != 'HEAD' and status >= 200 and status not in (204, 304):
			self.wfile.write('<html><head><title>HTTP Status %d</title></head>' % status)
			self.wfile.write('<body><h1>HTTP Status %d: %s</h1></body>' % (status, HTTP.responses[status]))
			self.wfile.write('<pre>')
			for k,v in headers.items():
				self.wfile.write('%s: %s' % (k, v))
				self.wfile.write('</pre></body>')
	
	def redirect(self, status, resource):
		self.defaultpage(status, {'Location': resource})
	
	def serve_file(self, resource):
		try:
			if self.headers.get('If-None-Match')==ETAG_VALUE or self.headers.get('If-Modified-Since')==LAST_MODIFIED_VALUE:
				self.header(304)
				return
			
			FILE = open(TEST.WEBROOT + resource,'r')
			self.header(200, {
				'Last-Modified': LAST_MODIFIED_VALUE,
				'ETag': ETAG_VALUE
			})
			if self.command != 'HEAD':
				self.wfile.write(FILE.read())
			FILE.close()
		except IOError,e:
			self.defaultpage(404)
	
	def do_HEAD(self):
		do_GET()

	def do_GET(self):
		FeedcacheTestHTTPHandler.request_header['If-None-Match'] = self.headers.get('If-None-Match')
		FeedcacheTestHTTPHandler.request_header['If-Modified-Since'] = self.headers.get('If-Modified-Since')
		
		p = re.compile('^/([^/]+)/(.+)$')
		m = p.match(self.path)
		if m:
			action = m.group(1)
			path = m.group(2)
			if action==u'fixture':
				self.serve_file(path)
				#, {'Content-type': 'text/html'})
			elif action==u'301' or action==u'302' or action==u'307':
				self.redirect(int(action), '/fixture/%s' % path)
			else:
				try:
					self.defaultpage(int(action))
				except ValueError:
					self.defaultpage(400)
		else:
			self.defaultpage(200)

class FeedcacheTestHTTPServer(BaseHTTPServer.HTTPServer):
	allow_reuse_address = True

class FeedcacheTestServer(Thread):
	"""
	HTTP Server that runs in a thread and handles a predetermined number of requests.
	Based on code in Mark Pilgrim's Feedparser tests.
	"""

	def __init__(self, port, requests):
		Thread.__init__(self)
		self.port = port
		self.requests = requests
		self.ready = 0

	def run(self):
		self.httpd = FeedcacheTestHTTPServer(('', self.port), FeedcacheTestHTTPHandler)
		self.ready = 1
		while self.requests:
			self.httpd.handle_request()
			self.requests -= 1
		self.httpd.server_close()

# =========
# = tests =
# =========

class BasicHTTPTest(DBTestBase):

	def testHTTPRequest(self):
		"""fetches a new (uncached) feed and verifies some fields."""
		FeedcacheTestServer(get_port(), 1).start()
	
		feed = Feed.Load(self.store, TEST.http_fixture(u'fixture/dekstop.de_weblog_index.xml'))
		
		self.assertEquals(u'dekstop weblog', feed.title)
		self.assertEquals(u'http://dekstop.de/weblog/', feed.link)
		self.assertEquals(15, feed.entries.count())

class RedirectTest(DBTestBase):
	
	def testHTTP301Request(self):
		"""must follow HTTP 301 redirects"""
		FeedcacheTestServer(get_port(), 2).start()
		feed = Feed.Load(self.store, TEST.http_fixture(u'301/dekstop.de_weblog_index.xml'))
		self.assertEquals(u'dekstop weblog', feed.title)
	
	def testHTTP302Request(self):
		"""must follow HTTP 302 redirects"""
		FeedcacheTestServer(get_port(), 2).start()
		feed = Feed.Load(self.store, TEST.http_fixture(u'302/dekstop.de_weblog_index.xml'))
		self.assertEquals(u'dekstop weblog', feed.title)

class HTTPErrorTest(DBTestBase):
	
	def testHTTP404Request(self):
		"""must throw FeedFetchError on HTTP 404 status"""
		FeedcacheTestServer(get_port(), 1).start()
		self.assertRaises(
			feedcache.exceptions.FeedFetchError,
			Feed.Load, self.store, TEST.http_fixture(u'404/dekstop.de_weblog_index.xml'))
	
	def testHTTP503Request(self):
		"""must throw FeedFetchError on HTTP 503 status"""
		FeedcacheTestServer(get_port(), 1).start()
		self.assertRaises(
			feedcache.exceptions.FeedFetchError,
			Feed.Load, self.store, TEST.http_fixture(u'503/dekstop.de_weblog_index.xml'))

class HTTPCachingTest(DBTestBase):
	
	def testETagHeader(self):
		"""when updating a feed we must send the ETag header from the initial request"""
		FeedcacheTestServer(get_port(), 2).start()
		feed = Feed.Load(self.store, TEST.http_fixture(u'fixture/dekstop.de_weblog_index.xml'))
		feed.update(self.store)
		# if we get here without an exception then we can cope with HTTP status 304 NOT MODIFIED
		self.assertEquals(ETAG_VALUE, FeedcacheTestHTTPHandler.request_header['If-None-Match'])
	
	def testLastModifiedHeader(self):
		"""when updating a feed we must send the Last Modified header from the initial request"""
		FeedcacheTestServer(get_port(), 2).start()
		feed = Feed.Load(self.store, TEST.http_fixture(u'fixture/dekstop.de_weblog_index.xml'))
		feed.update(self.store)
		# if we get here without an exception then we can cope with HTTP status 304 NOT MODIFIED
		self.assertEquals(LAST_MODIFIED_VALUE, FeedcacheTestHTTPHandler.request_header['If-Modified-Since'])

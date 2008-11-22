#!/usr/bin/env python
#
# crawl.py
#
# Test bed for feedparser code.
# Traverses local copies of feeds and does stuff.
#
# martind 2008-10-11, 15:50:59
#

import os
import sys
#import glob

import feedparser

cache_dir = r'./data/feeds'
#cache_dir = r'./data/feeds/contexts/people'

stdout = sys.stdout
stderr = sys.stdout

feedparser.USER_AGENT = feedparser.USER_AGENT + ' crawl.py'

#for filename in glob.glob(cache_dir + '/**/*'):
#	print filename

max_len = 0

for root, dirs, files in os.walk(cache_dir):
	for file in [f for f in files if False==os.path.isdir(f)]:
		filename = root + '/' + file
		stdout.write(filename + "\n")
		try:
			d = feedparser.parse(filename)
			if d.bozo:
				stderr.write('Bozo Bit: ' + d.bozo_exception.getMessage() + "\n")
				# note: a set bozo bit does not always mean we can't parse the feed -> continue
				
			if hasattr(d, 'status') and d.status==304:
				stdout.write('Feed content has not changed')
			elif d.version==None or d.version=='':
				stderr.write("Unsupported Document Type\n")
			else:
				print 'Version: ' + d.version
				if d.feed.has_key('title') and (len(d.feed.title) > 0):
					stdout.write('Title: ' + d.feed.title.encode('utf-8') + "\n")
				else:
					stderr.write("Title: <No title>\n")
				
				for entry in d.entries:
					if entry.has_key('content'):
						for content in entry.content:
							max_len = max(max_len, len(content.value))
					elif entry.has_key('summary'):
						max_len = max(max_len, len(entry.summary))
					else:
						print entry
		except LookupError, e:
		 	# broken character encoding
			import traceback
			tb = traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2])
			msg = tb.pop()
			stderr.write('Parse Error: ' + msg + "\n" + "\n".join(tb))
		except UnicodeEncodeError, e:
		 	# cannot write Unicode string to output stream. This should not happen on a live system;
			# usually it's caused by Unicde strings not being converted to UTF-8 before writing
			import traceback
			tb = traceback.format_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2])
			msg = tb.pop()
			stderr.write('Parse Error: ' + msg + "\n" + "\n".join(tb))

		stdout.write("----\n")

stdout.write("max len: %d" % max_len)

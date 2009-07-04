#!/usr/bin/env python
# coding=utf8
#
# lastfm.py
#
# ...
#
# martind 2008-12-09, 21:44:01
#

from optparse import OptionParser
import sys
from xml.etree import ElementTree as ET

import storm.locals

from feedcache.search import Searcher

# ========
# = conf =
# ========

#http://ws.audioscrobbler.com/2.0/?method=user.gettopartists&period=3month&user=martind&api_key=cc84abb177f541dfb3d43aff15f7166e

# ========
# = main =
# ========

if __name__ == '__main__':
	
	usage = 'usage: %prog driver://user:password@host/database <username>'
	parser = OptionParser(usage)
	
	(options, args) = parser.parse_args()

	if len(args) != 2:
		parser.error('incorrect number of arguments')
	dsn = args[0]

	# lfm
	xml = ET.parse('/Users/mongo/Documents/code/feedcache/py-feedcache/src/martind.xml').getroot()

	# check status
	if xml.attrib['status'] != 'ok':
		print xml.find('error').text
		sys.exit(1)
	
	# load result
	#artists = [u"マナ"]
	artists = []
	for n in xml.findall('topartists/artist/name'):
		artists.append(n.text)
	
	# search
	db = storm.database.create_database(dsn)
	store = storm.store.Store(db)

	for entry in Searcher.Entries(store, artists):
		print entry

	store.close()


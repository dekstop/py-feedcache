#!/usr/bin/env python
#
# uniq.py
#
# Prunes duplicate subscriptions for a specific user: for all feeds that have the 
# same feed.link value keep the one with the highest number of posts.
#
# (Doesn't actually remove duplicate feeds, it just removes the respective 
# users_feeds join table row.)
#
# martind 2009-07-14 00:20:43
#

from optparse import OptionParser
import sys
import time

import storm.locals

import feedcache.util as util

# ========
# = main =
# ========

if __name__ == '__main__':
	
	usage = 'usage: %prog [options] driver://user:password@host/database username'
	parser = OptionParser(usage)
	
	parser.add_option('-s', '--log-sql', 
		dest='log_sql', 
		action='store_true', 
		help='enable logging of SQL statements')
	
	(options, args) = parser.parse_args()

	if len(args) != 2:
		parser.error('incorrect number of arguments')
	dsn = args[0]
	username = args[1]
		
	db = storm.database.create_database(dsn)
	store = storm.store.Store(db)
	
	if options.log_sql:
		from storm.tracer import debug
		debug(True, stream=sys.stdout)

	store.execute("CREATE TEMPORARY TABLE feed_post_counts " +
		"AS SELECT f.id, f.link, count(*) AS total " +
		"FROM feeds f " + 
		"INNER JOIN entries e on f.id=e.feed_id " + 
		"GROUP BY f.id, f.link")
	store.execute("CREATE TEMPORARY TABLE feeds_dropme " + 
		"AS SELECT fpc.* FROM feed_post_counts fpc " + 
		"INNER JOIN (" + 
			"SELECT link, max(total) AS maxtotal " + 
			"FROM feed_post_counts " + 
			"GROUP BY link) t " + 
		"ON fpc.link=t.link AND fpc.total!=t.maxtotal " + 
		"INNER JOIN users_feeds uf ON uf.feed_id=fpc.id " + 
		"INNER JOIN users u ON uf.user_id=u.id " + 
		"WHERE u.name=?", [username])
	store.execute("DELETE FROM users_feeds 	" + 
		"WHERE user_id IN (" + 
			"SELECT id FROM users WHERE name=?) " + 
		"AND feed_id IN (" + 
			"SELECT id FROM feeds_dropme)", [username])

	store.commit()

	store.close()

#!/usr/bin/env python
#
# vis1.py
#
# martind 2008-12-30, 00:29:28
#

from optparse import OptionParser
import sys

from matplotlib.pyplot import figure, show
from numpy import pi, sin, linspace
from matplotlib.mlab import stineman_interp

import storm.locals

from feedcache.models.feeds import Batchimport, Feed
from feedcache.models.users import User

# ===========
# = helpers =
# ===========


# ========
# = main =
# ========

if __name__ == '__main__':
	
	usage = 'usage: %prog driver://user:password@host/database'
	parser = OptionParser(usage)
	
	(options, args) = parser.parse_args()

	if len(args) != 1:
		parser.error('incorrect number of arguments')
	dsn = args[0]

	db = storm.database.create_database(dsn)
	store = storm.store.Store(db)
	
	histogram = store.execute("select to_char(date_added, 'YYYY-MM-DD') as date, count(*) from entries group by date order by date")
	
	print histogram;
	
	# x = linspace(0,2*pi,20);
	# y = sin(x); yp = None
	# xi = linspace(x[0],x[-1],100);
	# yi = stineman_interp(xi,x,y,yp);
	# 
	# fig = figure()
	# ax = fig.add_subplot(111)
	# ax.plot(x,y,'ro',xi,yi,'-b.')
	# show()

	store.close()

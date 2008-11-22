# conf.py
#
# ...
#
# martind 2008-11-22, 16:12:53
#

import feedparser

__all__ = [
	'VERSION', 'USER_AGENT'
]

# =================
# = configuration =
# =================

VERSION = '0.1'

USER_AGENT = feedparser.USER_AGENT + ' feedcache ' + VERSION + ', feedcache@dekstop.de'


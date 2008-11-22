#!/usr/bin/env python

import unittest

from test_feeds import *
from test_http import *


if __name__ == "__main__":
	
	unittest.main()
	
	# runner = unittest.TextTestRunner()
	# runner.run(TransactionTest('testTransactionRollback'))

	# runner = unittest.TextTestRunner()
	# runner.run(HTTPCachingTest('testETagHeader'))
	# runner.run(BasicParserTest('testLoadFeed'))
	# runner.run(TransactionTest('testTransactionRollback'))

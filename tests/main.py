#!/usr/bin/env python

import unittest

from test_batchimports import *
from test_conf import *
from test_feeds import *
from test_http import *
from test_messages import *
from test_timezones import *


if __name__ == "__main__":
	
	unittest.main()
	
	# runner = unittest.TextTestRunner()
	# runner.run(ConfTest('testDefaultValueNone'))
	# runner.run(ConfTest('testStringProperty'))
	# runner.run(ConfTest('testIntProperty'))
	# runner.run(ConfTest('testLongProperty'))
	# runner.run(ConfTest('testDateTimeProperty'))

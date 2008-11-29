#!/usr/bin/env python

import pylab
import re
import storm.locals

# ============
# = get data =
# ============

# create table stats(id serial primary key, type text, start_time timestamp, end_time timestamp, num_retries int, num_messages int);
db = storm.database.create_database('postgres://postgres:@localhost/metrics')
store = storm.store.Store(db)

num_threads = []
time = []
num_retries = []
num_messages = []
p = re.compile('pro[^:]+: (\d+)')

for row in store.execute("select type, extract(epoch from (end_time-start_time)) as time, num_retries, num_messages from stats").get_all():
	m = p.match(row[0])
	if m:
		c = m.group(1)
		num_threads.append(int(c))
		time.append(row[1])
		num_retries.append(row[2])
		num_messages.append(row[3])

store.close()

# ========
# = draw =
# ========

pylab.xlabel('num_threads', fontsize=10)

pylab.scatter(num_threads, time, label='time', color='green', edgecolor='green', alpha=0.3)
pylab.scatter(num_threads, num_retries, label='num_retries', color='b', edgecolor='b', alpha=0.3)
pylab.scatter(num_threads, num_messages, label='num_errors', color='r', edgecolor='r', alpha=0.3)

leg = pylab.legend(('time', 'num_retries', 'num_errors'), axespad=0.05)
leg.get_frame().set_edgecolor('1')
for t in leg.get_texts():
	t.set_fontsize(10)

pylab.savefig('benchmark-plot.png')
pylab.show()

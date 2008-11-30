#!/bin/sh

function run() {
	bash ~/Documents/code/_aggregator/python/py-feedcache/bin/resetdb.sh feedcache
	python benchmark-threads.py $1 || return 1
	#python benchmark-processes.py $1 || return 1
}

function repeat() {
	for (( i=0; i<$1; i++ )); do 
		run $2 || return 1
	done
}

pushd ~/Documents/code/_aggregator/python/py-feedcache/src

for (( n=1; n<=15; n++ )); do
	repeat 10 $n || exit 1
done

popd


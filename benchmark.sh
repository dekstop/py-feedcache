#!/bin/sh

function run() {
	bash ~/Documents/code/_aggregator/python/py-feedcache/bin/resetdb.sh feedcache
	python crawl.py $1
}

function repeat() {
	for (( i=0; i<$1; i++ )); do 
		run $2
	done
}

pushd ~/Documents/code/_aggregator/python/py-feedcache/src

for (( n=10; n<=15; n++ )); do
	repeat 10 $n
done

popd


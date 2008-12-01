#!/bin/sh

bin=`dirname $0`
bin=`cd $bin; pwd`

${bin}/dropdb.sh $@
${bin}/createdb.sh $@ || exit 1
${bin}/loadschema.sh $@ || exit 1

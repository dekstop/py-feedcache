#!/bin/sh
#
# Stupid pp processes keep hanging. Run this script frequently to kill the app.
# (This is not nice.)
#

pid=`pgrep -f "bin/updateloop.sh" | head -n 1`
kill -- -${pid}

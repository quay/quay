#!/bin/bash

set -e

REPO=quay.io/quay/quay-dev

d ()
{
	docker build -t $REPO -f dev.df --build-arg src_subdir=$(basename `pwd`) .

	#ENV_VARS="foo=bar key=value name=joe"
	local envStr=""
	if [[ "$ENV_VARS" != "" ]];then
	    for envVar in $ENV_VARS;do
		    envStr="${envStr} -e \"${envVar}\""
	    done
	fi
	docker -- run --rm $envStr -v /var/run/docker.sock:/run/docker.sock -it --net=host -v $(pwd)/..:/src $REPO $*
}

case $1 in
buildman)
	d /venv/bin/python -m buildman.builder
	;;
dev)
	d bash /src/quay/local-run.sh
	;;
notifications)
	d /venv/bin/python -m workers.notificationworker
	;;
test)
	d bash /src/quay/local-test.sh
	;;
initdb)
	rm -f test/data/test.db
	d /venv/bin/python initdb.py
	;;
fulldbtest)
	d bash /src/quay/test/fulldbtest.sh
	;;
*)
	echo "unknown option"
	exit 1
	;;
esac

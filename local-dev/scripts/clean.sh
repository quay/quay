#!/bin/bash

# this script expects to be ran from root of 
# quay repository.

set -e 

Files=(
	'util/ipresolver/aws-ip-ranges.json'
	'revision_head'
	'local-dev/jwtproxy_conf.yaml'
	'local-dev/mitm.cert'
	'local-dev/mitm.key'
	'local-dev/quay.kid'
	'local-dev/quay.pem'
	'local-dev/supervisord.conf'
	'local-dev/__pycache__'
	'/local-dev/*.sock'
	'node_modules'
	'static/webfonts/'
	'supervisord.log'
	'supervisord.pid'
)

for file in "${Files[@]}"; do
	rm -rf $file
done

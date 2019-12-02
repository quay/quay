import os
import pytest
import json
import yaml
import jinja2

from ..supervisord_conf_create import QUAYCONF_DIR, default_services, limit_services


def render_supervisord_conf(config):
    with open(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../supervisord.conf.jnj")
    ) as f:
        template = jinja2.Template(f.read())
    return template.render(config=config)


def test_supervisord_conf_create_defaults():
    config = default_services()
    limit_services(config, [])
    rendered = render_supervisord_conf(config)

    expected = """[supervisord]
nodaemon=true

[unix_http_server]
file=%(ENV_QUAYCONF)s/supervisord.sock
user=root

[supervisorctl]
serverurl=unix:///%(ENV_QUAYCONF)s/supervisord.sock

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[eventlistener:stdout]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command = supervisor_stdout
buffer_size = 1024
events = PROCESS_LOG
result_handler = supervisor_stdout:event_handler

;;; Run batch scripts
[program:blobuploadcleanupworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.blobuploadcleanupworker.blobuploadcleanupworker
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:buildlogsarchiver]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.buildlogsarchiver.buildlogsarchiver
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:builder]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m buildman.builder
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:chunkcleanupworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.chunkcleanupworker
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:expiredappspecifictokenworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.expiredappspecifictokenworker
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:exportactionlogsworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.exportactionlogsworker
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:gcworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.gc.gcworker
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:globalpromstats]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.globalpromstats.globalpromstats
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:labelbackfillworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.labelbackfillworker
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:logrotateworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.logrotateworker
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:namespacegcworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.namespacegcworker
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:notificationworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.notificationworker.notificationworker
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:queuecleanupworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.queuecleanupworker
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:repositoryactioncounter]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.repositoryactioncounter
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:security_notification_worker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.security_notification_worker
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:securityworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.securityworker.securityworker
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:storagereplication]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.storagereplication
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:tagbackfillworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.tagbackfillworker
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:teamsyncworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.teamsyncworker.teamsyncworker
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

;;; Run interactive scripts
[program:dnsmasq]
command=/usr/sbin/dnsmasq --no-daemon --user=root --listen-address=127.0.0.1 --port=8053
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:gunicorn-registry]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s,
  DB_CONNECTION_POOLING=%(ENV_DB_CONNECTION_POOLING_REGISTRY)s
command=nice -n 10 gunicorn -c %(ENV_QUAYCONF)s/gunicorn_registry.py registry:application
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:gunicorn-secscan]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=gunicorn -c %(ENV_QUAYCONF)s/gunicorn_secscan.py secscan:application
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:gunicorn-verbs]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=nice -n 10 gunicorn -c %(ENV_QUAYCONF)s/gunicorn_verbs.py verbs:application
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:gunicorn-web]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=gunicorn -c %(ENV_QUAYCONF)s/gunicorn_web.py web:application
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:jwtproxy]
command=/usr/local/bin/jwtproxy --config %(ENV_QUAYCONF)s/jwtproxy_conf.yaml
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:memcache]
command=memcached -u memcached -m 64 -l 127.0.0.1 -p 18080
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:nginx]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=nginx -c %(ENV_QUAYCONF)s/nginx/nginx.conf
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:prometheus-aggregator]
command=/usr/local/bin/prometheus-aggregator
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:servicekey]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.servicekeyworker.servicekeyworker
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:repomirrorworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.repomirrorworker.repomirrorworker
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true
# EOF NO NEWLINE"""
    assert rendered == expected


def test_supervisord_conf_create_all_overrides():
    config = default_services()
    limit_services(config, "servicekey,prometheus-aggregator")
    rendered = render_supervisord_conf(config)

    expected = """[supervisord]
nodaemon=true

[unix_http_server]
file=%(ENV_QUAYCONF)s/supervisord.sock
user=root

[supervisorctl]
serverurl=unix:///%(ENV_QUAYCONF)s/supervisord.sock

[rpcinterface:supervisor]
supervisor.rpcinterface_factory = supervisor.rpcinterface:make_main_rpcinterface

[eventlistener:stdout]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command = supervisor_stdout
buffer_size = 1024
events = PROCESS_LOG
result_handler = supervisor_stdout:event_handler

;;; Run batch scripts
[program:blobuploadcleanupworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.blobuploadcleanupworker.blobuploadcleanupworker
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:buildlogsarchiver]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.buildlogsarchiver.buildlogsarchiver
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:builder]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m buildman.builder
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:chunkcleanupworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.chunkcleanupworker
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:expiredappspecifictokenworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.expiredappspecifictokenworker
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:exportactionlogsworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.exportactionlogsworker
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:gcworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.gc.gcworker
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:globalpromstats]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.globalpromstats.globalpromstats
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:labelbackfillworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.labelbackfillworker
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:logrotateworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.logrotateworker
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:namespacegcworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.namespacegcworker
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:notificationworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.notificationworker.notificationworker
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:queuecleanupworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.queuecleanupworker
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:repositoryactioncounter]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.repositoryactioncounter
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:security_notification_worker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.security_notification_worker
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:securityworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.securityworker.securityworker
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:storagereplication]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.storagereplication
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:tagbackfillworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.tagbackfillworker
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:teamsyncworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.teamsyncworker.teamsyncworker
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

;;; Run interactive scripts
[program:dnsmasq]
command=/usr/sbin/dnsmasq --no-daemon --user=root --listen-address=127.0.0.1 --port=8053
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:gunicorn-registry]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s,
  DB_CONNECTION_POOLING=%(ENV_DB_CONNECTION_POOLING_REGISTRY)s
command=nice -n 10 gunicorn -c %(ENV_QUAYCONF)s/gunicorn_registry.py registry:application
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:gunicorn-secscan]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=gunicorn -c %(ENV_QUAYCONF)s/gunicorn_secscan.py secscan:application
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:gunicorn-verbs]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=nice -n 10 gunicorn -c %(ENV_QUAYCONF)s/gunicorn_verbs.py verbs:application
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:gunicorn-web]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=gunicorn -c %(ENV_QUAYCONF)s/gunicorn_web.py web:application
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:jwtproxy]
command=/usr/local/bin/jwtproxy --config %(ENV_QUAYCONF)s/jwtproxy_conf.yaml
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:memcache]
command=memcached -u memcached -m 64 -l 127.0.0.1 -p 18080
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:nginx]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=nginx -c %(ENV_QUAYCONF)s/nginx/nginx.conf
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:prometheus-aggregator]
command=/usr/local/bin/prometheus-aggregator
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:servicekey]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.servicekeyworker.servicekeyworker
autostart = true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true

[program:repomirrorworker]
environment=
  PYTHONPATH=%(ENV_QUAYDIR)s
command=python -m workers.repomirrorworker.repomirrorworker
autostart = false
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stdout
stderr_logfile_maxbytes=0
stdout_events_enabled = true
stderr_events_enabled = true
# EOF NO NEWLINE"""
    assert rendered == expected

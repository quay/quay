from util.ipresolver import IPResolver

from singletons.app import _app

ip_resolver = IPResolver(_app)

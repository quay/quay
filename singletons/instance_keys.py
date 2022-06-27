from util.security.instancekeys import InstanceKeys

from singletons.app import _app

instance_keys = InstanceKeys(_app)

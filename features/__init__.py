import os

from singletons.config import app_config

_FEATURES = {}


def import_features(config_dict):
    for feature, feature_val in list(config_dict.items()):
        if feature.startswith("FEATURE_"):
            feature_name = feature[8:]
            _FEATURES[feature_name] = globals()[feature_name] = FeatureNameValue(
                feature_name, feature_val
            )
    for key, val in os.environ.items():
        if key.startswith("QUAY_FEATURE_"):
            feature_name = key[len("QUAY_FEATURE_") :]
            _FEATURES[feature_name] = globals()[feature_name] = FeatureNameValue(feature_name, val)


def get_features():
    return {key: _FEATURES[key].value for key in _FEATURES}


class FeatureNameValue(object):
    def __init__(self, name, value):
        self.value = value
        self.name = name

    def __str__(self):
        return "%s => %s" % (self.name, self.value)

    def __repr__(self):
        return str(self.value)

    def __cmp__(self, other):
        return self.value.__cmp__(other)

    def __bool__(self):
        if isinstance(self.value, str):
            return self.value.lower() == "true"

        return bool(self.value)


# Load features from config.
import_features(app_config)

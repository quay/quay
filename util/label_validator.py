class LabelValidator(object):
    """
    Helper class for validating that labels meet prefix requirements.
    """

    def __init__(self, app):
        self.app = app

        overridden_prefixes = app.config.get("LABEL_KEY_RESERVED_PREFIXES", [])
        for prefix in overridden_prefixes:
            if not prefix.endswith("."):
                raise Exception(
                    'Prefix "%s" in LABEL_KEY_RESERVED_PREFIXES must end in a dot', prefix
                )

        default_prefixes = app.config.get("DEFAULT_LABEL_KEY_RESERVED_PREFIXES", [])
        self.reserved_prefixed_set = set(default_prefixes + overridden_prefixes)

    def has_reserved_prefix(self, label_key):
        """
        Validates that the provided label key does not match any reserved prefixes.
        """
        for prefix in self.reserved_prefixed_set:
            if label_key.startswith(prefix):
                return True

        return False

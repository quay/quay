class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self

    @classmethod
    def deep_copy(cls, attr_dict):
        copy = AttrDict(attr_dict)
        for key, value in list(copy.items()):
            if isinstance(value, AttrDict):
                copy[key] = cls.deep_copy(value)
        return copy

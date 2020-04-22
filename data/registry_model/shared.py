import uuid

from hashids import Hashids


class SyntheticIDHandler(object):
    def __init__(self, hash_salt=None):
        self.hash_salt = hash_salt or str(uuid.uuid4())
        self.hashids = Hashids(alphabet="0123456789abcdef", min_length=64, salt=self.hash_salt)

    def encode(self, manifest_id, layer_index=0):
        encoded = self.hashids.encode(manifest_id, layer_index)
        assert len(encoded) == 64
        return encoded

    def decode(self, synthetic_v1_id):
        return self.hashids.decode(synthetic_v1_id)

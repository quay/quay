import re
import os.path
import hashlib


DIGEST_PATTERN = r"([A-Za-z0-9_+.-]+):([A-Fa-f0-9]+)"
REPLACE_WITH_PATH = re.compile(r"[+.]")
REPLACE_DOUBLE_SLASHES = re.compile(r"/+")


class InvalidDigestException(RuntimeError):
    pass


class Digest(object):
    DIGEST_REGEX = re.compile(DIGEST_PATTERN)

    def __init__(self, hash_alg, hash_bytes):
        self._hash_alg = hash_alg
        self._hash_bytes = hash_bytes

    def __str__(self):
        return "{0}:{1}".format(self._hash_alg, self._hash_bytes)

    def __eq__(self, rhs):
        return isinstance(rhs, Digest) and str(self) == str(rhs)

    def __hash__(self):
        return hash((self._hash_alg, self._hash_bytes))

    @staticmethod
    def parse_digest(digest):
        """
        Returns the digest parsed out to its components.
        """
        match = Digest.DIGEST_REGEX.match(digest)
        if match is None or match.end() != len(digest):
            raise InvalidDigestException("Not a valid digest: %s", digest)

        return Digest(match.group(1), match.group(2))

    @property
    def hash_alg(self):
        return self._hash_alg

    @property
    def hash_bytes(self):
        return self._hash_bytes


def content_path(digest):
    """
    Returns a relative path to the parsed digest.
    """
    parsed = Digest.parse_digest(digest)
    components = []

    # Generate a prefix which is always two characters, and which will be filled with leading zeros
    # if the input does not contain at least two characters. e.g. ABC -> AB, A -> 0A
    prefix = parsed.hash_bytes[0:2].zfill(2)
    pathish = REPLACE_WITH_PATH.sub("/", parsed.hash_alg)
    normalized = REPLACE_DOUBLE_SLASHES.sub("/", pathish).lstrip("/")
    components.extend([normalized, prefix, parsed.hash_bytes])
    return os.path.join(*components)


def sha256_digest(content):
    """
    Returns a sha256 hash of the content bytes in digest form.
    """
    assert isinstance(content, bytes)

    def single_chunk_generator():
        yield content

    return sha256_digest_from_generator(single_chunk_generator())


def sha256_digest_from_generator(content_generator):
    """
    Reads all of the data from the iterator and creates a sha256 digest from the content.
    """
    digest = hashlib.sha256()
    for chunk in content_generator:
        digest.update(chunk)
    return "sha256:{0}".format(digest.hexdigest())


def sha256_digest_from_hashlib(sha256_hash_obj):
    return "sha256:{0}".format(sha256_hash_obj.hexdigest())


def digests_equal(lhs_digest_string, rhs_digest_string):
    """
    Parse and compare the two digests, returns True if the digests are equal, False otherwise.
    """
    return Digest.parse_digest(lhs_digest_string) == Digest.parse_digest(rhs_digest_string)

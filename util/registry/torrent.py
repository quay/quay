import hashlib
import time

from binascii import hexlify

import bencode
import jwt
import resumablehashlib


class TorrentConfiguration(object):
    def __init__(self, instance_keys, announce_url, filename_pepper, registry_title):
        self.instance_keys = instance_keys
        self.announce_url = announce_url
        self.filename_pepper = filename_pepper
        self.registry_title = registry_title

    @classmethod
    def for_testing(cls, instance_keys, announce_url, registry_title):
        return TorrentConfiguration(instance_keys, announce_url, "somepepper", registry_title)

    @classmethod
    def from_app_config(cls, instance_keys, config):
        return TorrentConfiguration(
            instance_keys,
            config["BITTORRENT_ANNOUNCE_URL"],
            config["BITTORRENT_FILENAME_PEPPER"],
            config["REGISTRY_TITLE"],
        )


def _jwt_from_infodict(torrent_config, infodict):
    """
    Returns an encoded JWT for the given BitTorrent info dict, signed by the local instance's
    private key.
    """
    digest = hashlib.sha1()
    digest.update(bencode.bencode(infodict))
    return jwt_from_infohash(torrent_config, digest.digest())


def jwt_from_infohash(torrent_config, infohash_digest):
    """
    Returns an encoded JWT for the given BitTorrent infohash, signed by the local instance's private
    key.
    """
    token_data = {
        "iss": torrent_config.instance_keys.service_name,
        "aud": torrent_config.announce_url,
        "infohash": hexlify(infohash_digest),
    }
    return jwt.encode(
        token_data,
        torrent_config.instance_keys.local_private_key,
        algorithm="RS256",
        headers={"kid": torrent_config.instance_keys.local_key_id},
    )


def make_torrent(torrent_config, name, webseed, length, piece_length, pieces):
    info_dict = {
        "name": name,
        "length": length,
        "piece length": piece_length,
        "pieces": pieces,
        "private": 1,
    }

    info_jwt = _jwt_from_infodict(torrent_config, info_dict)
    return bencode.bencode(
        {
            "announce": torrent_config.announce_url + "?jwt=" + info_jwt,
            "url-list": str(webseed),
            "encoding": "UTF-8",
            "created by": torrent_config.registry_title,
            "creation date": int(time.time()),
            "info": info_dict,
        }
    )


def public_torrent_filename(blob_uuid):
    """
    Returns the filename for the given blob UUID in a public image.
    """
    return hashlib.sha256(blob_uuid).hexdigest()


def per_user_torrent_filename(torrent_config, user_uuid, blob_uuid):
    """
    Returns the filename for the given blob UUID for a private image.
    """
    joined = torrent_config.filename_pepper + "||" + blob_uuid + "||" + user_uuid
    return hashlib.sha256(joined).hexdigest()


class PieceHasher(object):
    """
    Utility for computing torrent piece hashes as the data flows through the update method of this
    class.

    Users should get the final value by calling final_piece_hashes since new chunks are allocated
    lazily.
    """

    def __init__(
        self,
        piece_size,
        starting_offset=0,
        starting_piece_hash_bytes="",
        hash_fragment_to_resume=None,
    ):
        if not isinstance(starting_offset, int):
            raise TypeError("starting_offset must be an integer")
        elif not isinstance(piece_size, int):
            raise TypeError("piece_size must be an integer")

        self._current_offset = starting_offset
        self._piece_size = piece_size
        self._piece_hashes = bytearray(starting_piece_hash_bytes)

        if hash_fragment_to_resume is None:
            self._hash_fragment = resumablehashlib.sha1()
        else:
            self._hash_fragment = hash_fragment_to_resume

    def update(self, buf):
        buf_offset = 0
        while buf_offset < len(buf):
            buf_bytes_to_hash = buf[0 : self._piece_length_remaining()]
            to_hash_len = len(buf_bytes_to_hash)

            if self._piece_offset() == 0 and to_hash_len > 0 and self._current_offset > 0:
                # We are opening a new piece
                self._piece_hashes.extend(self._hash_fragment.digest())
                self._hash_fragment = resumablehashlib.sha1()

            self._hash_fragment.update(buf_bytes_to_hash)
            self._current_offset += to_hash_len
            buf_offset += to_hash_len

    @property
    def hashed_bytes(self):
        return self._current_offset

    def _piece_length_remaining(self):
        return self._piece_size - (self._current_offset % self._piece_size)

    def _piece_offset(self):
        return self._current_offset % self._piece_size

    @property
    def piece_hashes(self):
        return self._piece_hashes

    @property
    def hash_fragment(self):
        return self._hash_fragment

    def final_piece_hashes(self):
        return self._piece_hashes + self._hash_fragment.digest()

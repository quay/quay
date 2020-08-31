# -*- coding: utf-8 -*-

import random
import string

import pytest

from Crypto.PublicKey import RSA
from jwkest.jwk import RSAKey

from test.registry.fixtures import data_model
from test.registry.protocols import Image, layer_bytes_for_contents
from test.registry.protocol_v1 import V1Protocol
from test.registry.protocol_v2 import V2Protocol


@pytest.fixture(scope="session")
def basic_images():
    """
    Returns basic images for push and pull testing.
    """
    # Note: order is from base layer down to leaf.
    parent_bytes = layer_bytes_for_contents(b"parent contents")
    image_bytes = layer_bytes_for_contents(b"some contents")
    return [
        Image(id="parentid", bytes=parent_bytes, parent_id=None),
        Image(id="someid", bytes=image_bytes, parent_id="parentid"),
    ]


@pytest.fixture(scope="session")
def unicode_images():
    """
    Returns basic images for push and pull testing that contain unicode in the image metadata.
    """
    # Note: order is from base layer down to leaf.
    parent_bytes = layer_bytes_for_contents(b"parent contents")
    image_bytes = layer_bytes_for_contents(b"some contents")
    return [
        Image(id="parentid", bytes=parent_bytes, parent_id=None),
        Image(
            id="someid",
            bytes=image_bytes,
            parent_id="parentid",
            config={"comment": "the Pawe\xc5\x82 Kami\xc5\x84ski image", "author": "Sômé guy"},
        ),
    ]


@pytest.fixture(scope="session")
def different_images():
    """
    Returns different basic images for push and pull testing.
    """
    # Note: order is from base layer down to leaf.
    parent_bytes = layer_bytes_for_contents(b"different parent contents")
    image_bytes = layer_bytes_for_contents(b"some different contents")
    return [
        Image(id="anotherparentid", bytes=parent_bytes, parent_id=None),
        Image(id="anothersomeid", bytes=image_bytes, parent_id="anotherparentid"),
    ]


@pytest.fixture(scope="session")
def sized_images():
    """
    Returns basic images (with sizes) for push and pull testing.
    """
    # Note: order is from base layer down to leaf.
    parent_bytes = layer_bytes_for_contents(b"parent contents", mode="")
    image_bytes = layer_bytes_for_contents(b"some contents", mode="")
    return [
        Image(
            id="parentid",
            bytes=parent_bytes,
            parent_id=None,
            size=len(parent_bytes),
            config={"foo": "bar"},
        ),
        Image(
            id="someid",
            bytes=image_bytes,
            parent_id="parentid",
            size=len(image_bytes),
            config={"foo": "childbar", "Entrypoint": ["hello"]},
            created="2018-04-03T18:37:09.284840891Z",
        ),
    ]


@pytest.fixture(scope="session")
def multi_layer_images():
    """
    Returns complex images (with sizes) for push and pull testing.
    """
    # Note: order is from base layer down to leaf.
    layer1_bytes = layer_bytes_for_contents(
        b"layer 1 contents",
        mode="",
        other_files={
            "file1": b"from-layer-1",
        },
    )

    layer2_bytes = layer_bytes_for_contents(
        b"layer 2 contents",
        mode="",
        other_files={
            "file2": b"from-layer-2",
        },
    )

    layer3_bytes = layer_bytes_for_contents(
        b"layer 3 contents",
        mode="",
        other_files={
            "file1": b"from-layer-3",
            "file3": b"from-layer-3",
        },
    )

    layer4_bytes = layer_bytes_for_contents(
        b"layer 4 contents",
        mode="",
        other_files={
            "file3": b"from-layer-4",
        },
    )

    layer5_bytes = layer_bytes_for_contents(
        b"layer 5 contents",
        mode="",
        other_files={
            "file4": b"from-layer-5",
        },
    )

    return [
        Image(
            id="layer1",
            bytes=layer1_bytes,
            parent_id=None,
            size=len(layer1_bytes),
            config={"internal_id": "layer1"},
        ),
        Image(
            id="layer2",
            bytes=layer2_bytes,
            parent_id="layer1",
            size=len(layer2_bytes),
            config={"internal_id": "layer2"},
        ),
        Image(
            id="layer3",
            bytes=layer3_bytes,
            parent_id="layer2",
            size=len(layer3_bytes),
            config={"internal_id": "layer3"},
        ),
        Image(
            id="layer4",
            bytes=layer4_bytes,
            parent_id="layer3",
            size=len(layer4_bytes),
            config={"internal_id": "layer4"},
        ),
        Image(
            id="someid",
            bytes=layer5_bytes,
            parent_id="layer4",
            size=len(layer5_bytes),
            config={"internal_id": "layer5"},
        ),
    ]


@pytest.fixture(scope="session")
def remote_images():
    """
    Returns images with at least one remote layer for push and pull testing.
    """
    # Note: order is from base layer down to leaf.
    remote_bytes = layer_bytes_for_contents(b"remote contents")
    parent_bytes = layer_bytes_for_contents(b"parent contents")
    image_bytes = layer_bytes_for_contents(b"some contents")
    return [
        Image(id="remoteid", bytes=remote_bytes, parent_id=None, urls=["http://some/url"]),
        Image(id="parentid", bytes=parent_bytes, parent_id="remoteid"),
        Image(id="someid", bytes=image_bytes, parent_id="parentid"),
    ]


@pytest.fixture(scope="session")
def images_with_empty_layer():
    """
    Returns images for push and pull testing that contain an empty layer.
    """
    # Note: order is from base layer down to leaf.
    parent_bytes = layer_bytes_for_contents(b"parent contents")
    empty_bytes = layer_bytes_for_contents(b"", empty=True)
    image_bytes = layer_bytes_for_contents(b"some contents")
    middle_bytes = layer_bytes_for_contents(b"middle")

    return [
        Image(id="parentid", bytes=parent_bytes, parent_id=None),
        Image(id="emptyid", bytes=empty_bytes, parent_id="parentid", is_empty=True),
        Image(id="middleid", bytes=middle_bytes, parent_id="emptyid"),
        Image(id="emptyid2", bytes=empty_bytes, parent_id="middleid", is_empty=True),
        Image(id="someid", bytes=image_bytes, parent_id="emptyid2"),
    ]


@pytest.fixture(scope="session")
def unicode_emoji_images():
    """
    Returns basic images for push and pull testing that contain unicode in the image metadata.
    """
    # Note: order is from base layer down to leaf.
    parent_bytes = layer_bytes_for_contents(b"parent contents")
    image_bytes = layer_bytes_for_contents(b"some contents")
    return [
        Image(id="parentid", bytes=parent_bytes, parent_id=None),
        Image(
            id="someid",
            bytes=image_bytes,
            parent_id="parentid",
            config={"comment": "😱", "author": "Sômé guy"},
        ),
    ]


@pytest.fixture(scope="session")
def jwk():
    return RSAKey(key=RSA.generate(2048))


@pytest.fixture(params=[V2Protocol])
def v2_protocol(request, jwk):
    return request.param(jwk)


@pytest.fixture()
def v21_protocol(request, jwk):
    return V2Protocol(jwk, schema="schema1")


@pytest.fixture()
def v22_protocol(request, jwk):
    return V2Protocol(jwk, schema="schema2")


@pytest.fixture(params=[V1Protocol])
def v1_protocol(request, jwk):
    return request.param(jwk)


@pytest.fixture(params=["schema1", "schema2", "oci"])
def manifest_protocol(request, data_model, jwk):
    return V2Protocol(jwk, schema=request.param)


@pytest.fixture(params=["v1", "v2_1", "v2_2", "oci"])
def pusher(request, data_model, jwk):
    if request.param == "v1":
        return V1Protocol(jwk)

    if request.param == "v2_2":
        return V2Protocol(jwk, schema="schema2")

    if request.param == "oci":
        return V2Protocol(jwk, schema="oci")

    return V2Protocol(jwk)


@pytest.fixture(params=["v1", "v2_1"])
def legacy_puller(request, data_model, jwk):
    if request.param == "v1":
        return V1Protocol(jwk)

    return V2Protocol(jwk)


@pytest.fixture(params=["v1", "v2_1"])
def legacy_pusher(request, data_model, jwk):
    if request.param == "v1":
        return V1Protocol(jwk)

    return V2Protocol(jwk)


@pytest.fixture(params=["v1", "v2_1", "v2_2", "oci"])
def puller(request, data_model, jwk):
    if request.param == "v1":
        return V1Protocol(jwk)

    if request.param == "v2_2":
        return V2Protocol(jwk, schema="schema2")

    if request.param == "oci":
        return V2Protocol(jwk, schema="oci")

    return V2Protocol(jwk)


@pytest.fixture(params=[V1Protocol, V2Protocol])
def loginer(request, jwk):
    return request.param(jwk)


@pytest.fixture(scope="session")
def random_layer_data():
    size = 4096
    contents = "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(size))
    return layer_bytes_for_contents(contents.encode("ascii"))

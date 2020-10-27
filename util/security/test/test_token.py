from util.security.token import (
    encode_public_private_token,
    decode_public_private_token,
    DecodedToken,
)


def test_private_token():

    public_code = "PUBLIC-CODE"
    private_token = "PRIVATE-TOKEN"

    encoded_token = encode_public_private_token(public_code, private_token)
    assert isinstance(encoded_token, str)

    decoded_token = decode_public_private_token(encoded_token)
    assert isinstance(decoded_token, DecodedToken)

    assert decoded_token.public_code == public_code
    assert decoded_token.private_token == private_token

import base64


def parse_basic_auth(header_value):
    """
    Attempts to parse the given header value as a Base64-encoded Basic auth header.
    """

    if not header_value:
        return None

    parts = header_value.split(" ")
    if len(parts) != 2 or parts[0].lower() != "basic":
        return None

    try:
        basic_parts = base64.b64decode(parts[1]).split(":", 1)
        if len(basic_parts) != 2:
            return None

        return basic_parts
    except ValueError:
        return None

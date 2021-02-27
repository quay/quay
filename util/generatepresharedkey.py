import argparse

from dateutil.parser import parse as parse_date

from app import app
from data import model
from data.database import ServiceKeyApprovalType
from data.logs_model import logs_model


def generate_key(service, name, expiration_date=None, notes=None):
    metadata = {
        "created_by": "CLI tool",
    }

    # Generate a key with a private key that we *never save*.
    (private_key, key) = model.service_keys.generate_service_key(
        service, expiration_date, metadata=metadata, name=name
    )
    # Auto-approve the service key.
    model.service_keys.approve_service_key(
        key.kid, ServiceKeyApprovalType.AUTOMATIC, notes=notes or ""
    )

    return private_key, key.kid


def valid_date(s):
    try:
        return parse_date(s)
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generates a preshared key")
    parser.add_argument("service", help="The service name for which the key is being generated")
    parser.add_argument("name", help="The friendly name for the key")
    parser.add_argument(
        "--expiration",
        default=None,
        type=valid_date,
        help="The optional expiration date for the key",
    )
    parser.add_argument("--notes", help="Optional notes about the key", default=None)

    args = parser.parse_args()
    generated, _ = generate_key(args.service, args.name, args.expiration, args.notes)
    print(
        generated.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )

from collections import namedtuple
from datetime import datetime

from data.database import User


class UserDataType(
    namedtuple(
        "User",
        [
            "id",
            "uuid" "username",
            "password_hash",
            "email",
            "verified",
            "stripe_id",
            "organization",
            "robot",
            "invoice_email",
            "invalid_login_attempts",
            "last_invalid_login",
            "removed_tag_expiration_s",
            "enabled",
            "invoice_email_address",
            "given_name",
            "family_name",
            "company",
            "location",
            "maximum_queued_builds_count",
            "creation_date",
            "last_accessed",
        ],
    )
):
    """
    BlobUpload represents information about an in-progress upload to create a blob.
    """

    @classmethod
    def to_dict(cls, user):
        return {
            "id": user.id,
            "uuid": user.uuid,
            "username": user.username,
            "password_hash": user.password_hash,
            "email": user.email,
            "verified": user.verified,
            "stripe_id": user.stripe_id,
            "organization": user.organization,
            "robot": user.robot,
            "invoice_email": user.invoice_email,
            "invalid_login_attempts": user.invalid_login_attempts,
            "last_invalid_login": user.last_invalid_login.strftime("%Y-%m-%d %H:%M:%S"),
            "removed_tag_expiration_s": user.removed_tag_expiration_s,
            "enabled": user.enabled,
            "invoice_email_address": user.invoice_email_address,
            "given_name": user.given_name,
            "family_name": user.family_name,
            "company": user.company,
            "location": user.location,
            "maximum_queued_builds_count": user.maximum_queued_builds_count,
            "creation_date": user.creation_date.strftime("%Y-%m-%d %H:%M:%S"),
            "last_accessed": user.last_accessed,
        }

    @classmethod
    def from_dict(cls, user):
        if user is None:
            return None

        return User(
            id=user["id"],
            uuid=user["uuid"],
            username=user["username"],
            password_hash=user["password_hash"],
            email=user["email"],
            verified=user["verified"],
            stripe_id=user["stripe_id"],
            organization=user["organization"],
            robot=user["robot"],
            invoice_email=user["invoice_email"],
            invalid_login_attempts=user["invalid_login_attempts"],
            last_invalid_login=datetime.strptime(user["last_invalid_login"], "%Y-%m-%d %H:%M:%S"),
            removed_tag_expiration_s=user["removed_tag_expiration_s"],
            enabled=user["enabled"],
            invoice_email_address=user["invoice_email_address"],
            given_name=user["given_name"],
            family_name=user["family_name"],
            company=user["company"],
            location=user["location"],
            maximum_queued_builds_count=user["maximum_queued_builds_count"],
            creation_date=datetime.strptime(user["creation_date"], "%Y-%m-%d %H:%M:%S"),
            last_accessed=user["last_accessed"],
        )

import json

import features
from data.database import RepositoryPolicy


def get_repository_policy(repository):
    try:
        policy = RepositoryPolicy.select().where(RepositoryPolicy.repository == repository).get()
        return policy
    except RepositoryPolicy.DoesNotExist:
        return None


def get_or_create_repository_policy(repository):
    try:
        policy = RepositoryPolicy.select().where(RepositoryPolicy.repository == repository).get()
        return policy
    except RepositoryPolicy.DoesNotExist:
        pass

    policy = RepositoryPolicy.create(
        repository=repository, policy=json.dumps({"blockUnisgnedImages": False})
    )
    return policy


def update_or_create_repository_policy(repository, policy_config):
    # TODO: change this to update in one request
    try:
        policy = RepositoryPolicy.select().where(RepositoryPolicy.repository == repository).get()
        policy.policy = json.dumps(policy_config)
        policy.save()
        return policy
    except RepositoryPolicy.DoesNotExist:
        pass

    return RepositoryPolicy.create(repository=repository, policy=json.dumps(policy_config))


def block_unsigned_images_enabled(repository):
    if not features.BLOCK_UNSIGNED_IMAGES:
        return False

    policy = get_repository_policy(repository.id)
    if policy is None:
        return False

    policy = json.loads(policy.policy)
    return policy.get("blockUnsignedImages", False)

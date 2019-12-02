import logging
import time

from datetime import datetime, timedelta

from data.database import RepositoryBuild, AccessToken
from app import app

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000


def delete_temporary_access_tokens(older_than):
    # Find the highest ID up to which we should delete
    up_to_id = (
        AccessToken.select(AccessToken.id)
        .where(AccessToken.created < older_than)
        .limit(1)
        .order_by(AccessToken.id.desc())
        .get()
        .id
    )
    logger.debug("Deleting temporary access tokens with ids lower than: %s", up_to_id)

    access_tokens_in_builds = RepositoryBuild.select(RepositoryBuild.access_token).distinct()

    while up_to_id > 0:
        starting_at_id = max(up_to_id - BATCH_SIZE, 0)
        logger.debug("Deleting tokens with ids between %s and %s", starting_at_id, up_to_id)
        start_time = datetime.utcnow()
        (
            AccessToken.delete()
            .where(
                AccessToken.id >= starting_at_id,
                AccessToken.id < up_to_id,
                AccessToken.temporary == True,
                ~(AccessToken.id << access_tokens_in_builds),
            )
            .execute()
        )

        time_to_delete = datetime.utcnow() - start_time

        up_to_id -= BATCH_SIZE

        logger.debug("Sleeping for %s seconds", time_to_delete.total_seconds())
        time.sleep(time_to_delete.total_seconds())


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    delete_temporary_access_tokens(datetime.utcnow() - timedelta(days=2))

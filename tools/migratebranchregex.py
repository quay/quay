import argparse
import logging
import json

from app import app
from data import model
from data.database import RepositoryBuildTrigger, configure
from data.model.build import update_build_trigger

configure(app.config)

logger = logging.getLogger(__name__)


def run_branchregex_migration():
    encountered = set()
    while True:
        found = list(
            RepositoryBuildTrigger.select().where(
                RepositoryBuildTrigger.config ** "%branch_regex%",
                ~(RepositoryBuildTrigger.config ** "%branchtag_regex%"),
            )
        )
        found = [f for f in found if not f.uuid in encountered]

        if not found:
            logger.debug("No additional records found")
            return

        logger.debug("Found %s records to be changed", len(found))
        for trigger in found:
            encountered.add(trigger.uuid)

            try:
                config = json.loads(trigger.config)
            except:
                logging.error("Cannot parse config for trigger %s", trigger.uuid)
                continue

            logger.debug("Checking trigger %s", trigger.uuid)
            existing_regex = config["branch_regex"]
            logger.debug("Found branch regex '%s'", existing_regex)

            sub_regex = existing_regex.split("|")
            new_regex = "|".join(["heads/" + sub for sub in sub_regex])
            config["branchtag_regex"] = new_regex

            logger.debug("Updating to branchtag regex '%s'", new_regex)
            update_build_trigger(trigger, config)


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("boto").setLevel(logging.CRITICAL)

    run_branchregex_migration()

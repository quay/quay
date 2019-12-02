from math import log10

from app import app
from data.model.image import (
    get_images_eligible_for_scan,
    get_image_pk_field,
    get_max_id_for_sec_scan,
    get_min_id_for_sec_scan,
)
from util.migrate.allocator import yield_random_entries

from workers.securityworker.models_interface import ScanToken, SecurityWorkerDataInterface


class PreOCIModel(SecurityWorkerDataInterface):
    def candidates_to_scan(self, target_version, start_token=None):
        def batch_query():
            return get_images_eligible_for_scan(target_version)

        # Find the minimum ID.
        min_id = None
        if start_token is not None:
            min_id = start_token.min_id
        else:
            min_id = app.config.get("SECURITY_SCANNER_INDEXING_MIN_ID")
            if min_id is None:
                min_id = get_min_id_for_sec_scan(target_version)

        # Get the ID of the last image we can analyze. Will be None if there are no images in the
        # database.
        max_id = get_max_id_for_sec_scan()
        if max_id is None:
            return (None, None)

        if min_id is None or min_id > max_id:
            return (None, None)

        # 4^log10(total) gives us a scalable batch size into the billions.
        batch_size = int(4 ** log10(max(10, max_id - min_id)))

        # TODO: Once we have a clean shared NamedTuple for Images, send that to the secscan analyzer
        # rather than the database Image itself.
        iterator = yield_random_entries(
            batch_query, get_image_pk_field(), batch_size, max_id, min_id,
        )

        return (iterator, ScanToken(max_id + 1))


pre_oci_model = PreOCIModel()

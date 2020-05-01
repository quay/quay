from data.appr_model import tag as apprtags_model
from data.appr_model.tag import get_most_recent_tag_lifetime_start
from endpoints.appr.models_cnr import model as appr_model

from test.fixtures import *


def test_empty_get_most_recent_tag_lifetime_start(initialized_db):
    tags = apprtags_model.get_most_recent_tag_lifetime_start([], appr_model.models_ref)
    assert isinstance(tags, dict) and len(tags) == 0

import base64
from test.fixtures import *

import pytest
from flask import url_for

from data import model
from endpoints.test.shared import conduct_call, gen_basic_auth


def test_start_build_disabled_trigger(app, client):
    trigger = model.build.list_build_triggers("devtable", "building")[0]
    trigger.enabled = False
    trigger.save()

    params = {
        "trigger_uuid": trigger.uuid,
    }

    headers = {
        "Authorization": gen_basic_auth("devtable", "password"),
    }

    conduct_call(
        client,
        "webhooks.build_trigger_webhook",
        url_for,
        "POST",
        params,
        None,
        400,
        headers=headers,
    )

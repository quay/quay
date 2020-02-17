from endpoints.test.shared import conduct_call
from endpoints.api import api


def conduct_api_call(client, resource, method, params, body=None, expected_code=200, headers=None):
    """
    Conducts an API call to the given resource via the given client, and ensures its returned status
    matches the code given.

    Returns the response.
    """
    return conduct_call(
        client, resource, api.url_for, method, params, body, expected_code, headers=headers
    )

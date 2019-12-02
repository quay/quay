import pytest
from mock import patch

from endpoints.api.subscribe_models_pre_oci import data_model


@pytest.mark.parametrize("username,repo_count", [("devtable", 3)])
def test_get_private_repo_count(username, repo_count):
    with patch(
        "endpoints.api.subscribe_models_pre_oci.get_private_repo_count"
    ) as mock_get_private_reop_count:
        mock_get_private_reop_count.return_value = repo_count
        count = data_model.get_private_repo_count(username)

        mock_get_private_reop_count.assert_called_once_with(username)
        assert count == repo_count


@pytest.mark.parametrize(
    "kind_name,target_username,metadata",
    [("over_private_usage", "devtable", {"namespace": "devtable"})],
)
def test_create_unique_notification(kind_name, target_username, metadata):
    with patch("endpoints.api.subscribe_models_pre_oci.get_user_or_org") as mock_get_user_or_org:
        mock_get_user_or_org.return_value = {"username": target_username}
        with patch(
            "endpoints.api.subscribe_models_pre_oci.create_unique_notification"
        ) as mock_create_unique_notification:
            data_model.create_unique_notification(kind_name, target_username, metadata)

            mock_get_user_or_org.assert_called_once_with(target_username)
            mock_create_unique_notification.assert_called_once_with(
                kind_name, mock_get_user_or_org.return_value, metadata
            )


@pytest.mark.parametrize("target_username,kind_name", [("devtable", "over_private_usage")])
def test_delete_notifications_by_kind(target_username, kind_name):
    with patch("endpoints.api.subscribe_models_pre_oci.get_user_or_org") as mock_get_user_or_org:
        mock_get_user_or_org.return_value = {"username": target_username}
        with patch(
            "endpoints.api.subscribe_models_pre_oci.delete_notifications_by_kind"
        ) as mock_delete_notifications_by_kind:
            data_model.delete_notifications_by_kind(target_username, kind_name)

            mock_get_user_or_org.assert_called_once_with(target_username)
            mock_delete_notifications_by_kind.assert_called_once_with(
                mock_get_user_or_org.return_value, kind_name
            )

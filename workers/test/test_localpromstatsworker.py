import mock

from workers.localpromstats import get_gunicorn_process_count, get_zombie_process_count


@mock.patch("workers.localpromstats.get_gunicorn_processes")
def test_get_gunicorn_process_count(mock_get_processes):
    mock_get_processes.return_value = ["proc1", "proc2", "proc3"]
    assert get_gunicorn_process_count() == 3


@mock.patch("workers.localpromstats.get_all_zombies")
def test_get_zombie_process_count(mock_get_processes):
    mock_get_processes.return_value = ["zombie1", "zombie2"]
    assert get_zombie_process_count() == 2

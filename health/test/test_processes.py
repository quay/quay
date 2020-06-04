import mock

from health.processes import get_gunicorn_processes, get_all_zombies


@mock.patch("health.processes.psutil")
def test_get_gunicorn_processes(mock_psutil):
    """
    Verify that get_gunicorn_processes only returns gunicorn processes or an empty list.
    """

    p1 = mock.Mock()
    p1.name.return_value = "gunicorn"
    p1.status.return_value = "running"

    p2 = mock.Mock()
    p2.name.return_value = "not_gunicorn"
    p2.status.return_value = "running"

    p3 = mock.Mock()
    p3.name.return_value = "gunicorn"
    p3.status.return_value = "zombie"

    mock_psutil.process_iter.return_value = (p for p in (p1, p2, p3))

    # Only includes processes named "gunicorn"
    assert get_gunicorn_processes() == [p1, p3]
    assert p2 not in get_gunicorn_processes()


@mock.patch("health.processes.psutil")
def test_get_all_zombies(mock_psutil):
    """
    Verify that get_all_zombies only returns processes which are known to psutil to be zombies.
    """

    p1 = mock.Mock()
    p1.name.return_value = "gunicorn"
    p1.status.return_value = "running"

    p2 = mock.Mock()
    p2.name.return_value = "not_gunicorn"
    p2.status.return_value = "running"

    p3 = mock.Mock()
    p3.name.return_value = "gunicorn"
    p3.status.return_value = "zombie"

    mock_psutil.process_iter.return_value = (p for p in (p1, p2, p3))

    # Only includes processes with the zombie state
    assert get_all_zombies() == [p3]
    assert p2 not in get_all_zombies()
    assert p1 not in get_all_zombies()

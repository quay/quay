from test.fixtures import *

from data import database, model
from workers.repositoryactioncounter import RepositoryActionCountWorker


def test_repositoryactioncount(app):
    database.RepositoryActionCount.delete().execute()
    database.RepositorySearchScore.delete().execute()

    rac = RepositoryActionCountWorker()
    for repository in database.Repository.select():
        assert rac._count_repository_actions(repository)

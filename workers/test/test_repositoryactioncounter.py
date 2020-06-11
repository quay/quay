from data import model, database
from workers.repositoryactioncounter import RepositoryActionCountWorker

from test.fixtures import *


def test_repositoryactioncount(app):
    database.RepositoryActionCount.delete().execute()
    database.RepositorySearchScore.delete().execute()

    rac = RepositoryActionCountWorker()
    for repository in database.Repository.select():
        assert rac._count_repository_actions(repository)

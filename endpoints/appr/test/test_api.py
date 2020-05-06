import uuid

import pytest

from app import model_cache

from cnr.tests.conftest import *
from cnr.tests.test_apiserver import BaseTestServer
from cnr.tests.test_models import CnrTestModels

import data.appr_model.blob as appr_blob

from data.database import User
from data.model import organization, user
from endpoints.appr import registry  # Needed to register the endpoint
from endpoints.appr.cnr_backend import Channel, Package, QuayDB
from endpoints.appr.models_cnr import model as appr_app_model

from test.fixtures import *


def create_org(namespace, owner):
    try:
        User.get(username=namespace)
    except User.DoesNotExist:
        organization.create_organization(namespace, "%s@test.com" % str(uuid.uuid1()), owner)


class ChannelTest(Channel):
    @classmethod
    def dump_all(cls, package_class=None):
        result = []
        for repo in appr_app_model.list_applications(with_channels=True):
            for chan in repo.channels:
                result.append({"name": chan.name, "current": chan.current, "package": repo.name})
        return result


class PackageTest(Package):
    def _save(self, force, **kwargs):
        owner = user.get_user("devtable")
        create_org(self.namespace, owner)
        super(PackageTest, self)._save(force, user=owner, visibility="public")

    @classmethod
    def create_repository(cls, package_name, visibility, owner):
        ns, _ = package_name.split("/")
        owner = user.get_user("devtable")
        visibility = "public"
        create_org(ns, owner)
        return super(PackageTest, cls).create_repository(package_name, visibility, owner)

    @classmethod
    def dump_all(cls, blob_cls):
        result = []
        for repo in appr_app_model.list_applications(with_channels=True):
            package_name = repo.name
            for release in repo.releases:
                for mtype in cls.manifests(package_name, release):
                    package = appr_app_model.fetch_release(package_name, release, mtype)
                    blob = blob_cls.get(package_name, package.manifest.content.digest)
                    app_data = cls._apptuple_to_dict(package)
                    app_data.pop("digest")
                    app_data["channels"] = [
                        x.name
                        for x in appr_app_model.list_release_channels(
                            package_name, package.release, False
                        )
                    ]
                    app_data["blob"] = blob.b64blob
                    result.append(app_data)
        return result


@pytest.fixture(autouse=True)
def quaydb(monkeypatch, app):
    monkeypatch.setattr("endpoints.appr.cnr_backend.QuayDB.Package", PackageTest)
    monkeypatch.setattr("endpoints.appr.cnr_backend.Package", PackageTest)
    monkeypatch.setattr("endpoints.appr.registry.Package", PackageTest)
    monkeypatch.setattr("cnr.models.Package", PackageTest)

    monkeypatch.setattr("endpoints.appr.cnr_backend.QuayDB.Channel", ChannelTest)
    monkeypatch.setattr("endpoints.appr.registry.Channel", ChannelTest)
    monkeypatch.setattr("cnr.models.Channel", ChannelTest)


class TestServerQuayDB(BaseTestServer):
    DB_CLASS = QuayDB

    @property
    def token(self):
        return "basic ZGV2dGFibGU6cGFzc3dvcmQ="

    def test_search_package_match(self, db_with_data1, client):
        """ TODO: search cross namespace and package name """
        BaseTestServer.test_search_package_match(self, db_with_data1, client)

    def test_list_search_package_match(self, db_with_data1, client):
        url = self._url_for("api/v1/packages")
        res = self.Client(client, self.headers()).get(url, params={"query": "rocketchat"})
        assert res.status_code == 200
        assert len(self.json(res)) == 1

        # Run again for cache checking.
        res = self.Client(client, self.headers()).get(url, params={"query": "rocketchat"})
        assert res.status_code == 200
        assert len(self.json(res)) == 1

    def test_list_search_package_no_match(self, db_with_data1, client):
        url = self._url_for("api/v1/packages")
        res = self.Client(client, self.headers()).get(url, params={"query": "toto"})
        assert res.status_code == 200
        assert len(self.json(res)) == 0

    @pytest.mark.xfail
    def test_push_package_already_exists_force(self, db_with_data1, package_b64blob, client):
        """
        No force push implemented.
        """
        BaseTestServer.test_push_package_already_exists_force(
            self, db_with_data1, package_b64blob, client
        )

    @pytest.mark.xfail
    def test_delete_channel_release_absent_release(self, db_with_data1, client):
        BaseTestServer.test_delete_channel_release_absent_release(self, db_with_data1, client)

    @pytest.mark.xfail
    def test_get_absent_blob(self, newdb, client):
        pass


class TestQuayModels(CnrTestModels):
    DB_CLASS = QuayDB

    @pytest.mark.xfail
    def test_channel_delete_releases(self, db_with_data1):
        """
        Can't remove a release from the channel, only delete the channel entirely.
        """
        CnrTestModels.test_channel_delete_releases(self, db_with_data1)

    @pytest.mark.xfail
    def test_forbiddeb_db_reset(self, db_class):
        pass

    @pytest.mark.xfail
    def test_db_restore(self, newdb, dbdata1):
        # This will fail as long as CNR tests use a mediatype with v1.
        pass

    def test_save_package_exists_force(self, newdb, package_b64blob):
        model_cache.empty_for_testing()
        CnrTestModels.test_save_package_exists_force(self, newdb, package_b64blob)

    def test_save_package_exists(self, newdb, package_b64blob):
        model_cache.empty_for_testing()
        CnrTestModels.test_save_package_exists(self, newdb, package_b64blob)

    def test_save_package(self, newdb, package_b64blob):
        model_cache.empty_for_testing()
        CnrTestModels.test_save_package(self, newdb, package_b64blob)

    def test_save_package_bad_release(self, newdb):
        model_cache.empty_for_testing()
        CnrTestModels.test_save_package_bad_release(self, newdb)

    def test_push_same_blob(self, db_with_data1):
        p = db_with_data1.Package.get("titi/rocketchat", ">1.2", "kpm")
        assert p.package == "titi/rocketchat"
        assert p.release == "2.0.1"
        assert p.digest == "d3b54b7912fe770a61b59ab612a442eac52a8a5d8d05dbe92bf8f212d68aaa80"
        blob = db_with_data1.Blob.get("titi/rocketchat", p.digest)
        bdb = appr_blob.get_blob(p.digest, appr_app_model.models_ref)
        newblob = db_with_data1.Blob("titi/app2", blob.b64blob)
        p2 = db_with_data1.Package("titi/app2", "1.0.0", "helm", newblob)
        p2.save()
        b2db = appr_blob.get_blob(p2.digest, appr_app_model.models_ref)
        assert b2db.id == bdb.id

    def test_force_push_different_blob(self, db_with_data1):
        p = db_with_data1.Package.get("titi/rocketchat", "2.0.1", "kpm")
        assert p.package == "titi/rocketchat"
        assert p.release == "2.0.1"
        assert p.digest == "d3b54b7912fe770a61b59ab612a442eac52a8a5d8d05dbe92bf8f212d68aaa80"
        blob = db_with_data1.Blob.get(
            "titi/rocketchat", "72ed15c9a65961ecd034cca098ec18eb99002cd402824aae8a674a8ae41bd0ef"
        )
        p2 = db_with_data1.Package("titi/rocketchat", "2.0.1", "kpm", blob)
        p2.save(force=True)
        pnew = db_with_data1.Package.get("titi/rocketchat", "2.0.1", "kpm")
        assert pnew.package == "titi/rocketchat"
        assert pnew.release == "2.0.1"
        assert pnew.digest == "72ed15c9a65961ecd034cca098ec18eb99002cd402824aae8a674a8ae41bd0ef"

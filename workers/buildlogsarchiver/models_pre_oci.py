from data import model
from workers.buildlogsarchiver.models_interface import Build, BuildLogsArchiverWorkerDataInterface


class PreOCIModel(BuildLogsArchiverWorkerDataInterface):
    def get_archivable_build(self):
        build = model.build.get_archivable_build()
        if build is None:
            return None

        return Build(build.uuid, build.logs_archived)

    def mark_build_archived(self, build_uuid):
        return model.build.mark_build_archived(build_uuid)

    def create_build_for_testing(self):
        repo = model.repository.get_repository("devtable", "simple")
        access_token = model.token.create_access_token(repo, "admin")
        build = model.build.create_repository_build(repo, access_token, {}, None, "foo")
        build.phase = "error"
        build.save()
        return Build(build.uuid, build.logs_archived)

    def get_build(self, build_uuid):
        build = model.build.get_repository_build(build_uuid)
        if build is None:
            return None

        return Build(build.uuid, build.logs_archived)


pre_oci_model = PreOCIModel()

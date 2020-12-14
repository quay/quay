import grpc
import json
import logging

from google.protobuf.json_format import MessageToDict

from buildman.buildman_pb import buildman_pb2
from buildman.buildman_pb import buildman_pb2_grpc
from buildman.build_token import (
    BUILD_JOB_REGISTRATION_TYPE,
    BUILD_JOB_TOKEN_TYPE,
    InvalidBuildTokenException,
)
from data.database import BUILD_PHASE


logger = logging.getLogger(__name__)


class BuildManagerServicer(buildman_pb2_grpc.BuildManagerServicer):
    GRPC_PHASE_TO_BUILD_PHASE = {
        buildman_pb2.WAITING: BUILD_PHASE.WAITING,
        buildman_pb2.UNPACKING: BUILD_PHASE.UNPACKING,
        buildman_pb2.PULLING: BUILD_PHASE.PULLING,
        buildman_pb2.BUILDING: BUILD_PHASE.BUILDING,
        buildman_pb2.PUSHING: BUILD_PHASE.PUSHING,
        buildman_pb2.COMPLETE: BUILD_PHASE.COMPLETE,
        buildman_pb2.ERROR: BUILD_PHASE.ERROR,
    }

    def __init__(self, lifecycle_manager):
        self._lifecycle_manager = lifecycle_manager

    def _handle_error(self, context, code, msg):
        context.set_details(msg)
        context.set_code(code)

    def _decode_build_token(self, token, token_type):
        """Return the build token context,
        or an error message if there was an exception decoding the token."""
        msg = None
        try:
            decoded_token = self._lifecycle_manager.verify_build_token(
                token,
                token_type,
            )
        except InvalidBuildTokenException as ibte:
            msg = "Invalid build token: %s" % ibte
            return (None, msg)
        except Exception as e:
            msg = "Unknown build token exception: %s" % e
            return (None, msg)

        build_token_context = decoded_token.get("context", {})
        return (build_token_context, msg)

    def Ping(self, request, context):
        return buildman_pb2.PingReply(reply="pong")

    def RegisterBuildJob(self, request, context):
        """Registers a build job, returning a buildpack."""
        decoded_token, msg = self._decode_build_token(
            request.register_jwt,
            BUILD_JOB_REGISTRATION_TYPE,
        )
        if not decoded_token:
            self._handle_error(context, grpc.StatusCode.UNAUTHENTICATED, msg)
            return buildman_pb2.BuildPack()

        job_id = decoded_token["job_id"]
        max_build_time = decoded_token["expiration"]

        token, build_args = self._lifecycle_manager.start_job(job_id, max_build_time)
        if not token or not build_args:
            msg = "Build manager unable to start job"
            self._handle_error(context, grpc.StatusCode.INTERNAL, msg)
            return buildman_pb2.BuildPack()

        buildpack = buildman_pb2.BuildPack(
            job_jwt=token,
            context=build_args.get("context", ""),
            dockerfile_path=build_args.get("dockerfile_path", ""),
            repository=build_args.get("repository", ""),
            registry=build_args.get("registry", ""),
            pull_token=build_args.get("pull_token", ""),
            push_token=build_args.get("push_token", ""),
            tag_names=build_args.get("tag_names", ""),
            base_image=buildman_pb2.BuildPack.BaseImage(
                **build_args.get("base_image", {}),
            ),
        )

        git_package = build_args.get("git")
        build_package = build_args.get("build_package")
        if git_package:
            buildpack.git_package.url = git_package["url"]
            buildpack.git_package.sha = git_package["sha"]
            buildpack.git_package.private_key = git_package["private_key"]
        elif build_package:
            buildpack.package_url = build_args.get("build_package")
        else:
            self._handle_error(context, grpc.StatusCode.INTERNAL, "Invalid buildpack")
            return buildman_pb2.BuildPack()

        return buildpack

    def Heartbeat(self, request_iterator, context):
        """Updates the last heartbeat."""
        for req in request_iterator:
            decoded_token, msg = self._decode_build_token(
                req.job_jwt,
                BUILD_JOB_TOKEN_TYPE,
            )
            if not decoded_token:
                self._handle_error(context, grpc.StatusCode.UNAUTHENTICATED, msg)
                return buildman_pb2.HeartbeatResponse()

            job_id = decoded_token["job_id"]
            yield buildman_pb2.HeartbeatResponse(
                reply=self._lifecycle_manager.job_heartbeat(job_id)
            )

    def SetPhase(self, request, context):
        """Update the job phase."""
        decoded_token, msg = self._decode_build_token(
            request.job_jwt,
            BUILD_JOB_TOKEN_TYPE,
        )
        if not decoded_token:
            self._handle_error(context, grpc.StatusCode.UNAUTHENTICATED, msg)
            return buildman_pb2.SetPhaseResponse()

        job_id = decoded_token["job_id"]
        phase_metadata = {}
        if request.HasField("pull_metadata"):
            phase_metadata.update(
                MessageToDict(request.pull_metadata, preserving_proto_field_name=True)
            )

        updated = self._lifecycle_manager.update_job_phase(
            job_id,
            self.GRPC_PHASE_TO_BUILD_PHASE[request.phase],
            phase_metadata,
        )
        return buildman_pb2.SetPhaseResponse(
            success=updated, sequence_number=request.sequence_number
        )

    def LogMessage(self, request_iterator, context):
        """Tails log messages to build logs"""
        last_sequence_number = None
        for req in request_iterator:
            decoded_token, msg = self._decode_build_token(
                req.job_jwt,
                BUILD_JOB_TOKEN_TYPE,
            )
            if not decoded_token:
                self._handle_error(context, grpc.StatusCode.UNAUTHENTICATED, msg)
                return buildman_pb2.LogMessageResponse()

            job_id = decoded_token["job_id"]
            build_id = decoded_token["build_id"]

            # Attempt to update the heartbeat on log requests
            self._lifecycle_manager.job_heartbeat(job_id)

            sequence_number = req.sequence_number
            if last_sequence_number is not None and sequence_number <= last_sequence_number:
                logger.warning("Got unexcpected log sequence number for job %s", job_id)
                yield buildman_pb2.LogMessageResponse(success=False)
            else:
                log_message = req.log_message
                logged = self._lifecycle_manager.append_build_log(build_id, log_message)
                yield buildman_pb2.LogMessageResponse(
                    success=logged, sequence_number=sequence_number
                )
                last_sequence_number = sequence_number

    def DetermineCachedTag(self, request, context):
        decoded_token, msg = self._decode_build_token(
            request.job_jwt,
            BUILD_JOB_TOKEN_TYPE,
        )
        if not decoded_token:
            self._handle_error(context, grpc.StatusCode.UNAUTHENTICATED, msg)
            return buildman_pb2.CachedTag()

        build_id = decoded_token["build_id"]
        cached_tag = self._lifecycle_manager.determine_cached_tag(build_id, request.base_image_id)
        if not cached_tag:
            return buildman_pb2.CachedTag(CachedTag="")

        return buildman_pb2.CachedTag(CachedTag=cached_tag)

from abc import ABC, abstractmethod

from data.database import BUILD_PHASE


class BuildJobError(Exception):
    """Base error for build jobs."""


class BuildJobAlreadyExistsError(BuildJobError):
    """Raised when trying to create a job that already exists."""


class BuildJobDoesNotExistsError(BuildJobError):
    """Raised when trying to delete a job that does not exists."""


class BuildJobExpiredError(BuildJobError):
    """Raised when trying to update a job that has already expired."""


class BuildJobResult(object):
    """
    Build job result enum.
    """

    ERROR = "error"
    EXPIRED = "expired"
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    CANCELLED = "cancelled"


RESULT_PHASES = {
    BuildJobResult.ERROR: BUILD_PHASE.ERROR,
    BuildJobResult.EXPIRED: BUILD_PHASE.INTERNAL_ERROR,
    BuildJobResult.COMPLETE: BUILD_PHASE.COMPLETE,
    BuildJobResult.INCOMPLETE: BUILD_PHASE.INTERNAL_ERROR,
    BuildJobResult.CANCELLED: BUILD_PHASE.CANCELLED,
}


class BuildStateInterface(ABC):
    @abstractmethod
    def create_job(self, build_id, build_metadata):
        """Creates a new job for a build. Raises an error if the job already exists.
        Otherwise, returns a job_id. The job should get expired if the job is not scheduled within
        a time frame.
        """

    @abstractmethod
    def job_scheduled(self, job_id,  execution_id, max_startup_time):
        """Mark the job as scheduled with execution_id. If the job is not started after
        max_startup_time, the job should get expired.
        """

    @abstractmethod
    def job_unschedulable(self, job_id):
        """Delete job from state tracking. Called when unable to schedule the job.
        Raises BuildJobError if already called when the job has been successfully scheduled.
        """

    @abstractmethod
    def on_job_complete(self, build_job, job_result, executor_name, execution_id):
        """Invoke the callback to clean up the build execution:
        - Update the build phase
        - Set the final build job state: complete, cancelled, user_error, internal_error, cancelled
        - Clean up any resources used to execute the build: ec2 instances, k8s jobs, ...
        Returns False if there is an error, and should be tried again.
        """

    @abstractmethod
    def start_job(self, job_id, max_build_time):
        """Mark a job as started.
        Returns False if the job does not exists, or has already started.
        The worker's lifetime should be set to max_build_time
        """

    @abstractmethod
    def update_job_phase(self, job_id, phase):
        """Update the given job phase.
        Returns False if the given job does not exists or the job has been cancelled.
        """

    @abstractmethod
    def job_heartbeat(self, job_id):
        """Sends a heartbeat to a job, extending its expiration time.
        Returns True if the given job exists and its expiration was updated, False otherwise.
        """

    @abstractmethod
    def cancel_build(self, build_id):
        """
        Cancels the given build.
        """

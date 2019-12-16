from asyncio import coroutine


class BaseManager(object):
    """
    Base for all worker managers.
    """

    def __init__(
        self,
        register_component,
        unregister_component,
        job_heartbeat_callback,
        job_complete_callback,
        manager_hostname,
        heartbeat_period_sec,
    ):
        self.register_component = register_component
        self.unregister_component = unregister_component
        self.job_heartbeat_callback = job_heartbeat_callback
        self.job_complete_callback = job_complete_callback
        self.manager_hostname = manager_hostname
        self.heartbeat_period_sec = heartbeat_period_sec

    @coroutine
    def job_heartbeat(self, build_job):
        """
        Method invoked to tell the manager that a job is still running.

        This method will be called every few minutes.
        """
        self.job_heartbeat_callback(build_job)

    def overall_setup_time(self):
        """
        Returns the number of seconds that the build system should wait before allowing the job to
        be picked up again after called 'schedule'.
        """
        raise NotImplementedError

    def shutdown(self):
        """
        Indicates that the build controller server is in a shutdown state and that no new jobs or
        workers should be performed.

        Existing workers should be cleaned up once their jobs have completed
        """
        raise NotImplementedError

    @coroutine
    def schedule(self, build_job):
        """
        Schedules a queue item to be built.

        Returns a 2-tuple with (True, None) if the item was properly scheduled and (False, a retry
        timeout in seconds) if all workers are busy or an error occurs.
        """
        raise NotImplementedError

    def initialize(self, manager_config):
        """
        Runs any initialization code for the manager.

        Called once the server is in a ready state.
        """
        raise NotImplementedError

    @coroutine
    def build_component_ready(self, build_component):
        """
        Method invoked whenever a build component announces itself as ready.
        """
        raise NotImplementedError

    def build_component_disposed(self, build_component, timed_out):
        """
        Method invoked whenever a build component has been disposed.

        The timed_out boolean indicates whether the component's heartbeat timed out.
        """
        raise NotImplementedError

    @coroutine
    def job_completed(self, build_job, job_status, build_component):
        """
        Method invoked once a job_item has completed, in some manner.

        The job_status will be one of: incomplete, error, complete. Implementations of this method
        should call coroutine self.job_complete_callback with a status of Incomplete if they wish
        for the job to be automatically requeued.
        """
        raise NotImplementedError

    def num_workers(self):
        """
        Returns the number of active build workers currently registered.

        This includes those that are currently busy and awaiting more work.
        """
        raise NotImplementedError

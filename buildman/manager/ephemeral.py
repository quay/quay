# complete code
from buildman.jobutil.buildjob import BuildJob

class EphemeralBuildManager:
    def update_job_phase(self, job: BuildJob, phase: str):
        if phase == 'BUILDING':
            job.send_notification('build_start')
        # Add other phase transitions as needed
        pass
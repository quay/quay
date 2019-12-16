import logging
import datetime

from random import SystemRandom
from functools import wraps, partial
from copy import deepcopy
from jinja2.utils import generate_lorem_ipsum

from data.buildlogs import RedisBuildLogs


logger = logging.getLogger(__name__)
random = SystemRandom()


get_sentence = partial(generate_lorem_ipsum, html=False, n=1, min=5, max=10)


def maybe_advance_script(is_get_status=False):
    def inner_advance(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            advance_units = random.randint(1, 500)
            logger.debug("Advancing script %s units", advance_units)
            while advance_units > 0 and self.remaining_script:
                units = self.remaining_script[0][0]

                if advance_units > units:
                    advance_units -= units
                    self.advance_script(is_get_status)
                else:
                    break

            return func(self, *args, **kwargs)

        return wrapper

    return inner_advance


class TestBuildLogs(RedisBuildLogs):
    COMMAND_TYPES = [
        "FROM",
        "MAINTAINER",
        "RUN",
        "CMD",
        "EXPOSE",
        "ENV",
        "ADD",
        "ENTRYPOINT",
        "VOLUME",
        "USER",
        "WORKDIR",
    ]
    STATUS_TEMPLATE = {
        "total_commands": None,
        "current_command": None,
        "push_completion": 0.0,
        "pull_completion": 0.0,
    }

    def __init__(self, redis_config, namespace, repository, test_build_id, allow_delegate=True):
        super(TestBuildLogs, self).__init__(redis_config)
        self.namespace = namespace
        self.repository = repository
        self.test_build_id = test_build_id
        self.allow_delegate = allow_delegate
        self.remaining_script = self._generate_script()
        logger.debug("Total script size: %s", len(self.remaining_script))
        self._logs = []

        self._status = {}
        self._last_status = {}

    def advance_script(self, is_get_status):
        (_, log, status_wrapper) = self.remaining_script.pop(0)
        if log is not None:
            self._logs.append(log)

        if status_wrapper is not None:
            (phase, status) = status_wrapper

            if not is_get_status:
                from data import model

                build_obj = model.build.get_repository_build(self.test_build_id)
                build_obj.phase = phase
                build_obj.save()

                self._status = status
                self._last_status = status

    def _generate_script(self):
        script = []

        # generate the init phase
        script.append(self._generate_phase(400, "initializing"))
        script.extend(self._generate_logs(random.randint(1, 3)))

        # move to the building phase
        script.append(self._generate_phase(400, "building"))
        total_commands = random.randint(5, 20)
        for command_num in range(1, total_commands + 1):
            command_weight = random.randint(50, 100)
            script.append(self._generate_command(command_num, total_commands, command_weight))

            # we want 0 logs some percent of the time
            num_logs = max(0, random.randint(-50, 400))
            script.extend(self._generate_logs(num_logs))

        # move to the pushing phase
        script.append(self._generate_phase(400, "pushing"))
        script.extend(self._generate_push_statuses(total_commands))

        # move to the error or complete phase
        if random.randint(0, 1) == 0:
            script.append(self._generate_phase(400, "complete"))
        else:
            script.append(self._generate_phase(400, "error"))
            script.append(
                (1, {"message": "Something bad happened! Oh noes!", "type": self.ERROR}, None)
            )

        return script

    def _generate_phase(self, start_weight, phase_name):
        message = {
            "message": phase_name,
            "type": self.PHASE,
            "datetime": str(datetime.datetime.now()),
        }

        return (start_weight, message, (phase_name, deepcopy(self.STATUS_TEMPLATE)))

    def _generate_command(self, command_num, total_commands, command_weight):
        sentence = get_sentence()
        command = random.choice(self.COMMAND_TYPES)
        if command == "FROM":
            sentence = random.choice(
                [
                    "ubuntu",
                    "lopter/raring-base",
                    "quay.io/devtable/simple",
                    "quay.io/buynlarge/orgrepo",
                    "stackbrew/ubuntu:precise",
                ]
            )

        msg = {
            "message": "Step %s: %s %s" % (command_num, command, sentence),
            "type": self.COMMAND,
            "datetime": str(datetime.datetime.now()),
        }
        status = deepcopy(self.STATUS_TEMPLATE)
        status["total_commands"] = total_commands
        status["current_command"] = command_num
        return (command_weight, msg, ("building", status))

    @staticmethod
    def _generate_logs(count):
        others = []
        if random.randint(0, 10) <= 8:
            premessage = {
                "message": "\x1b[91m" + get_sentence(),
                "data": {"datetime": str(datetime.datetime.now())},
            }

            postmessage = {"message": "\x1b[0m", "data": {"datetime": str(datetime.datetime.now())}}

            count = count - 2
            others = [(1, premessage, None), (1, postmessage, None)]

        def get_message():
            return {"message": get_sentence(), "data": {"datetime": str(datetime.datetime.now())}}

        return others + [(1, get_message(), None) for _ in range(count)]

    @staticmethod
    def _compute_total_completion(statuses, total_images):
        percentage_with_sizes = float(len(list(statuses.values()))) / total_images
        sent_bytes = sum([status["current"] for status in list(statuses.values())])
        total_bytes = sum([status["total"] for status in list(statuses.values())])
        return float(sent_bytes) / total_bytes * percentage_with_sizes

    @staticmethod
    def _generate_push_statuses(total_commands):
        push_status_template = deepcopy(TestBuildLogs.STATUS_TEMPLATE)
        push_status_template["current_command"] = total_commands
        push_status_template["total_commands"] = total_commands

        push_statuses = []

        one_mb = 1 * 1024 * 1024

        num_images = random.randint(2, 7)
        sizes = [random.randint(one_mb, one_mb * 5) for _ in range(num_images)]

        image_completion = {}
        for image_num, image_size in enumerate(sizes):
            image_id = "image_id_%s" % image_num

            image_completion[image_id] = {
                "current": 0,
                "total": image_size,
            }

            for i in range(one_mb, image_size, one_mb):
                image_completion[image_id]["current"] = i
                new_status = deepcopy(push_status_template)
                completion = TestBuildLogs._compute_total_completion(image_completion, num_images)
                new_status["push_completion"] = completion
                push_statuses.append((250, None, ("pushing", new_status)))

        return push_statuses

    @maybe_advance_script()
    def get_log_entries(self, build_id, start_index):
        if build_id == self.test_build_id:
            return (len(self._logs), self._logs[start_index:])
        elif not self.allow_delegate:
            return None
        else:
            return super(TestBuildLogs, self).get_log_entries(build_id, start_index)

    @maybe_advance_script(True)
    def get_status(self, build_id):
        if build_id == self.test_build_id:
            returnable_status = self._last_status
            self._last_status = self._status
            return returnable_status
        elif not self.allow_delegate:
            return None
        else:
            return super(TestBuildLogs, self).get_status(build_id)

    def expire_log_entries(self, build_id):
        if build_id == self.test_build_id:
            return
        if not self.allow_delegate:
            return None
        else:
            return super(TestBuildLogs, self).expire_log_entries(build_id)

    def delete_log_entries(self, build_id):
        if build_id == self.test_build_id:
            return
        if not self.allow_delegate:
            return None
        else:
            return super(TestBuildLogs, self).delete_log_entries(build_id)

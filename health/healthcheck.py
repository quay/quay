import logging
import socket

import boto3.session

from auth.permissions import SuperUserPermission
from flask import session
from health.services import check_all_services, check_warning_services

logger = logging.getLogger(__name__)


def get_healthchecker(app, config_provider, instance_keys):
    """
    Returns a HealthCheck instance for the given app.
    """
    return HealthCheck.get_checker(app, config_provider, instance_keys)


class HealthCheck(object):
    def __init__(self, app, config_provider, instance_keys, instance_skips=None):
        self.app = app
        self.config_provider = config_provider
        self.instance_keys = instance_keys
        self.instance_skips = instance_skips or []

    def check_warning(self):
        """
        Conducts a check on the warnings, returning a dict representing the HealthCheck output and a
        number indicating the health check response code.
        """
        service_statuses = check_warning_services(self.app, [])
        return self.get_instance_health(service_statuses)

    def check_instance(self):
        """
        Conducts a check on this specific instance, returning a dict representing the HealthCheck
        output and a number indicating the health check response code.
        """
        service_statuses = check_all_services(self.app, self.instance_skips, for_instance=True)
        return self.get_instance_health(service_statuses)

    def check_endtoend(self):
        """
        Conducts a check on all services, returning a dict representing the HealthCheck output and a
        number indicating the health check response code.
        """
        service_statuses = check_all_services(self.app, [], for_instance=False)
        return self.calculate_overall_health(service_statuses)

    def get_instance_health(self, service_statuses):
        """
        For the given service statuses, returns a dict representing the HealthCheck output and a
        number indicating the health check response code.

        By default, this simply ensures that all services are reporting as healthy.
        """
        return self.calculate_overall_health(service_statuses)

    def calculate_overall_health(self, service_statuses, skip=None, notes=None):
        """
        Returns true if and only if all the given service statuses report as healthy.
        """
        is_healthy = True
        notes = notes or []

        service_statuses_bools = {}
        service_status_expanded = {}

        for service_name in service_statuses:
            status, message = service_statuses[service_name]

            service_statuses_bools[service_name] = status
            service_status_expanded[service_name] = {
                "status": status,
            }

            if not status:
                service_status_expanded[service_name]["failure"] = message
            elif message:
                service_status_expanded[service_name]["message"] = message

            if skip and service_name in skip:
                notes.append("%s skipped in compute health" % service_name)
                continue

            is_healthy = is_healthy and status

        data = {
            "services": service_statuses_bools,
        }

        expanded_data = {
            "services_expanded": service_status_expanded,
            "notes": notes,
            "is_testing": self.app.config["TESTING"],
            "config_provider": self.config_provider.provider_id,
            "local_service_key_id": self.instance_keys.local_key_id,
            "hostname": socket.gethostname(),
        }

        add_debug_information = SuperUserPermission().can() or session.get("health_debug", False)
        if add_debug_information:
            data.update(expanded_data)

        if not is_healthy:
            logger.warning("[FAILED HEALTH CHECK] %s", expanded_data)

        return (data, 200 if is_healthy else 503)

    @classmethod
    def get_checker(cls, app, config_provider, instance_keys):
        name = app.config["HEALTH_CHECKER"][0]
        parameters = app.config["HEALTH_CHECKER"][1] or {}

        for subc in cls.__subclasses__():
            if name in subc.check_names():
                return subc(app, config_provider, instance_keys, **parameters)

        raise Exception("Unknown health check with name %s" % name)


class LocalHealthCheck(HealthCheck):
    def __init__(self, app, config_provider, instance_keys):
        super(LocalHealthCheck, self).__init__(
            app, config_provider, instance_keys, ["redis", "storage"]
        )

    @classmethod
    def check_names(cls):
        return ["LocalHealthCheck"]


class RDSAwareHealthCheck(HealthCheck):
    def __init__(
        self,
        app,
        config_provider,
        instance_keys,
        access_key,
        secret_key,
        db_instance="quay",
        region="us-east-1",
    ):
        # Note: We skip the redis check because if redis is down, we don't want ELB taking the
        # machines out of service. Redis is not considered a high avaliability-required service.
        super(RDSAwareHealthCheck, self).__init__(
            app, config_provider, instance_keys, ["redis", "storage"]
        )

        self.access_key = access_key
        self.secret_key = secret_key
        self.db_instance = db_instance
        self.region = region

    @classmethod
    def check_names(cls):
        return ["RDSAwareHealthCheck", "ProductionHealthCheck"]

    def get_instance_health(self, service_statuses):
        skip = []
        notes = []

        # If the database is marked as unhealthy, check the status of RDS directly. If RDS is
        # reporting as available, then the problem is with this instance. Otherwise, the problem is
        # with RDS, and so we skip the DB status so we can keep this machine as 'healthy'.
        if "database" in service_statuses:
            db_healthy = service_statuses["database"]
            if not db_healthy:
                rds_status = self._get_rds_status()
                notes.append("DB reports unhealthy; RDS status: %s" % rds_status)

                # If the RDS is in any state but available, then we skip the DB check since it will
                # fail and bring down the instance.
                if rds_status != "available":
                    skip.append("database")

        return self.calculate_overall_health(service_statuses, skip=skip, notes=notes)

    def _get_rds_status(self):
        """
        Returns the status of the RDS instance as reported by AWS.
        """
        try:
            session = boto3.session.Session(
                aws_access_key_id=self.access_key,
                aws_secret_access_key=self.secret_key,
                region_name=self.region,
            )
            client = session.client("rds")
            instances = client.describe_db_instances()["DBInstances"]
            matches = [i for i in instances if i["DBInstanceIdentifier"] == self.db_instance]

            if not matches:
                return "error"

            status = matches[0]["DBInstanceStatus"]
            return status
        except:
            logger.exception("Exception while checking RDS status")
            return "error"

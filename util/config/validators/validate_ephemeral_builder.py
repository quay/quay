from buildman.manager.executor import EC2Executor, KubernetesExecutor

from util.config.validators import BaseValidator, ConfigValidationException


class EphemeralBuilderValidator(BaseValidator):
    name = "ephemeral-builder"

    @classmethod
    def validate(cls, validator_context):
        config = validator_context.config

        if not config.get("FEATURE_BUILD_SUPPORT", False):
            return

        if not config.get("BUILD_MANAGER"):
            return

        if len(build_manager_config) != 2:
            raise ConfigValidationException("Expected list of size two for build manager config")

        build_manager_config = config["BUILD_MANAGER"]
        if build_manager_config[0] != "ephemeral":
            return

        manager_config = build_manager_config[1]
        if not isinstance(manager_config, dict):
            raise ConfigValidationException("Expected dictionary as second parameter of config")

        executors = manager_config.get("EXECUTORS", [])
        if not executors:
            raise ConfigValidationException("At least one cluster must be defined")

        for executor_config in executors:
            executor_kind = executor_config.get("EXECUTOR")
            if executor_kind is None:
                raise ConfigValidationException("Missing executor kind")

            if executor_kind == "kubernetes":
                okay, err_msg = KubernetesExecutor.validate(executor_config)
                if not okay:
                    raise ConfigValidationException(err_msg)
            elif executor_kind == "ec2":
                okay, err_msg = EC2Executor.validate(executor_config)
                if not okay:
                    raise ConfigValidationException(err_msg)
            else:
                raise ConfigValidationException("Unknown executor kind: %s" % executor_kind)

import endpoints.v2.errors as errors


def test_base_class_tests():
    # we want to check all Exceptions for equal interface and handling
    initdict = {
        "error_code_str": "error_code_str",
        "message": "message",
        "detail": {"reason": "reason"},
        "http_status_code": 418,
        "repository": "repository",
        "scopes": "scopes",  # << this should be a list but wasn't implemented as specific
        "is_read_only": False,
    }
    for k in filter(
        lambda x: not any([x.startswith("__"), x == "bitmath"]), errors.__dict__.keys()
    ):
        if issubclass(getattr(errors, k), errors.V2RegistryException):
            # initialize the classes with the dict
            cls = getattr(errors, k)(**initdict)
            assert isinstance(cls.as_dict(), dict)
            assert sorted(cls.as_dict().keys()) in (
                ["code", "detail", "message"],
                ["code", "detail", "is_readonly", "message"],
            )
            assert cls._error_code_str == "error_code_str"
            assert cls.args == ("message",)  # << Exception class content
            assert cls._detail == {"reason": "reason"}
            if getattr(getattr(errors, k), "http_status_code", False) is not False:
                assert cls.http_status_code == getattr(errors, k).http_status_code
            else:
                assert cls.http_status_code == initdict["http_status_code"]
            assert cls.repository == "repository"
            assert cls.scopes == "scopes"
            assert cls.is_read_only == False


def test_base_class_tests_uninitialized():
    # we want to check all Exceptions for equal interface and handling on default
    for k in filter(
        lambda x: not any([x.startswith("__"), x == "bitmath"]), errors.__dict__.keys()
    ):
        if issubclass(getattr(errors, k), errors.V2RegistryException):
            # initialize the classes with the dict
            cls = getattr(errors, k)()
            assert isinstance(cls.as_dict(), dict)
            assert sorted(cls.as_dict().keys()) in (
                ["code", "detail", "message"],
                ["code", "detail", "is_readonly", "message"],
            )
            if getattr(getattr(errors, k), "http_status_code", False) is not False:
                assert cls.http_status_code == getattr(errors, k).http_status_code
            else:
                assert cls.http_status_code == 400
            assert cls.is_read_only == False

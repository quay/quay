def truthy_bool(param):
    return param not in {False, "false", "False", "0", "FALSE", "", "null"}

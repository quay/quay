from util.config.validator import EXTRA_CA_DIRECTORY


def strip_absolute_path_and_add_trailing_dir(path):
    """
  Removes the initial trailing / from the prefix path, and add the last dir one
  """
    return path[1:] + "/"


def tarinfo_filter_partial(prefix):
    def tarinfo_filter(tarinfo):
        # remove leading directory info
        tarinfo.name = tarinfo.name.replace(prefix, "")

        # ignore any directory that isn't the specified extra ca one:
        if tarinfo.isdir() and not tarinfo.name == EXTRA_CA_DIRECTORY:
            return None

        return tarinfo

    return tarinfo_filter

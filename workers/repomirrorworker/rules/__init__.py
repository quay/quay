from collections import namedtuple
from enum import IntEnum, unique


@unique
class RepoMirrorComplexRuleType(IntEnum):
    """
    Types of mirroring rules that can live under a complex rule.
    """

    """
    TAG_GLOB_CSV: Comma separated glob values (eg. "7.6,7.6-1.*").
    """
    TAG_GLOB_CSV = 1

    """
    AND: Both the left and right child rules must be true.
    """
    AND = 2

    """
    OR: Either the left or right child rule must be true.
    """
    OR = 3

    """
    NOT: Inverts the child rule.
    """
    NOT = 4

    """
    ALLOWED_VULNERABILITY_SEVERITIES: The allowed severities of vulnerabilities found
    in the tag's manifest that will still allow the tag to be mirrored. If the tag is
    mirrored from a registry that does not support vulnerability information sourcing,
    it is automatically skipped.
    """
    ALLOWED_VULNERABILITY_SEVERITIES = 5

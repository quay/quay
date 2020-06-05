# -*- coding: utf-8 -*-

from util.dockerfileparse import parse_dockerfile


def test_basic_parse():
    parsed = parse_dockerfile(
        """
    FROM someimage:latest
    RUN dosomething
  """
    )

    assert parsed.get_image_and_tag() == ("someimage", "latest")
    assert parsed.get_base_image() == "someimage"


def test_basic_parse_notag():
    parsed = parse_dockerfile(
        """
    FROM someimage
    RUN dosomething
  """
    )

    assert parsed.get_image_and_tag() == ("someimage", "latest")
    assert parsed.get_base_image() == "someimage"


def test_two_from_lines():
    parsed = parse_dockerfile(
        """
    FROM someimage:latest
    FROM secondimage:second
  """
    )

    assert parsed.get_image_and_tag() == ("secondimage", "second")
    assert parsed.get_base_image() == "secondimage"


def test_parse_comments():
    parsed = parse_dockerfile(
        """
    # FROM someimage:latest
    FROM anotherimage:foobar # This is a comment
    RUN dosomething
  """
    )

    assert parsed.get_image_and_tag() == ("anotherimage", "foobar")
    assert parsed.get_base_image() == "anotherimage"


def test_unicode_parse_as_ascii():
    parsed = parse_dockerfile(
        """
    FROM someimage:latest
    MAINTAINER José Schorr <jschorr@whatever.com>
  """
    )

    assert parsed.get_image_and_tag() == ("someimage", "latest")
    assert parsed.get_base_image() == "someimage"


def test_unicode_parse_as_unicode():
    parsed = parse_dockerfile(
        """
    FROM someimage:latest
    MAINTAINER José Schorr <jschorr@whatever.com>
  """
    )

    assert parsed.get_image_and_tag() == ("someimage", "latest")
    assert parsed.get_base_image() == "someimage"

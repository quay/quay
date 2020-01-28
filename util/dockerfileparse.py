import re

LINE_CONTINUATION_REGEX = re.compile(r"(\s)*\\(\s)*\n")
COMMAND_REGEX = re.compile("([A-Za-z]+)\s(.*)")

COMMENT_CHARACTER = "#"
LATEST_TAG = "latest"


class ParsedDockerfile(object):
    def __init__(self, commands):
        self.commands = commands

    def _get_commands_of_kind(self, kind):
        return [command for command in self.commands if command["command"] == kind]

    def _get_from_image_identifier(self):
        from_commands = self._get_commands_of_kind("FROM")
        if not from_commands:
            return None

        return from_commands[-1]["parameters"]

    @staticmethod
    def parse_image_identifier(image_identifier):
        """
        Parses a docker image identifier, and returns a tuple of image name and tag, where the tag
        is filled in with "latest" if left unspecified.
        """
        # Note:
        # Dockerfile images references can be of multiple forms:
        #   server:port/some/path
        #   somepath
        #   server/some/path
        #   server/some/path:tag
        #   server:port/some/path:tag
        parts = image_identifier.strip().split(":")

        if len(parts) == 1:
            # somepath
            return (parts[0], LATEST_TAG)

        # Otherwise, determine if the last part is a port
        # or a tag.
        if parts[-1].find("/") >= 0:
            # Last part is part of the hostname.
            return (image_identifier, LATEST_TAG)

        # Remaining cases:
        #   server/some/path:tag
        #   server:port/some/path:tag
        return (":".join(parts[0:-1]), parts[-1])

    def get_base_image(self):
        """
        Return the base image without the tag name.
        """
        return self.get_image_and_tag()[0]

    def get_image_and_tag(self):
        """
        Returns the image and tag from the FROM line of the dockerfile.
        """
        image_identifier = self._get_from_image_identifier()
        if image_identifier is None:
            return (None, None)

        return self.parse_image_identifier(image_identifier)


def strip_comments(contents):
    lines = []
    for line in contents.split("\n"):
        index = line.find(COMMENT_CHARACTER)
        if index < 0:
            lines.append(line)
            continue

        line = line[:index]
        lines.append(line)

    return "\n".join(lines)


def join_continued_lines(contents):
    return LINE_CONTINUATION_REGEX.sub("", contents)


def parse_dockerfile(contents):
    # If we receive ASCII, translate into unicode.
    if isinstance(contents, bytes):
        contents = contents.decode("utf-8")

    contents = join_continued_lines(strip_comments(contents))
    lines = [line.strip() for line in contents.split("\n") if len(line) > 0]

    commands = []
    for line in lines:
        match_command = COMMAND_REGEX.match(line)
        if match_command:
            command = match_command.group(1).upper()
            parameters = match_command.group(2)

            commands.append({"command": command, "parameters": parameters})

    return ParsedDockerfile(commands)

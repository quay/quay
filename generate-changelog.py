#!/usr/bin/env python
import re
import subprocess
import sys
from typing import Optional

TAGS_PATTERN = 'v[0-9]*'
START_TAG = 'v3.6.0-alpha.4'

branch_prefix_re = re.compile(r'^\[redhat-3\.[0-9]+\] ')
pull_request_suffix_re = re.compile(r' \(#\d+\)$')
github_issue_re = re.compile(r'#(\d+)')
jira_ticket_re = re.compile(r'(?:https://issues\.redhat\.com/browse/)?(PROJQUAY-\d+)')


def remove_branch_prefix(msg: str) -> str:
    return branch_prefix_re.sub('', msg)


def remove_pull_request_suffix(msg: str) -> str:
    return pull_request_suffix_re.sub('', msg)


def get_tags() -> list[str]:
    return subprocess.check_output(
        ['git', 'tag', '--list', TAGS_PATTERN],
    ).decode('utf-8').strip().split('\n')


def get_changes(tag: str, previous_tag: Optional[str], already_released: set[str]) -> list[str]:
    git_range = f'{previous_tag}..{tag}' if previous_tag else tag
    commits = subprocess.check_output(
        ['git', 'log', '--pretty=format:%s', git_range],
    ).decode('utf-8').strip()
    if not commits:
        return []
    result = []
    for msg in commits.split('\n'):
        msg = remove_branch_prefix(msg)
        if remove_pull_request_suffix(msg) in already_released:
            continue
        result.append(msg)
    return result


def parse_version(tag: str) -> tuple[int, int, int, int, str]:
    if tag.startswith('v'):
        tag = tag[1:]
    if '-' not in tag:
        core, suffix = tag, ''
        release = 0
    else:
        core, suffix = tag.split('-', 1)
        release = -1
    version = tuple(int(x) for x in core.split('.'))
    assert len(version) == 3
    # TODO: v3.6.0-alpha.9 and v3.6.0-alpha.10 are not sorted correctly, but
    # we don't have such tags yet.
    return (version[0], version[1], version[2], release, suffix)


def change_as_markdown(msg: str) -> str:
    msg = github_issue_re.sub(r'[#\1](https://github.com/quay/quay/issues/\1)', msg)
    msg = jira_ticket_re.sub(r'[\1](https://issues.redhat.com/browse/\1)', msg)
    return msg


def format_changes(changes: list[str]) -> str:
    if not changes:
        return '- *no changes*'

    class Block:
        def __init__(self, name, pattern, weight):
            if isinstance(pattern, str):
                self.pattern = re.compile(f'^(?:Revert ")*(?:{pattern})(?:\\((\\w+)\\))?: (.*)$', re.IGNORECASE)
            elif isinstance(pattern, re.Pattern):
                self.pattern = pattern
            else:
                raise TypeError(f'invalid pattern type: {type(pattern)}')
            self.name = name
            self.weight = weight
            self.changes = []

    blocks = [
        Block('Features', 'feat', 1),
        Block('User Interface', 'ui|[a-z.]+ ui', 2),
        Block('Security Scanner', 'secscan', 3),
        Block('Builders', 'builders|buildman', 4),
        Block('Bug Fixes', 'fix|bug', 101),
        Block('Documentation', 'docs?|documentation', 102),
        Block('Testing', 'test', 103),
        Block('Miscellaneous Tasks', 'chore|ci|build|dockerfile|release|deploy|dev|requirements(?:[.-][a-z.-]+)', 104),
        Block('Other', re.compile(r'(.*)'), 100),
    ]
    for msg in changes:
        for b in blocks:
            if b.pattern.match(msg):
                b.changes.append(msg)
                break
    blocks = sorted(blocks, key=lambda b: b.weight)
    out = ''
    for b in blocks:
        if b.changes:
            if out:
                out += '\n'
            out += f'### {b.name}\n'
            for c in b.changes:
                out += f'- {change_as_markdown(c)}\n'
    return out


def main():
    if len(sys.argv) != 2:
        print(f'Usage: {sys.argv[0]} NEW_RELEASE_TAG', file=sys.stderr)
        sys.exit(1)

    new_release_tag = sys.argv[1]
    new_release_version = parse_version(new_release_tag)
    start_version = parse_version(START_TAG)
    major_minor = '{}.{}'.format(*new_release_version[:2])

    tags = get_tags()
    new_release_tag_is_fake = False
    if new_release_tag not in tags:
        new_release_tag_is_fake = True
        tags += [new_release_tag]
    tags = sorted(tags, key=parse_version, reverse=True)

    selected_tags = []
    previous_version = new_release_version
    for tag in tags:
        v = parse_version(tag)
        if v > new_release_version or v[1] < previous_version[1] and v[2] > 0:
            continue
        if v <= start_version:
            break
        selected_tags.append(tag)
        previous_version = v

    changelogs = []
    previous_tag = START_TAG
    already_released = set()
    for tag in reversed(selected_tags):
        changes = get_changes('HEAD' if tag == new_release_tag and new_release_tag_is_fake else tag, previous_tag, already_released)
        if not changes and tag == new_release_tag:
            continue
        changelogs.append(f'''
<a name="{tag}"></a>
## [{tag}](https://github.com/quay/quay/compare/{previous_tag}...{tag})
{format_changes(changes)}
'''.strip())
        for msg in changes:
            already_released.add(remove_pull_request_suffix(msg))
        previous_tag = tag
    changelog = '\n\n'.join(reversed(changelogs))
    print(f'''
## Red Hat Quay Release Notes

[Red Hat Customer Portal](https://access.redhat.com/documentation/en-us/red_hat_quay/{major_minor}/html/red_hat_quay_release_notes/index)

{changelog}

## Historical Changelog
[CHANGELOG.md](https://github.com/quay/quay/blob/96b17b8338fb10ca2ed12e9bc920dcbba148289c/CHANGELOG.md)
'''.strip())


if __name__ == '__main__':
    main()

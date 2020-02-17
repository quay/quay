from bs4 import BeautifulSoup, Tag, NavigableString

_NEWLINE_INDICATOR = "<<<newline>>>"


def _bold(elem):
    elem.replace_with("*%s*" % elem.text)


def _unordered_list(elem):
    constructed = ""
    for child in elem.children:
        if child.name == "li":
            constructed += "* %s\n" % child.text
    elem.replace_with(constructed)


def _horizontal_rule(elem):
    elem.replace_with("%s\n" % ("-" * 80))


def _anchor(elem):
    elem.replace_with("[%s](%s)" % (elem.text, elem["href"]))


def _table(elem):
    elem.replace_with("%s%s" % (elem.text, _NEWLINE_INDICATOR))


_ELEMENT_REPLACER = {
    "b": _bold,
    "strong": _bold,
    "ul": _unordered_list,
    "hr": _horizontal_rule,
    "a": _anchor,
    "table": _table,
}


def _collapse_whitespace(text):
    new_lines = []
    lines = text.split("\n")
    for line in lines:
        if not line.strip():
            continue

        new_lines.append(line.strip().replace(_NEWLINE_INDICATOR, "\n"))

    return "\n".join(new_lines)


def html2text(html):
    soup = BeautifulSoup(html, "html5lib")
    _html2text(soup)
    return _collapse_whitespace(soup.text)


def _html2text(elem):
    for child in elem.children:
        if isinstance(child, Tag):
            _html2text(child)
        elif isinstance(child, NavigableString):
            # No changes necessary
            continue

    if elem.parent:
        if elem.name in _ELEMENT_REPLACER:
            _ELEMENT_REPLACER[elem.name](elem)

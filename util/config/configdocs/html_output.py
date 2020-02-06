class HtmlOutput:
    """
    Generates HTML from documentation model.
    """

    def __init__(self):
        pass

    def generate_output(self, parsed_items):
        """
        Returns generated HTML strin.
        """
        return (
            self.__get_html_begin() + self.__get_html_middle(parsed_items) + self.__get_html_end()
        )

    def __get_html_begin(self):
        return '<!DOCTYPE html>\n<html>\n<head>\n<link rel="stylesheet" type="text/css" href="style.css" />\n</head>\n<body>\n'

    def __get_html_end(self):
        return "</body>\n</html>"

    def __get_html_middle(self, parsed_items):
        output = ""
        root_item = parsed_items[0]

        # output += '<h1 class="root_title">{}</h1>\n'.format(root_item['title'])
        # output += '<h1 class="root_title">{}</h1>\n'.format(root_item['title'])
        output += "Schema for Red Hat Quay"

        output += '<ul class="level0">\n'
        last_level = 0
        is_root = True
        for item in parsed_items:
            level = item["level"] - 1
            if last_level < level:
                output += '<ul class="level{}">\n'.format(level)
            for i in range(last_level - level):
                output += "</ul>\n"
            last_level = level
            output += self.__get_html_item(item, is_root)
            is_root = False
        output += "</ul>\n"
        return output

    def __get_required_field(self, parsed_item):
        return "required" if parsed_item["required"] else ""

    def __get_html_item(self, parsed_item, is_root):
        item = '<li class="schema item"> \n'
        item += '<div class="name">{}</div> \n'.format(parsed_item["name"])
        item += '<div class="type">[{}]</div> \n'.format(parsed_item["type"])
        item += '<div class="required">{}</div> \n'.format(self.__get_required_field(parsed_item))
        item += '<div class="docs">\n' if not is_root else '<div class="root_docs">\n'
        item += '<div class="title">{}</div>\n'.format(parsed_item["title"])
        item += ": " if parsed_item["title"] != "" and parsed_item["description"] != "" else ""
        item += '<div class="description">{}</div>\n'.format(parsed_item["description"])
        item += (
            '<div class="enum">enum: {}</div>\n'.format(parsed_item["enum"])
            if parsed_item["enum"] != ""
            else ""
        )
        item += (
            '<div class="minItems">Min Items: {}</div>\n'.format(parsed_item["minItems"])
            if parsed_item["type"] == "array" and parsed_item["minItems"] != "None"
            else ""
        )
        item += (
            '<div class="uniqueItems">Unique Items: {}</div>\n'.format(parsed_item["uniqueItems"])
            if parsed_item["type"] == "array" and parsed_item["uniqueItems"]
            else ""
        )
        item += (
            '<div class="pattern">Pattern: {}</div>\n'.format(parsed_item["pattern"])
            if parsed_item["pattern"] != "None" and parsed_item["pattern"] != ""
            else ""
        )
        item += (
            '<div class="x-reference"><a href="{}">Reference: {}</a></div>\n'.format(
                parsed_item["x-reference"], parsed_item["x-reference"]
            )
            if parsed_item["x-reference"] != ""
            else ""
        )
        item += (
            '<div class="x-example">Example: <code>{}</code></div>\n'.format(
                parsed_item["x-example"]
            )
            if parsed_item["x-example"] != ""
            else ""
        )
        item += "</div>\n"
        item += "</li>\n"
        return item

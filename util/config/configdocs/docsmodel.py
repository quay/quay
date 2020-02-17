import json
import collections


class ParsedItem(dict):
    """
    Parsed Schema item.
    """

    def __init__(self, json_object, name, required, level):
        """
        Fills dict with basic item information.
        """
        super(ParsedItem, self).__init__()
        self["name"] = name
        self["title"] = json_object.get("title", "")
        self["type"] = json_object.get("type")
        self["description"] = json_object.get("description", "")
        self["level"] = level
        self["required"] = required
        self["x-reference"] = json_object.get("x-reference", "")
        self["x-example"] = json_object.get("x-example", "")
        self["pattern"] = json_object.get("pattern", "")
        self["enum"] = json_object.get("enum", "")


class DocsModel:
    """
    Documentation model and Schema Parser.
    """

    def __init__(self):
        self.__parsed_items = None

    def parse(self, json_object):
        """
        Returns multi-level list of recursively parsed items.
        """

        self.__parsed_items = list()
        self.__parse_schema(json_object, "root", True, 0)
        return self.__parsed_items

    def __parse_schema(self, schema, name, required, level):
        """
        Parses schema, which type is object, array or leaf.

        Appends new ParsedItem to self.__parsed_items lis
        """
        parsed_item = ParsedItem(schema, name, required, level)
        self.__parsed_items.append(parsed_item)
        required = schema.get("required", [])

        if "enum" in schema:
            parsed_item["item"] = schema.get("enum")
        item_type = schema.get("type")
        if item_type == "object" and name != "DISTRIBUTED_STORAGE_CONFIG":
            self.__parse_object(parsed_item, schema, required, level)
        elif item_type == "array":
            self.__parse_array(parsed_item, schema, required, level)
        else:
            parse_leaf(parsed_item, schema)

    def __parse_object(self, parsed_item, schema, required, level):
        """
        Parses schema of type object.
        """
        for key, value in schema.get("properties", {}).items():
            self.__parse_schema(value, key, key in required, level + 1)

    def __parse_array(self, parsed_item, schema, required, level):
        """
        Parses schema of type array.
        """
        items = schema.get("items")
        parsed_item["minItems"] = schema.get("minItems", None)
        parsed_item["maxItems"] = schema.get("maxItems", None)
        parsed_item["uniqueItems"] = schema.get("uniqueItems", False)
        if isinstance(items, dict):
            # item is single schema describing all elements in an array
            self.__parse_schema(items, "array item", required, level + 1)

        elif isinstance(items, list):
            # item is a list of schemas
            for index, list_item in enumerate(items):
                self.__parse_schema(
                    list_item, "array item {}".format(index), index in required, level + 1
                )


def parse_leaf(parsed_item, schema):
    """
    Parses schema of a number and a string.
    """
    if parsed_item["name"] != "root":
        parsed_item["description"] = schema.get("description", "")
        parsed_item["x-reference"] = schema.get("x-reference", "")
        parsed_item["pattern"] = schema.get("pattern", "")
        parsed_item["enum"] = ", ".join(schema.get("enum", "")).encode()

        ex = schema.get("x-example", "")
        if isinstance(ex, list):
            parsed_item["x-example"] = ", ".join(ex).encode()
        elif isinstance(ex, collections.OrderedDict):
            parsed_item["x-example"] = json.dumps(ex)
        else:
            parsed_item["x-example"] = ex

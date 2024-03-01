import os

import jinja2
import yaml
from jsonschema import ValidationError
from jsonschema import validate as validate_schema

QUAYPATH = os.getenv("QUAYPATH", ".")
QUAYDIR = os.getenv("QUAYDIR", "/")
QUAYCONF_DIR = os.getenv("QUAYCONF", os.path.join(QUAYDIR, QUAYPATH, "conf"))
STATIC_DIR = os.path.join(QUAYDIR, "static")

# Define meta schema for rate limiting setup
META_SCHEMA = {
    "type": "object",
    "title": "Rate limiting schema",
    "additionalProperties": {"type": "object"},
    "required": [
        "http1",
        "http2",
        "namespaced",
    ],
    "properties": {
        "http1": {
            "type": "object",
            "required": [
                "v2",
                "registry",
                "api_resources",
            ],
            "properties": {
                "v2": {
                    "type": "number",
                    "description": "Rate limit v2 endpoint for HTTP/1 connections.",
                    "minimum": 1,
                },
                "registry": {
                    "type": "number",
                    "description": "Rate limit registry operations.",
                    "minimum": 1,
                },
                "api_resources": {
                    "type": "number",
                    "description": "Rate limit access to API operations.",
                    "minimum": 1,
                },
            },
        },
        "http2": {
            "type": "object",
            "required": [
                "v2",
                "registry",
                "api_resources",
            ],
            "properties": {
                "v2": {
                    "type": "number",
                    "description": "Rate limit v2 endpoint for HTTP/2 connections.",
                    "minimum": 1,
                },
                "registry": {
                    "type": "number",
                    "description": "Rate limit registry operations for HTTP/2 connections.",
                    "minimum": 1,
                },
                "api_resources": {
                    "type": "number",
                    "description": "Rate limit access to API operations for HTTP/2 connections.",
                    "minimum": 1,
                },
            },
        },
        "namespaced": {
            "type": "object",
            "required": [
                "http1_v2",
                "http2_v2",
                "http1_registry",
                "http2_registry",
                "http1_api_resources",
                "http2_api_resources",
            ],
            "properties": {
                "http1_v2": {
                    "type": "number",
                    "description": "Rate limit v2 endpoint for HTTP/1 connections for specific namespaces.",
                    "minimum": 1,
                },
                "http2_v2": {
                    "type": "number",
                    "description": "Rate limit v2 endpoint for HTTP/2 connections for specific namespaces.",
                    "minimum": 1,
                },
                "http1_registry": {
                    "type": "number",
                    "description": "Rate limit registry operations for HTTP/1 connections for specific namespaces.",
                    "minimum": 1,
                },
                "http2_registry": {
                    "type": "number",
                    "description": "Rate limit registry operations for HTTP/2 connections for specific namespaces.",
                    "minimum": 1,
                },
                "http1_api_resources": {
                    "type": "number",
                    "description": "Rate limit access to API resources for HTTP/1 connections for specific namespaces.",
                    "minimum": 1,
                },
                "http2_api_resources": {
                    "type": "number",
                    "description": "Rate limit access to API resources for HTTP/2 connections for specific namespaces.",
                    "minimum": 1,
                },
            },
        },
    },
}


def validate_config(config):
    config = config or {}
    to_validate = config.get("RATE_LIMITS")
    try:
        validate_schema(to_validate, META_SCHEMA)
    except ValidationError as ve:
        print("Failed to validate rate limit setup: {}".format(ve))
        exit(1)


if __name__ == "__main__":
    if os.path.exists(os.path.join(QUAYCONF_DIR, "stack/config.yaml")):
        with open(os.path.join(QUAYCONF_DIR, "stack/config.yaml"), "r") as f:
            config = yaml.safe_load(f)
    else:
        config = None
    if config.get("FEATURE_RATE_LIMITS") == True:
        validate_config(config)

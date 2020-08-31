import logging
import logging.config
import urllib.request, urllib.error, urllib.parse
import re
import os
import hashlib

from _init import STATIC_FONTS_DIR, STATIC_WEBFONTS_DIR, STATIC_LDN_DIR
from util.log import logfile_path


LOCAL_PATH = "/static/ldn/"

MAX_RETRY_COUNT = 3

EXTERNAL_JS = [
    "code.jquery.com/jquery.js",
    "netdna.bootstrapcdn.com/bootstrap/3.3.2/js/bootstrap.min.js",
    "ajax.googleapis.com/ajax/libs/angularjs/1.5.3/angular.min.js",
    "ajax.googleapis.com/ajax/libs/angularjs/1.5.3/angular-route.min.js",
    "ajax.googleapis.com/ajax/libs/angularjs/1.5.3/angular-sanitize.min.js",
    "ajax.googleapis.com/ajax/libs/angularjs/1.5.3/angular-animate.min.js",
    "ajax.googleapis.com/ajax/libs/angularjs/1.5.3/angular-cookies.min.js",
    "cdn.jsdelivr.net/g/momentjs",
    "cdnjs.cloudflare.com/ajax/libs/bootstrap-datepicker/1.2.0/js/bootstrap-datepicker.min.js",
    "cdnjs.cloudflare.com/ajax/libs/bootstrap-datetimepicker/4.17.37/js/bootstrap-datetimepicker.min.js",
    "cdn.jsdelivr.net/g/bootbox@4.1.0,underscorejs@1.5.2,restangular@1.2.0,d3js@3.3.3",
    "cdn.ravenjs.com/3.1.0/angular/raven.min.js",
    "cdn.jsdelivr.net/cal-heatmap/3.3.10/cal-heatmap.min.js",
    "cdnjs.cloudflare.com/ajax/libs/angular-recaptcha/4.1.3/angular-recaptcha.min.js",
    "cdnjs.cloudflare.com/ajax/libs/ng-tags-input/3.1.1/ng-tags-input.min.js",
    "cdnjs.cloudflare.com/ajax/libs/corejs-typeahead/1.1.1/typeahead.bundle.min.js",
]

EXTERNAL_CSS = [
    "use.fontawesome.com/releases/v5.0.4/css/all.css",
    "netdna.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.css",
    "netdna.bootstrapcdn.com/bootstrap/3.3.2/css/bootstrap.min.css",
    "fonts.googleapis.com/css?family=Source+Sans+Pro:300,400,700",
    "s3.amazonaws.com/cdn.core-os.net/icons/core-icons.css",
    "cdnjs.cloudflare.com/ajax/libs/bootstrap-datetimepicker/4.17.37/css/bootstrap-datetimepicker.min.css",
    "cdn.jsdelivr.net/cal-heatmap/3.3.10/cal-heatmap.css",
    "cdnjs.cloudflare.com/ajax/libs/ng-tags-input/3.1.1/ng-tags-input.min.css",
]

EXTERNAL_FONTS = [
    "netdna.bootstrapcdn.com/font-awesome/4.7.0/fonts/fontawesome-webfont.eot?v=4.7.0",
    "netdna.bootstrapcdn.com/font-awesome/4.7.0/fonts/fontawesome-webfont.woff?v=4.7.0",
    "netdna.bootstrapcdn.com/font-awesome/4.7.0/fonts/fontawesome-webfont.woff2?v=4.7.0",
    "netdna.bootstrapcdn.com/font-awesome/4.7.0/fonts/fontawesome-webfont.ttf?v=4.7.0",
    "netdna.bootstrapcdn.com/font-awesome/4.7.0/fonts/fontawesome-webfont.svg?v=4.7.0",
    "netdna.bootstrapcdn.com/bootstrap/3.3.2/fonts/glyphicons-halflings-regular.eot",
    "netdna.bootstrapcdn.com/bootstrap/3.3.2/fonts/glyphicons-halflings-regular.woff2",
    "netdna.bootstrapcdn.com/bootstrap/3.3.2/fonts/glyphicons-halflings-regular.woff",
    "netdna.bootstrapcdn.com/bootstrap/3.3.2/fonts/glyphicons-halflings-regular.ttf",
    "netdna.bootstrapcdn.com/bootstrap/3.3.2/fonts/glyphicons-halflings-regular.svg",
]

EXTERNAL_WEBFONTS = [
    "use.fontawesome.com/releases/v5.0.4/webfonts/fa-regular-400.ttf",
    "use.fontawesome.com/releases/v5.0.4/webfonts/fa-regular-400.woff",
    "use.fontawesome.com/releases/v5.0.4/webfonts/fa-regular-400.woff2",
    "use.fontawesome.com/releases/v5.0.4/webfonts/fa-solid-900.ttf",
    "use.fontawesome.com/releases/v5.0.4/webfonts/fa-solid-900.woff",
    "use.fontawesome.com/releases/v5.0.4/webfonts/fa-solid-900.woff2",
    "use.fontawesome.com/releases/v5.0.4/webfonts/fa-brands-400.ttf",
    "use.fontawesome.com/releases/v5.0.4/webfonts/fa-brands-400.woff",
    "use.fontawesome.com/releases/v5.0.4/webfonts/fa-brands-400.woff2",
]

EXTERNAL_CSS_FONTS = [
    "s3.amazonaws.com/cdn.core-os.net/icons/core-icons.eot",
    "s3.amazonaws.com/cdn.core-os.net/icons/core-icons.woff",
    "s3.amazonaws.com/cdn.core-os.net/icons/core-icons.ttf",
    "s3.amazonaws.com/cdn.core-os.net/icons/core-icons.svg",
]


logger = logging.getLogger(__name__)


def get_external_javascript(local=False):
    if local:
        return [LOCAL_PATH + format_local_name(src) for src in EXTERNAL_JS]

    return ["//" + src for src in EXTERNAL_JS]


def get_external_css(local=False, exclude=None):
    exclude = exclude or []
    if local:
        return [LOCAL_PATH + format_local_name(src) for src in EXTERNAL_CSS if src not in exclude]

    return ["//" + src for src in EXTERNAL_CSS if src not in exclude]


def format_local_name(url):
    filename = url.split("/")[-1]
    filename = re.sub(r"[+,?@=:]", "", filename)

    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[0:12]
    filename += "-" + url_hash

    if not filename.endswith(".css") and not filename.endswith(".js"):
        if filename.find("css") >= 0:
            filename = filename + ".css"
        else:
            filename = filename + ".js"

    return filename


def _download_url(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Quay (External Library Downloader)",})
    for index in range(0, MAX_RETRY_COUNT):
        try:
            response = urllib.request.urlopen(req)
            return response.read()
        except urllib.error.URLError:
            logger.exception(
                "Got exception when trying to download URL %s (try #%s)", url, index + 1
            )

    raise Exception("Aborted due to maximum retries reached")


if __name__ == "__main__":
    logging.config.fileConfig(logfile_path(debug=False), disable_existing_loggers=False)

    resources = [
        (STATIC_LDN_DIR, EXTERNAL_JS + EXTERNAL_CSS, True),
        (STATIC_LDN_DIR, EXTERNAL_CSS_FONTS, False),
        (STATIC_FONTS_DIR, EXTERNAL_FONTS, False),
        (STATIC_WEBFONTS_DIR, EXTERNAL_WEBFONTS, False),
    ]

    for local_directory, urls, requires_hashing in resources:
        for url in urls:
            if requires_hashing:
                filename = format_local_name(url)
            else:
                filename = os.path.basename(url).split("?")[0]

            path = os.path.join(local_directory, filename)
            print("Downloading %s to %s" % (url, path))
            contents = _download_url("https://" + url)

            with open(path, "wb") as local_file:
                local_file.write(contents)

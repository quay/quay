import logging
import re
import sys
from argparse import ArgumentParser
from urllib.parse import urlparse

import boto3
import boto3.session
import requests
import yaml
from botocore.client import Config
from peewee import *


class MyParser(ArgumentParser):
    def error(self, message):
        sys.stdout.write("Error: %s\n" % message)
        self.print_help()
        sys.exit(2)


STORAGE_ENGINE_LIST = [
    "RadosGWStorage",
    "S3Storage",
    "IBMCloudStorage",
    "RHOCSStorage",
]


def main():
    parser = MyParser(
        prog="python-blob-check",
        description="Check blob status between Quay db and storage",
    )

    parser.add_argument("filename", help="Path to Quay's config.yaml file")
    parser.add_argument("-d", "--debug", help="Turn S3 debugging on", action="store_true")
    args = parser.parse_args()
    print("Quay config path: {}".format(args.__dict__["filename"]))

    with open(args.__dict__["filename"]) as file_stream:
        try:
            config = yaml.safe_load(file_stream)
        except yaml.YAMLError as e:
            print("Encountered error during parsing: {}".format(e))
            sys.exit(2)

    # We need to figure out what the name of the first storage engine is, because we'll only check 1st storage config, and only if it's S3 compatible.
    # This is ugly, but works.
    # We will check only the first listed configuration, assume that's the primary one.
    storage_config = config["DISTRIBUTED_STORAGE_CONFIG"][
        list(config["DISTRIBUTED_STORAGE_CONFIG"].keys())[0]
    ]

    if storage_config[0] not in STORAGE_ENGINE_LIST:
        print("Storage engine must be S3 compatible.")
        sys.exit(2)

    db_uri = urlparse(config["DB_URI"])

    if db_uri.scheme != "postgresql":
        print("This utility only supports PostgreSQL as database backend.")
        sys.exit(2)

    # split net location by the `@` symbol
    # last parameter in the list should always be our hostname
    # ugly, but seems to work
    netloc_list = re.split(r"(@)", db_uri.netloc)

    if ":" in netloc_list[-1]:
        DB_HOSTNAME = netloc_list[-1].split(":")[0]
        DB_PORT = netloc_list[-1].split(":")[1]
    else:
        DB_HOSTNAME = netloc_list[-1]
        DB_PORT = 5432

    # we have to remove the last `@` symbol from the location list to extract the username and password
    DB_USERNAME = "".join(netloc_list[:-2]).split(":")[0]
    DB_PASSWORD = "".join(netloc_list[:-2]).split(":")[1]
    DB_NAME = db_uri.path.split("/")[1]

    print("Establishing connection with database on hostname {}.".format(DB_HOSTNAME))

    db = PostgresqlDatabase(
        DB_NAME, user=DB_USERNAME, password=DB_PASSWORD, host=DB_HOSTNAME, port=DB_PORT
    )
    db.connect()

    cursor = db.execute_sql("SELECT content_checksum FROM imagestorage;")
    blobs = cursor.fetchall()

    print("Found {} blobs in imagestorage table.".format(len(blobs)))

    print("Trying to establish a connection to the storage provider.")

    if args.debug:
        boto3.set_stream_logger("", logging.DEBUG)
    if storage_config[0] == "S3Storage":
        s3_client = boto3.client(
            "s3",
            region_name=storage_config[1]["s3_region"],
            aws_access_key_id=storage_config[1]["s3_access_key"],
            aws_secret_access_key=storage_config[1]["s3_secret_key"],
            endpoint_url="https://s3.{region}.amazonaws.com".format(
                region=storage_config[1]["s3_region"]
            ),
            config=Config(signature_version="s3v4"),
        )
    else:
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=storage_config[1]["access_key"],
            aws_secret_access_key=storage_config[1]["secret_key"],
            endpoint_url="https://{hostname}:{port}".format(
                hostname=storage_config[1]["hostname"], port=storage_config[1]["port"]
            )
            if storage_config[1]["is_secure"] == True
            else "http://{hostname}:{port}".format(
                hostname=storage_config[1]["hostname"], port=storage_config[1]["port"]
            ),
            config=Config(signature_version="s3v4"),
        )

    missing_blobs = []
    print("Searching for missing blobs...")
    for blob in blobs:
        blobname = blob[0].split(":")[1]
        blobdir = blobname[:2]
        url = s3_client.generate_presigned_url(
            ClientMethod="head_object",
            Params={
                "Bucket": storage_config[1]["s3_bucket"]
                if storage_config[0] == "S3Storage"
                else storage_config[1]["bucket_name"],
                "Key": "{path}/sha256/{dir}/{blobname}".format(
                    path=storage_config[1]["storage_path"][1:],
                    dir=blobdir,
                    blobname=blobname,
                ),
            },
        )

        response = requests.head(url)
        if response.status_code != 200:
            missing_blobs.append("sha256:" + blobname)
    if missing_blobs:
        print("Found {} missing blobs.".format(len(missing_blobs)))
        print("Complete list: {}".format(missing_blobs))
    else:
        print("All blobs OK!")


if __name__ == "__main__":
    main()

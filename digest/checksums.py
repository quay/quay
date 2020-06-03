import hashlib
import logging
import tarfile


TarError = tarfile.TarError
logger = logging.getLogger(__name__)


def sha256_file(fp, data=None):
    h = hashlib.sha256(data.encode("utf-8") if data else "".encode("utf-8"))
    if not fp:
        return h.hexdigest()
    while True:
        buf = fp.read(4096)
        if not buf:
            break
        h.update(buf)
    return h.hexdigest()


def sha256_string(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def compute_tarsum(fp, json_data):
    header_fields = (
        "name",
        "mode",
        "uid",
        "gid",
        "size",
        "mtime",
        "type",
        "linkname",
        "uname",
        "gname",
        "devmajor",
        "devminor",
    )
    tar = None
    hashes = []
    try:
        tar = tarfile.open(mode="r|*", fileobj=fp)
        for member in tar:
            header = ""
            for field in header_fields:
                value = getattr(member, field)
                if field == "type":
                    field = "typeflag"
                elif field == "name":
                    if member.isdir() and not value.endswith("/"):
                        value += "/"
                header += "{0}{1}".format(field, value)
            h = None
            try:
                if member.size > 0:
                    f = tar.extractfile(member)
                    h = sha256_file(f, header)
                else:
                    h = sha256_string(header)
            except KeyError:
                h = sha256_string(header)
            hashes.append(h)
        hashes.sort()
    except tarfile.ReadError as e:
        # TODO (kleesc): Need to add a test for empty tarfile
        if str(e) != "empty file":
            # NOTE(samalba): ignore empty tarfiles but still let the tarsum
            # compute with json data
            raise
    finally:
        if tar:
            tar.close()
    data = json_data + "".join(hashes)
    tarsum = "tarsum+sha256:{0}".format(sha256_string(data))
    logger.debug("checksums.compute_tarsum: return %s", tarsum)
    return tarsum


def simple_checksum_handler(json_data):
    h = hashlib.sha256(json_data.encode("utf8") + b"\n")

    def fn(buf):
        h.update(buf)

    return h, fn


def content_checksum_handler():
    h = hashlib.sha256()

    def fn(buf):
        h.update(buf.encode("utf-8"))

    return h, fn


def compute_simple(fp, json_data):
    data = json_data + "\n"
    return "sha256:{0}".format(sha256_file(fp, data))


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: {0} json_file layer_file".format(sys.argv[0]))
        sys.exit(1)
    json_data = open(sys.argv[1]).read()
    fp = open(sys.argv[2])
    print(compute_simple(fp, json_data))
    print(compute_tarsum(fp, json_data))

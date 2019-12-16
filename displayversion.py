from _init import __version__, __gitrev__


def displayversion():
    version_string = ("Quay %s (%s)" % (__version__, __gitrev__.strip())).strip()

    print("=" * (len(version_string) + 4))
    print("= " + version_string + " =")
    print("=" * (len(version_string) + 4))
    print("")


if __name__ == "__main__":
    displayversion()

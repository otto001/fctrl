
def read_all(path):
    """read full file (non binary)"""
    try:
        return open(path).read()
    except OSError:
        return None


def write(path, content):
    try:
        open(path, "w").write(str(content))
    except PermissionError:
        import __main__
        print("insufficent permission", path, content, __main__.__file__)
        raise
    except (FileNotFoundError, OSError):
        return False
    return True

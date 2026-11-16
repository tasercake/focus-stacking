CONTRACT_VERSION = 2


def main(argv=None):
    from .cli import main as entrypoint
    return entrypoint(argv)

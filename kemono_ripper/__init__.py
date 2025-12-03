from .main import main_async, main_sync
from .version import APP_NAME, APP_REVISION, APP_VER_MAJOR, APP_VER_SUB, APP_VERSION


def main(argv=None):
    exit(main_sync(argv))


__all__ = (
    'APP_NAME',
    'APP_REVISION',
    'APP_VERSION',
    'APP_VER_MAJOR',
    'APP_VER_SUB',
    'main',
    'main_async',
    'main_sync',
)

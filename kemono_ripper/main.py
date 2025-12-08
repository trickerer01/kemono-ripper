# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import json
import sys
from asyncio import get_running_loop, run, sleep
from collections.abc import Sequence
from contextlib import AsyncExitStack

from .api import DownloadMode, Kemono, KemonoAPIError, KemonoOptions
from .cmdargs import MODULE, HelpPrintExitException, parse_logging_args, prepare_arglist
from .config import Config
from .defs import CONFIG_NAME_DEFAULT, MIN_PYTHON_VERSION, MIN_PYTHON_VERSION_STR, UTF8
from .filters import FileNameFilter, FileSizeFilter
from .launcher import launch
from .logger import Log
from .version import APP_NAME, APP_VERSION

__all__ = ('main_async', 'main_sync')


class ErrorCodes:
    SUCCESS = 0
    INTERRUPTED = -1
    API_ERROR = -2
    UNKNOWN_ERROR = -255


def at_startup(args: Sequence[str]) -> None:
    """Inits logger. Reports python version and run options"""
    argv_set = set(args or ())
    parse_logging_args(args)
    Log.init()
    if argv_set.intersection({'--version', '--help'}):
        return
    Log.debug(f'Python {sys.version}\n{APP_NAME} ver {APP_VERSION}\nCommand-line args: {" ".join(sys.argv)}\n')


def autopick_config() -> None:
    base_config_path = Config.default_config_path()
    try:
        Log.debug(f'Looking for {CONFIG_NAME_DEFAULT}...')
        with open(base_config_path, 'rt', encoding=UTF8) as in_file:
            Log.debug(f'Using base configuration file {base_config_path.as_posix()}')
            Config.from_json(json.load(in_file))
    except OSError:
        Log.warn(f'Warning: config file \'{CONFIG_NAME_DEFAULT}\' is not found in \'{base_config_path.parent.as_posix()}\'!'
                 f' Default setting will be used.'
                 f'\nYou can make base config file for autoconfiguration using \'{MODULE} config create\' command')


def make_kemono_options() -> KemonoOptions:
    options = KemonoOptions(
        dest_base=Config.dest_base,
        retries=Config.retries,
        max_jobs=Config.max_jobs,
        api_address=Config.api_address,
        service=Config.service,
        timeout=Config.timeout,
        nodelay=Config.nodelay,
        proxy=Config.proxy,
        extra_headers=Config.extra_headers,
        extra_cookies=Config.extra_cookies,
        filters=(
            *((FileSizeFilter(Config.filter_filesize),) if Config.filter_filesize else ()),
            *((FileNameFilter(Config.filter_filename),) if Config.filter_filename else ()),
        ),
        download_mode=DownloadMode(Config.download_mode),
        logger=Log,
    )
    return options


async def main(args: Sequence[str]) -> int:
    try:
        autopick_config()
        prepare_arglist(args)
    except HelpPrintExitException:
        return 0

    try:
        kemono = Kemono(make_kemono_options())
        async with AsyncExitStack() as ctx:
            [await ctx.enter_async_context(_) for _ in (kemono,)]
            await launch(kemono)
        return ErrorCodes.SUCCESS
    except Exception as e:
        import traceback
        exc = traceback.format_exc()
        if isinstance(e, KemonoAPIError):
            Log.fatal(exc)
            return ErrorCodes.API_ERROR
        else:
            Log.fatal(f'Unhandled exception {e.__class__.__name__}!\n{exc}')
            return ErrorCodes.UNKNOWN_ERROR


async def run_main(args: Sequence[str]) -> int:
    res = await main(args)
    await sleep(0.5)
    return res


async def main_async(args: Sequence[str]) -> int:
    assert sys.version_info >= MIN_PYTHON_VERSION, f'Minimum python version required is {MIN_PYTHON_VERSION_STR}!'
    try:
        return await run_main(args)
    except (KeyboardInterrupt, SystemExit):
        Log.warn('Warning: catched KeyboardInterrupt/SystemExit...')
        return ErrorCodes.INTERRUPTED


def main_sync(args: Sequence[str]) -> int:
    at_startup(args)
    try:
        loop = get_running_loop()
    except RuntimeError:  # no current event loop
        loop = None
    run_func = loop.run_until_complete if loop else run
    return run_func(main_async(args))


if __name__ == '__main__':
    exit(main_sync(sys.argv[1:]))

#
#
#########################################

# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import pathlib
from typing import NamedTuple

from aiohttp import ClientTimeout

from .defs import DownloadMode
from .filters import Filter
from .logging import Logger
from .types import APIAddress, APIService


class KemonoOptions(NamedTuple):
    # for local
    dest_base: pathlib.Path
    retries: int
    max_jobs: int
    api_address: APIAddress
    service: APIService
    timeout: ClientTimeout
    nodelay: bool
    proxy: str
    extra_headers: list[tuple[str, str]]
    extra_cookies: list[tuple[str, str]]
    filters: tuple[Filter, ...]
    download_mode: DownloadMode
    # for global
    logger: Logger

#
#
#########################################

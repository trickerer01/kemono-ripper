# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from enum import Enum

CONNECT_REQUEST_DELAY = 0.3
CONNECT_RETRY_DELAY = (4.0, 8.0)

CHUNK_BLOCK_LEN = 16
EMPTY_IV = b'\0' * CHUNK_BLOCK_LEN
UINT32_MAX = 0xFFFFFFFF
DOWNLOAD_CHUNK_SIZE_INIT = 0x20000
DOWNLOAD_CHUNK_SIZE_MAX = 0x100000

POSTS_PER_PAGE = 50
MAX_JOBS = 8

UTF8 = 'utf-8'
LATIN1 = 'latin-1'


class DownloadMode(str, Enum):
    FULL = 'full'
    TOUCH = 'touch'
    SKIP = 'skip'


DOWNLOAD_MODES: tuple[str, ...] = tuple(_.value for _ in DownloadMode.__members__.values())
'''('full','touch','skip')'''
DOWNLOAD_MODE_DEFAULT = DownloadMode.FULL.value
"""'full'"""


class Mem:
    KB = 1024
    MB = KB * 1024
    GB = MB * 1024

#
#
#########################################

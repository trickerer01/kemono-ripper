# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from enum import Enum, IntEnum
from typing import NamedTuple

CONNECT_REQUEST_DELAY = 0.3
CONNECT_RETRY_DELAY = (4.0, 8.0)

CHUNK_BLOCK_LEN = 16
EMPTY_IV = b'\0' * CHUNK_BLOCK_LEN
UINT32_MAX = 0xFFFFFFFF
DOWNLOAD_CHUNK_SIZE_INIT = 0x20000
DOWNLOAD_CHUNK_SIZE_MAX = 0x100000

POSTS_PER_PAGE = 50

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


class DownloadResult(IntEnum):
    SUCCESS = 0
    FAIL_NOT_FOUND = 1
    FAIL_RETRIES = 2
    FAIL_ALREADY_EXISTS = 3
    FAIL_SKIPPED = 4
    FAIL_DELETED = 5
    FAIL_FILTERED_OUTER = 6
    FAIL_EMPTY_HTML = 7

    RESULT_MASK_ALL = ((1 << SUCCESS) | (1 << FAIL_NOT_FOUND) | (1 << FAIL_RETRIES) | (1 << FAIL_ALREADY_EXISTS) |
                       (1 << FAIL_SKIPPED) | (1 << FAIL_DELETED) | (1 << FAIL_FILTERED_OUTER) | (1 << FAIL_EMPTY_HTML))
    RESULT_MASK_CRITICAL = (RESULT_MASK_ALL & ~((1 << SUCCESS) | (1 << FAIL_SKIPPED) | (1 << FAIL_ALREADY_EXISTS)))

    def __str__(self) -> str:
        return f'{self.name} (0x{self.value:02X})'


class Mem:
    KB = 1024
    MB = KB * 1024
    GB = MB * 1024


class NumRange(NamedTuple):
    min: float
    max: float

    def __bool__(self) -> bool:
        return any(bool(getattr(self, _)) for _ in self._fields)

#
#
#########################################

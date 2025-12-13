# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import datetime
from enum import Enum, IntEnum
from typing import NamedTuple

MIN_PYTHON_VERSION = (3, 10)
MIN_PYTHON_VERSION_STR = f'{MIN_PYTHON_VERSION[0]:d}.{MIN_PYTHON_VERSION[1]:d}'

CREATORS_NAME_DEFAULT = 'creators.json'
POST_TAGS_NAME_DEFAULT = 'post_tags.json'
CONFIG_NAME_DEFAULT = 'setting.json'
POST_TAGS_PER_POST_NAME_DEFAULT = 'tags.txt'

SITE_MEGA = 'mega.nz'

CONNECT_RETRIES_BASE = 50
CONNECT_TIMEOUT_BASE = 10
CONNECT_TIMEOUT_SOCKET_READ = 30
MAX_JOBS_DEFAULT = 2
MAX_JOBS_MAX = 8

SCAN_CANCEL_KEYSTROKE = 'q'
SCAN_CANCEL_KEYCOUNT = 2
SLASH = '/'
UTF8 = 'utf-8'
JSON_INDENT_DEFAULT = 4
FMT_DATE = '%Y-%m-%d'


class SupportedExternalWebsite(str, Enum):
    MegaNz = SITE_MEGA


class LoggingFlags(IntEnum):
    NONE = 0x000
    TRACE = 0x001
    DEBUG = 0x002
    INFO = 0x004
    WARN = 0x008
    ERROR = 0x010
    FATAL = 0x800
    # unused
    ALL = FATAL | ERROR | WARN | INFO | DEBUG | TRACE
    '''0x81F'''

    def __str__(self) -> str:
        return f'{self.name} (0x{self.value:03X})'


LOGGING_FLAGS = {
    'error': f'0x{LoggingFlags.ERROR.value:03X}',
    'warn': f'0x{LoggingFlags.WARN.value:03X}',
    'info': f'0x{LoggingFlags.INFO.value:03X}',
    'debug': f'0x{LoggingFlags.DEBUG.value:03X}',
    'trace': f'0x{LoggingFlags.TRACE.value:03X}',
}
'''{\n\n'error': '0x010',\n\n'warn': '0x008',\n\n'info': '0x004',\n\n'debug': '0x002',\n\n'trace': '0x001'\n\n}'''
LOGGING_FLAGS_DEFAULT = LoggingFlags.INFO
'''0x004'''

ACTION_STORE_TRUE = 'store_true'
ACTION_APPEND = 'append'

HELP_ARG_VERSION = 'Show program\'s version number and exit'
HELP_ARG_PATH = 'Download destination. Default is current folder'
HELP_ARG_PROXY = 'Proxy to use, supports basic authentication'
HELP_ARG_DMMODE = '[Debug] Download (file creation) mode'
HELP_ARG_LOGGING = (
    f'Logging level: {{{str(list(LOGGING_FLAGS.keys())).replace(" ", "")[1:-1]}}}.'
    f' All messages equal or above this level will be logged. Default is \'info\''
)
HELP_ARG_NOCOLORS = 'Disable logging level dependent colors in log'
HELP_ARG_HEADER = 'Append additional header. Can be used multiple times'
HELP_ARG_COOKIE = 'Append additional cookie. Can be used multiple times'
HELP_ARG_TIMEOUT = f'Connection timeout (in seconds). Default is \'{CONNECT_TIMEOUT_BASE:d}\''
HELP_ARG_MAXJOBS = f'Maximum simultaneous connections, 1..{MAX_JOBS_MAX:d}'
HELP_ARG_RETRIES = f'Connection retries count. Default is \'{CONNECT_RETRIES_BASE:d}\''
HELP_ARG_API_ADDRESS = 'Target API address'
HELP_ARG_SERVICE = 'Target service'
HELP_ARG_CREATOR_NAME_PATTERN = 'Any name part. Case insensitive'
HELP_ARG_SKIP_CACHE = 'Always query API even if local creators dump exists'
HELP_ARG_INDENT = f'Saved JSON file indentation. Default is \'{JSON_INDENT_DEFAULT:d}\''
HELP_ARG_PRUNE = 'Prune all extra info from a saved JSON'
HELP_ARG_POST_ID = 'Post id as seen in web page address (integer)'
HELP_ARG_CREATOR_ID = 'Creator id as seen in web page address (integer)'
HELP_ARG_SAME_CREATOR = 'If all post have same creator this flag will speedup scanning process x2, (otherwise you\'ll get wrong results!)'
HELP_ARG_POST_URL = 'Full url to post page'
HELP_ARG_POST_FILE = 'Full path to target text file'
HELP_ARG_POST_FILE_LINES = 'Range of lines to read from the target file. Example: \'1-15\''
HELP_ARG_POST_TAG = 'Post tags. List of popular tags can be fetched using \'post tags dump\' command'
HELP_ARG_SEARCH_STRING = 'Search query string'
HELP_ARG_FILTER_POST_ID_RANGE = 'Post id range. Example: \'120000000-150000000\'. Not all post ids are numeric!'
HELP_ARG_FILTER_POST_DATE_RANGE = 'Post date range in format YYYY-MM-DD. Example 1: \'1970-01-01..2040-01-01\'. Example 2: \'2025-12-01..\''
HELP_ARG_FILTER_FILEEXT = 'Only download files with given extensions. Can be used multiple times. Example: \'--ext .mp4 --ext .png\''
HELP_ARG_FILTER_FILENAME = 'Only download files mathing given name pattern'


class NumRange(NamedTuple):
    min: float
    max: float

    def __bool__(self) -> bool:
        return any(bool(getattr(self, _)) for _ in self._fields)


class DateRange(NamedTuple):
    mindate: datetime.date
    maxdate: datetime.date

    def __bool__(self) -> bool:
        return any(bool(getattr(self, _)) for _ in self._fields)

#
#
#########################################

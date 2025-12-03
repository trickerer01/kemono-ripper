# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from typing import Final

from .api import ListedPostFile, Mem, NumRange
from .util import build_regex_from_pattern


class FileSizeFilter:
    """
    Filters files by file size in Megabytes (min .. max)
    """
    resolution: Final = Mem.MB

    def __init__(self, irange: NumRange) -> None:
        self._range = irange

    def filters_out(self, file: ListedPostFile) -> bool:
        file_size = len(file['path'])
        file_size /= FileSizeFilter.resolution
        return not self._range.min <= file_size <= self._range.max

    def __str__(self) -> str:
        return f'{self.__class__.__name__}<{self._range!s}>'


class FileNameFilter:
    """
    Filters files by file name pattern (regex)
    """
    def __init__(self, pattern: str) -> None:
        self._regex = build_regex_from_pattern(pattern)

    def filters_out(self, file: ListedPostFile) -> bool:
        file_name = file['name']
        return self._regex.fullmatch(file_name) is None

    def __str__(self) -> str:
        return f'{self.__class__.__name__}<{self._regex.pattern!s}>'

#
#
#########################################

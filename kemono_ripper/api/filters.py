# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from collections.abc import Iterable
from typing import Protocol

from .types import ListedPostFile

__all__ = ('Filter', 'any_filter_matching')


class Filter(Protocol):
    def filters_out(self, file: ListedPostFile) -> bool: ...
    def __str__(self) -> str: ...


def any_filter_matching(file: ListedPostFile, filters: Iterable[Filter]) -> Filter | None:
    for ffilter in filters:
        if ffilter.filters_out(file):
            return ffilter
    return None

#
#
#########################################

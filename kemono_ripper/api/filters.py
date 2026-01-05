# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from collections.abc import Iterable
from typing import Protocol

from .types import PostInfo, PostLinkInfo

__all__ = ('Filter', 'any_filter_matching')


class Filter(Protocol):
    def filters_out(self, post: PostInfo, plink: PostLinkInfo) -> bool: ...

    def __str__(self) -> str: ...


def any_filter_matching(post: PostInfo, plink: PostLinkInfo, filters: Iterable[Filter]) -> Filter | None:
    for ffilter in filters:
        if ffilter.filters_out(post, plink):
            return ffilter
    return None

#
#
#########################################

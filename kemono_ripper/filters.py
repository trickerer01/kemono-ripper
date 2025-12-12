# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import datetime
from collections.abc import Iterable
from typing import Final, Protocol, TypeAlias

from .api import ListedPost, Mem, PostDownloadInfo, PostLinkDownloadInfo, ScannedPost, SearchedPost
from .defs import DateRange, NumRange
from .util import build_regex_from_pattern


# API
class FileSizeFilter:
    """
    Filters files by file size in Megabytes (min .. max)
    """
    resolution: Final = Mem.MB

    def __init__(self, irange: NumRange) -> None:
        self._range = irange

    def filters_out(self, _post: PostDownloadInfo, plink: PostLinkDownloadInfo) -> bool:
        file_size = len(plink.path.as_posix())
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

    def filters_out(self, _post: PostDownloadInfo, plink: PostLinkDownloadInfo) -> bool:
        file_name = plink.path.name
        return self._regex.fullmatch(file_name) is None

    def __str__(self) -> str:
        return f'{self.__class__.__name__}<{self._regex.pattern!s}>'


# Downloader
LSPost: TypeAlias = ScannedPost | SearchedPost | ListedPost


class LSPostFilter(Protocol):
    def filters_out(self, post: LSPost) -> bool: ...

    def __str__(self) -> str: ...


def any_filter_matching_ls_post(post: LSPost, filters: Iterable[LSPostFilter | None]) -> LSPostFilter | None:
    for ffilter in filters:
        if ffilter and ffilter.filters_out(post):
            return ffilter
    return None


class PostIdFilter:
    """
    Filters posts by post id
    """

    def __init__(self, prange: NumRange) -> None:
        self._range = prange

    def filters_out(self, post: LSPost) -> bool:
        post_id = post['post']['id'] if 'post' in post else post['id']
        return post_id.isnumeric() and not self._range.min <= int(post_id) <= self._range.max

    def __str__(self) -> str:
        return f'{self.__class__.__name__}<{self._range!s}>'


class PostDateFilter:
    """
    Filters posts by post publish date
    """

    def __init__(self, drange: DateRange) -> None:
        self._range = drange

    def filters_out(self, post: LSPost) -> bool:
        published: str = post['post']['published'] if 'post' in post else post['published']
        published_date = datetime.datetime.fromisoformat(published).date()
        return not self._range.mindate <= published_date <= self._range.maxdate

    def __str__(self) -> str:
        return f'{self.__class__.__name__}<{self._range!s}>'


class PostLinkFilter(Protocol):
    def filters_out(self, plink: PostLinkDownloadInfo) -> bool: ...

    def __str__(self) -> str: ...


def any_filter_matching_post_link(plink: PostLinkDownloadInfo, filters: Iterable[PostLinkFilter | None]) -> PostLinkFilter | None:
    for ffilter in filters:
        if ffilter and ffilter.filters_out(plink):
            return ffilter
    return None


class PostLinkExtFilter:
    """
    Filters posts links by post link file extension
    """

    def __init__(self, extensions: Iterable[str]) -> None:
        self._extensions = list(extensions)

    def filters_out(self, plink: PostLinkDownloadInfo) -> bool:
        return plink.path.suffix and not any(plink.path.name.endswith(_) for _ in self._extensions)

    def __str__(self) -> str:
        return f'{self.__class__.__name__}<{self._extensions!s}>'

#
#
#########################################

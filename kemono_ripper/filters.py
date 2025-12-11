# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from collections.abc import Iterable
from typing import Final, Protocol

from .api import ListedPost, Mem, NumRange, PostDownloadInfo, PostLinkDownloadInfo, ScannedPost, SearchedPost
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
class LSPostFilter(Protocol):
    def filters_out(self, post: ScannedPost | SearchedPost | ListedPost) -> bool: ...
    def __str__(self) -> str: ...


def any_filter_matching_ls_post(post: ScannedPost | SearchedPost | ListedPost, filters: Iterable[LSPostFilter]) -> LSPostFilter | None:
    for ffilter in filters:
        if ffilter.filters_out(post):
            return ffilter
    return None


class PostIdFilter:
    """
    Filters posts by post id
    """
    def __init__(self, prange: NumRange) -> None:
        self._range = prange

    def filters_out(self, post: ScannedPost | SearchedPost | ListedPost) -> bool:
        post_id = post['post']['id'] if 'post' in post else post['id']
        return post_id.isnumeric() and not self._range.min <= int(post_id) <= self._range.max

    def __str__(self) -> str:
        return f'{self.__class__.__name__}<{self._range!s}>'


class PostLinkFilter(Protocol):
    def filters_out(self, plink: PostLinkDownloadInfo) -> bool: ...
    def __str__(self) -> str: ...


def any_filter_matching_post_link(plink: PostLinkDownloadInfo, filters: Iterable[PostLinkFilter]) -> PostLinkFilter | None:
    for ffilter in filters:
        if ffilter.filters_out(plink):
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

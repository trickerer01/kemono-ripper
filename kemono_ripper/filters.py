# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import datetime
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Final, Literal, Protocol, TypeAlias

from .api import ListedPost, Mem, PostDownloadInfo, PostLinkDownloadInfo, ScannedPost, SearchedPost
from .defs import FMT_DATE, DateRange, NumRange
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
    _last_filtered: str

    def filters_out(self, post: LSPost) -> bool: ...
    def close(self) -> None: ...
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
        self._last_filtered = ''

    def close(self) -> None:
        self._last_filtered = ''

    def filters_out(self, post: LSPost) -> bool:
        post_id = post['post']['id'] if 'post' in post else post['id']
        if post_id.isnumeric() and not self._range.min <= int(post_id) <= self._range.max:
            self._last_filtered = post_id
            return True
        return False

    def __str__(self) -> str:
        return f'{self.__class__.__name__}<{int(self._range.min):d} <= \'{self._last_filtered}\' <= {int(self._range.max):d}>'


class PostDateFilterBase(ABC):
    def __init__(self, drange: DateRange) -> None:
        self._range = drange
        self._last_filtered = ''

    def close(self) -> None:
        self._last_filtered = ''

    @abstractmethod
    def filters_out(self, post: LSPost) -> bool: ...

    def filters_out_by_date_type(self, post: LSPost, date_type_str: Literal['published', 'added', 'edited']) -> bool:
        dpost = post.get('post', post)
        assert date_type_str in dpost, f'[{self!s}] Post {dpost!s} doesn\'t have required field \'{date_type_str}\'!'
        date_type_date = datetime.datetime.fromisoformat(dpost[date_type_str]).date()
        if not self._range.mindate <= date_type_date <= self._range.maxdate:
            self._last_filtered = date_type_date.strftime(FMT_DATE)
            return True
        return False

    def __str__(self) -> str:
        return (f'{self.__class__.__name__}'
                f'<{self._range.mindate.strftime(FMT_DATE)} <= \'{self._last_filtered}\' <= {self._range.maxdate.strftime(FMT_DATE)}>')


class PostDatePublishedFilter(PostDateFilterBase):
    """
    Filters posts by post published date
    """
    def filters_out(self, post: LSPost) -> bool:
        return self.filters_out_by_date_type(post, 'published')


class PostDateImportedFilter(PostDateFilterBase):
    """
    Filters posts by post imported date
    """
    def filters_out(self, post: LSPost) -> bool:
        return self.filters_out_by_date_type(post, 'added')


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
        self._last_filtered = ''

    def close(self) -> None:
        self._last_filtered = ''

    def filters_out(self, plink: PostLinkDownloadInfo) -> bool:
        if plink.path.suffix and plink.path.suffix not in self._extensions:
            self._last_filtered = plink.path.name
            return True
        return False

    def __str__(self) -> str:
        return f'{self.__class__.__name__}<\'{self._last_filtered}\' <- {self._extensions!s}>'

#
#
#########################################

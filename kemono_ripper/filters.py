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
from .config import Config
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
        return f'{self.__class__.__name__}<{self._regex.pattern[1:-1]}>'


# Downloader
LSPost: TypeAlias = ScannedPost | SearchedPost | ListedPost


class LSPostFilter(Protocol):
    _last_filtered: str

    def filters_out(self, post: LSPost) -> bool: ...
    def close(self) -> None: ...
    def __str__(self) -> str: ...


class UserIdFilter:
    def __init__(self, patterns: list[str]) -> None:
        self._patterns = [build_regex_from_pattern(_) for _ in patterns]
        self._last_filtered = ''

    def close(self) -> None:
        self._last_filtered = ''

    @abstractmethod
    def filters_out(self, post: LSPost) -> bool:
        user: str = post.get('post', post)['user']
        for pattern in self._patterns:
            if pattern.fullmatch(user.lower()):
                self._last_filtered = user
                return True
        return False

    def __str__(self) -> str:
        return f'{self.__class__.__name__}<\'{self._last_filtered}\' <- {[f"-u:{_.pattern[1:-1]}" for _ in self._patterns]!s}>'


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
        post_id: str = post.get('post', post)['id']
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
        dpost: SearchedPost | ListedPost = post.get('post', post)
        assert date_type_str in dpost, f'[{self!s}] Post {dpost!s} doesn\'t have required field \'{date_type_str}\'!'
        try:
            date_type_date = datetime.datetime.fromisoformat(dpost[date_type_str]).date()
        except TypeError:
            return False
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


class PostTagsFilter:
    def __init__(self, patterns: list[str]) -> None:
        self._patterns = [build_regex_from_pattern(_) for _ in patterns]
        self._last_filtered = ''

    def close(self) -> None:
        self._last_filtered = ''

    @abstractmethod
    def filters_out(self, post: LSPost) -> bool:
        post_tags: list[str] = post.get('post', post).get('tags', [])
        if post_tags:
            for pattern in self._patterns:
                for tag in post_tags:
                    if pattern.fullmatch(tag.lower()):
                        self._last_filtered = tag
                        return True
        return False

    def __str__(self) -> str:
        return f'{self.__class__.__name__}<\'{self._last_filtered}\' <- {[f"-t:{_.pattern[1:-1]}" for _ in self._patterns]!s}>'


class PostLinkFilter(Protocol):
    def filters_out(self, plink: PostLinkDownloadInfo) -> bool: ...
    def __str__(self) -> str: ...


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


def any_filter_matching_ls_post(post: LSPost, filters: Iterable[LSPostFilter | None]) -> LSPostFilter | None:
    for ffilter in filters:
        if ffilter and ffilter.filters_out(post):
            return ffilter
    return None


def make_lspost_filters() -> list[LSPostFilter | None]:
    filters = [
        UserIdFilter(Config.filter_user_id) if Config.filter_user_id else None,
        PostIdFilter(Config.filter_post_ids) if Config.filter_post_ids else None,
        PostTagsFilter(Config.filter_post_tags) if Config.filter_post_tags else None,
        PostDateImportedFilter(Config.filter_post_imported) if Config.filter_post_imported else None,
        PostDatePublishedFilter(Config.filter_post_published) if Config.filter_post_published else None,
    ]
    return filters


def any_filter_matching_post_link(plink: PostLinkDownloadInfo, filters: Iterable[PostLinkFilter | None]) -> PostLinkFilter | None:
    for ffilter in filters:
        if ffilter and ffilter.filters_out(plink):
            return ffilter
    return None


def make_post_link_filters() -> list[PostLinkFilter | None]:
    filters = [
        PostLinkExtFilter(Config.filter_extensions) if Config.filter_extensions else None,
    ]
    return filters

#
#
#########################################

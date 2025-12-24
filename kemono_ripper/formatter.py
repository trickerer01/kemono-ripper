# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import pathlib
from typing import Protocol

from .api import ScannedPostPost
from .defs import PathFormatType
from .util import sanitize_path

__all__ = (
    'PathFormatter',
    'PathFormatterCreatorDashPostId',
    'PathFormatterCreatorDashPostIdDashTitle',
    'PathFormatterCreatorDashTitlePostId',
    'PathFormatterCreatorSlashPostId',
    'PathFormatterDefault',
    'get_path_formatter',
)


def ensure_max_length(base_string: str, max_len: int) -> str:
    result = base_string
    while len(result) > max_len:
        result = result[:len(result) // 2]
    return result


def normalize_format_string(base_string: str, max_len: int) -> str:
    result = sanitize_path(ensure_max_length(sanitize_path(base_string.strip()), max_len).strip()).strip() or 'Untitled'
    return result


class PathFormatter(Protocol):
    @staticmethod
    def format(post: ScannedPostPost) -> pathlib.Path: ...


class PathFormatterCreatorSlashPostId:
    @staticmethod
    def format(post: ScannedPostPost) -> pathlib.Path:
        return pathlib.Path(post['user']) / post['id']


class PathFormatterCreatorDashPostId:
    @staticmethod
    def format(post: ScannedPostPost) -> pathlib.Path:
        return pathlib.Path(f'{post["user"]} - {post["id"]}')


class PathFormatterCreatorDashTitlePostId:
    @staticmethod
    def format(post: ScannedPostPost) -> pathlib.Path:
        return pathlib.Path(f'{post["user"]} - {normalize_format_string(post["title"], 50)} ({post["id"]})')


class PathFormatterCreatorDashPostIdDashTitle:
    @staticmethod
    def format(post: ScannedPostPost) -> pathlib.Path:
        return pathlib.Path(f'{post["user"]} - {post["id"]} - {normalize_format_string(post["title"], 50)}')


PATH_FORMATTERS: dict[PathFormatType, PathFormatter] = {
    '{creator_id}/{post_id}': PathFormatterCreatorSlashPostId(),
    '{creator_id} - {post_id}': PathFormatterCreatorDashPostId(),
    '{creator_id} - {post_title} ({post_id})': PathFormatterCreatorDashTitlePostId(),
    '{creator_id} - {post_id} - {post_title}': PathFormatterCreatorDashPostIdDashTitle(),
}

PathFormatterDefault = PATH_FORMATTERS['{creator_id}/{post_id}']


def get_path_formatter(format_type: PathFormatType) -> PathFormatter:
    return PATH_FORMATTERS.get(format_type, PathFormatterDefault)

#
#
#########################################

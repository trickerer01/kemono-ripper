# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import datetime
import pathlib
from collections.abc import Callable

from .api import ScannedPostPost
from .defs import FMT_DATE, PathTokens
from .util import sanitize_path

__all__ = ('format_path',)


TOKEN_EXTRACTORS: dict[str, Callable[[ScannedPostPost], str]] = {
    PathTokens.PostId: lambda p: p['id'],
    PathTokens.Creator: lambda p: p['user'],
    PathTokens.Title: lambda p: _normalize_format_token(p['title'], 50),
    PathTokens.Imported: lambda p: _convert_date(p['added']),
    PathTokens.Published: lambda p: _convert_date(p['published']),
}
assert len(TOKEN_EXTRACTORS) == len(PathTokens.__members__.values()), 'God bless defensive programming'


def _ensure_max_length(base_string: str, max_len: int) -> str:
    result = base_string
    while len(result) > max_len:
        result = result[:len(result) // 2]
    return result


def _convert_date(date_str: str) -> str:
    try:
        date_type_date = datetime.datetime.fromisoformat(date_str).date()
        return date_type_date.strftime(FMT_DATE)
    except TypeError:
        return 'unk_date'


def _normalize_format_token(base_string: str, max_len: int) -> str:
    result = sanitize_path(_ensure_max_length(sanitize_path(base_string.strip()), max_len).strip()).strip() or 'Untitled'
    return result


def format_path(post: ScannedPostPost, format_string: str) -> pathlib.Path:
    result_str = format_string.format_map({t[1:-1]: TOKEN_EXTRACTORS[t](post) for t in TOKEN_EXTRACTORS if t in format_string})
    return pathlib.Path(result_str)

#
#
#########################################

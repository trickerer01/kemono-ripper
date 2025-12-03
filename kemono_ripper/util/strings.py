# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import re
import urllib.parse

HTTP_PREFIX = 'http://'
HTTPS_PREFIX = 'https://'


def ensure_scheme_https(url: str) -> str:
    if urllib.parse.urlparse(url).scheme == 'http':
        return url.replace(HTTP_PREFIX, HTTPS_PREFIX)


def compose_link_v2(folder_id: str, file_id: str, key: str, site: str = '') -> str:
    if key and (folder_id or file_id):
        if folder_id:
            link = f'{site}/folder/{folder_id}#{key}'
            if file_id:
                link = f'{link}/file/{file_id}'
        else:  # if file_id
            link = f'{site}/file/{file_id}#{key}'
        return link
    # invalid link always
    return ''


def build_regex_from_pattern(expression: str) -> re.Pattern:
    pat_freplacements = {
        '(?:': '\u2044', '?': '\u203D', '*': '\u20F0', '(': '\u2039', ')': '\u203A',
        '.': '\u1FBE', ',': '\u201A', '+': '\u2020', '-': '\u2012',
    }
    pat_breplacements: dict[str, str] = {pat_freplacements[k]: k for k in pat_freplacements}
    pat_breplacements[pat_freplacements['(']] = '(?:'
    chars_need_escaping = list(pat_freplacements.keys())
    del chars_need_escaping[1:3]
    escape_char = '`'
    escape = escape_char in expression
    if escape:
        for fk, wtag_freplacement in pat_freplacements.items():
            expression = expression.replace(f'{escape_char}{fk}', wtag_freplacement)
    for c in chars_need_escaping:
        expression = expression.replace(c, f'\\{c}')
    expression = expression.replace('*', '.*').replace('?', '.').replace(escape_char, '')
    if escape:
        for bk, pat_breplacement in pat_breplacements.items():
            expression = expression.replace(f'{bk}', pat_breplacement)
    return re.compile(rf'^{expression}$')

#
#
#########################################

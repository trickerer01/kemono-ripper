# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import re
from typing import Final

SLASH = '/'
re_ext: Final = re.compile(r'(\.[^&]{3,5})&')


def normalize_path(basepath: str, append_slash=True) -> str:
    """Converts path string to universal slash-concatenated string, enclosing slash is optional"""
    normalized_path = basepath.replace('\\', SLASH)
    if append_slash and normalized_path and not normalized_path.endswith(SLASH):
        normalized_path += SLASH
    return normalized_path


def sanitize_filename(filename_base: str) -> str:
    def char_replace(char: str) -> str:
        if char in '\n\r\t"*:<>?|/\\':
            return {'/': '\u29f8', '\\': '\u29f9', '\n': '', '\r': '', '\t': ''}.get(char, chr(ord(char) + 0xfee0))
        elif ord(char) < 32 or ord(char) == 127:
            char = ''
        return char

    filename = ''.join(map(char_replace, filename_base)).replace('\0', '_')
    while '__' in filename:
        filename = filename.replace('__', '_')
    return filename.strip('_')


def normalize_filename(filename: str, base_path: str) -> str:
    """Returns full path to a file, normalizing base path and removing disallowed symbols from file name"""
    return f'{normalize_path(base_path)}{sanitize_filename(filename)}'


def extract_ext(href: str) -> str:
    ext_match = re_ext.search(href)
    return ext_match.group(1) if ext_match else ''


#
#
#########################################

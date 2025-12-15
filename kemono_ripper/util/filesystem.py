# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import re

SLASH = '/'
re_ext = re.compile(r'(\.[^&]{3,5})&')


def sanitize_path(path_base: str) -> str:
    def char_replace(char: str) -> str:
        if char in '\n\r\t"*:<>?|/\\':
            return {'/': '\u29f8', '\\': '\u29f9', '\n': '', '\r': '', '\t': ''}.get(char, chr(ord(char) + 0xfee0))
        elif ord(char) < 32 or ord(char) == 127:
            char = ''
        return char

    sane_path = ''.join(map(char_replace, path_base)).replace('\0', '_')
    while '__' in sane_path:
        sane_path = sane_path.replace('__', '_')
    return sane_path.strip('_')


def extract_ext(href: str) -> str:
    ext_match = re_ext.search(href)
    return ext_match.group(1) if ext_match else ''

#
#
#########################################

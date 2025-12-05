# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import os
from argparse import ONE_OR_MORE, OPTIONAL, ArgumentParser, Namespace
from collections.abc import Sequence

from .api import DOWNLOAD_MODE_DEFAULT, DOWNLOAD_MODES, APIAddress, APIService
from .config import Config
from .defs import (
    ACTION_APPEND,
    ACTION_STORE_TRUE,
    CONNECT_RETRIES_BASE,
    HELP_ARG_API_ADDRESS,
    HELP_ARG_COOKIE,
    HELP_ARG_CREATOR_ID,
    HELP_ARG_CREATOR_NAME_PATTERN,
    HELP_ARG_DMMODE,
    HELP_ARG_FILTERS,
    HELP_ARG_HEADER,
    HELP_ARG_INDENT,
    HELP_ARG_LOGGING,
    HELP_ARG_MAXJOBS,
    HELP_ARG_NOCOLORS,
    HELP_ARG_PATH,
    HELP_ARG_POST_FILE,
    HELP_ARG_POST_ID,
    HELP_ARG_POST_URL,
    HELP_ARG_PROXY,
    HELP_ARG_RETRIES,
    HELP_ARG_SERVICE,
    HELP_ARG_SKIP_CACHE,
    HELP_ARG_TIMEOUT,
    HELP_ARG_VERSION,
    JSON_INDENT_DEFAULT,
    LOGGING_FLAGS_DEFAULT,
    MAX_JOBS_DEFAULT,
)
from .logger import Log
from .validators import (
    log_level,
    positive_int,
    positive_nonzero_int,
    valid_file_path,
    valid_folder_path,
    valid_indent,
    valid_kwarg,
    valid_maxjobs,
    valid_pattern,
    valid_post_url,
    valid_proxy,
    valid_range,
    valid_timeout,
)
from .version import APP_NAME, APP_VERSION

__all__ = ('MODULE', 'HelpPrintExitException', 'parse_logging_args', 'prepare_arglist')

MODULE = APP_NAME.replace('-', '_')
INDENT = ' ' * 7

DM_DEFAULT = DOWNLOAD_MODE_DEFAULT
"""'full'"""
LOGGING_DEFAULT = LOGGING_FLAGS_DEFAULT
'''0x004'''
INDENT_DEFAULT = JSON_INDENT_DEFAULT
SERVICE_DEFAULT: APIService = next(iter(APIService.__args__))
API_ADDRESS_DEFAULT: APIAddress = next(iter(APIAddress.__args__))

PARSER_TITLE_NONE = ''
PARSER_TITLE_CREATOR = 'creator'
PARSER_TITLE_CREATOR_LIST = 'clist'
PARSER_TITLE_CREATOR_DUMP = 'cdump'
PARSER_TITLE_CREATOR_RIP = 'crip'
PARSER_TITLE_POST = 'post'
PARSER_TITLE_POST_LIST = 'plist'
PARSER_TITLE_POST_SCAN = 'pscan'
PARSER_TITLE_POST_SCAN_ID = 'pscan_id'
PARSER_TITLE_POST_SCAN_URL = 'pscan_url'
PARSER_TITLE_POST_SCAN_FILE = 'pscan_file'
PARSER_TITLE_POST_RIP = 'prip'
PARSER_TITLE_CONFIG = 'config'
PARSER_TITLE_CONFIG_CREATE = 'cfcreate'
PARSER_TITLE_CONFIG_MODIFY = 'cfmodify'

PARSER_TITLE_NAMES_REMAP: dict[str, str] = {
    PARSER_TITLE_CREATOR_LIST: 'list',
    PARSER_TITLE_CREATOR_DUMP: 'dump',
    PARSER_TITLE_CREATOR_RIP: 'rip',
    PARSER_TITLE_POST_LIST: 'list',
    PARSER_TITLE_POST_SCAN: 'scan',
    PARSER_TITLE_POST_SCAN_ID: 'id',
    PARSER_TITLE_POST_SCAN_URL: 'url',
    PARSER_TITLE_POST_SCAN_FILE: 'file',
    PARSER_TITLE_POST_RIP: 'rip',
    PARSER_TITLE_CONFIG_CREATE: 'create',
    PARSER_TITLE_CONFIG_MODIFY: 'modify',
}


class HelpPrintExitException(Exception):
    pass


def parse_logging_args(args: Sequence[str]) -> None:
    parser = ArgumentParser(add_help=False)
    add_logging_args(parser)
    parsed = parser.parse_known_args(args)
    Config.logging_flags = parsed[0].log_level
    Config.disable_log_colors = parsed[0].disable_log_colors


def execute_parser(parser: ArgumentParser, args: Sequence[str]) -> Namespace:
    if not args:
        parser.print_help()
        raise HelpPrintExitException

    try:
        parsed, _unks = parser.parse_known_args(args)
        return parsed
    except SystemExit:
        raise HelpPrintExitException
    except Exception:
        from traceback import format_exc
        Log.fatal(format_exc())
        raise HelpPrintExitException


def create_parsers() -> dict[str, ArgumentParser]:
    def create_parser(sub, name: str, description: str) -> ArgumentParser:
        if sub:
            parser: ArgumentParser = sub.add_parser(PARSER_TITLE_NAMES_REMAP.get(name, name), description=description, add_help=False)
        else:
            parser = ArgumentParser(add_help=False, prog=MODULE)
        assert name not in parsers
        parsers[name] = parser
        return parser

    def create_subparser(parser: ArgumentParser, title: str, dest: str):
        return parser.add_subparsers(required=True, title=title, dest=dest, prog=MODULE)

    parsers: dict[str, ArgumentParser] = {}

    parser_main = create_parser(None, PARSER_TITLE_NONE, '')
    subs_main = create_subparser(parser_main, 'subcommands', 'subcommand_1')
    # subs_main.add_parser("", )

    par_creators = create_parser(subs_main, PARSER_TITLE_CREATOR, '')
    subs_creators = create_subparser(par_creators, 'creator', 'subcommand_2')
    _ = create_parser(subs_creators, PARSER_TITLE_CREATOR_LIST, 'List creators')
    _ = create_parser(subs_creators, PARSER_TITLE_CREATOR_DUMP, 'Dump ALL creators list to a JSON file')

    _ = create_parser(subs_creators, PARSER_TITLE_CREATOR_RIP, 'Scan all creator post pages and download everything')

    par_posts = create_parser(subs_main, PARSER_TITLE_POST, '')
    subs_posts = create_subparser(par_posts, 'post', 'subcommand_2')
    _ = create_parser(subs_posts, PARSER_TITLE_POST_LIST, 'List creator posts')

    par_post_scan = create_parser(subs_posts, PARSER_TITLE_POST_SCAN, 'Scan post contents')
    subs_posts_scan = create_subparser(par_post_scan, 'inputs', 'subcommand_3')
    _ = create_parser(subs_posts_scan, PARSER_TITLE_POST_SCAN_ID, 'Scan posts by post id')
    _ = create_parser(subs_posts_scan, PARSER_TITLE_POST_SCAN_URL, 'Scan posts by URL')
    _ = create_parser(subs_posts_scan, PARSER_TITLE_POST_SCAN_FILE, 'Read scan targets from text file')

    _ = create_parser(subs_posts, PARSER_TITLE_POST_RIP, 'Scan post content and download everything')

    par_config = create_parser(subs_main, PARSER_TITLE_CONFIG, '')
    subs_config = create_subparser(par_config, 'config', 'subcommand_2')
    _ = create_parser(subs_config, PARSER_TITLE_CONFIG_CREATE, 'Create a default config file if doesn\'t exist')
    _ = create_parser(subs_config, PARSER_TITLE_CONFIG_MODIFY, 'Change settings in config file')

    return parsers


def add_help(par: ArgumentParser, is_root: bool):
    mi = par.add_argument_group(title='misc')
    mi.add_argument('--help', action='help', help='Print this message')
    if is_root:
        mi.add_argument('--version', action='version', help=HELP_ARG_VERSION, version=f'{APP_NAME} {APP_VERSION}')


def add_common_args(par: ArgumentParser) -> None:
    ke = par.add_argument_group(title='kemono options')
    ke.add_argument('--api-address', default=API_ADDRESS_DEFAULT, help=HELP_ARG_API_ADDRESS, choices=APIAddress.__args__)
    ke.add_argument('--service', default=SERVICE_DEFAULT, help=HELP_ARG_SERVICE, choices=APIService.__args__)
    co = par.add_argument_group(title='connection options')
    co.add_argument('-x', '--proxy', metavar='#type://[u:p@]a.d.d.r:port', default=None, help=HELP_ARG_PROXY, type=valid_proxy)
    co.add_argument('-t', '--timeout', metavar='#seconds', default=valid_timeout(''), help=HELP_ARG_TIMEOUT, type=valid_timeout)
    co.add_argument('-r', '--retries', metavar='#number', default=CONNECT_RETRIES_BASE, help=HELP_ARG_RETRIES, type=positive_int)
    co.add_argument('-h', '--header', metavar='#name=value', action=ACTION_APPEND, help=HELP_ARG_HEADER, type=valid_kwarg)
    co.add_argument('-c', '--cookie', metavar='#name=value', action=ACTION_APPEND, help=HELP_ARG_COOKIE, type=valid_kwarg)
    do = par.add_argument_group(title='download options')
    do.add_argument('-o', '--path', default=valid_folder_path(os.path.curdir), help=HELP_ARG_PATH, type=valid_folder_path)
    do.add_argument('-d', '--download-mode', default=DM_DEFAULT, help=HELP_ARG_DMMODE, choices=DOWNLOAD_MODES)
    do.add_argument('-j', '--max-jobs', metavar='#number', default=MAX_JOBS_DEFAULT, help=HELP_ARG_MAXJOBS, type=valid_maxjobs)
    dofi = par.add_argument_group(title='filtering options')
    dofi.add_argument('-fs', '--filter-filesize', metavar='#min-max', default=None, help='', type=valid_range)
    dofi.add_argument('-fn', '--filter-filename', metavar='#pattern', default=None, help=HELP_ARG_FILTERS, type=valid_pattern)


def add_logging_args(par: ArgumentParser) -> None:
    lo = par.add_argument_group(title='logging options')
    lo.add_argument('-v', '--log-level', default=LOGGING_DEFAULT, help=HELP_ARG_LOGGING, type=log_level)
    lo.add_argument('-g', '--disable-log-colors', action=ACTION_STORE_TRUE, help=HELP_ARG_NOCOLORS)


def parse_arglist(args: Sequence[str]) -> Namespace:
    parsers = create_parsers()

    # Root
    parser_root = parsers[PARSER_TITLE_NONE]
    parser_root.usage = (
        f'\n{INDENT}{MODULE} {PARSER_TITLE_CREATOR} ...'
        f'\n{INDENT}{MODULE} {PARSER_TITLE_POST} ...'
        f'\n{INDENT}{MODULE} {PARSER_TITLE_CONFIG} ...'
    )

    # Config
    pcf = parsers[PARSER_TITLE_CONFIG]
    pcf.usage = (
        f'\n{INDENT}{MODULE} {PARSER_TITLE_CONFIG} {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_CONFIG_CREATE]}'
        f'\n{INDENT}{MODULE} {PARSER_TITLE_CONFIG} {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_CONFIG_MODIFY]}'
        f' #[options...]'
    )
    #  create
    pcfc = parsers[PARSER_TITLE_CONFIG_CREATE]
    # pcfcg1 = pcfc.add_argument_group(title='options')
    # pcfcg1.add_argument('name', help=HELP_ARG_CONFIG_NAME, type=str)
    #  modify
    pcfm = parsers[PARSER_TITLE_CONFIG_MODIFY]
    # pcfmg1 = pcfm.add_argument_group(title='options')
    # pcfmg1.add_argument('name', help=HELP_ARG_CONFIG_NAME, type=str)

    # Creators
    pc = parsers[PARSER_TITLE_CREATOR]
    pc.usage = (
        f'\n{INDENT}{MODULE} {PARSER_TITLE_CREATOR} {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_CREATOR_LIST]} ...'
        f'\n{INDENT}{MODULE} {PARSER_TITLE_CREATOR} {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_CREATOR_DUMP]} ...'
        f'\n{INDENT}{MODULE} {PARSER_TITLE_CREATOR} {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_CREATOR_RIP]} ...'
    )
    #  list
    pcl = parsers[PARSER_TITLE_CREATOR_LIST]
    pcl.usage = (
        f'\n{INDENT}{MODULE} {PARSER_TITLE_CREATOR} {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_CREATOR_LIST]}'
        f' #[options...] #pattern'
    )
    pclg1 = pcl.add_argument_group(title='options')
    pclg1.add_argument('pattern', help=HELP_ARG_CREATOR_NAME_PATTERN, type=str)
    pclg1.add_argument('-n', '--skip-cache', action=ACTION_STORE_TRUE, help=HELP_ARG_SKIP_CACHE)
    #  dump
    pcd = parsers[PARSER_TITLE_CREATOR_DUMP]
    pcd.usage = (
        f'\n{INDENT}{MODULE} {PARSER_TITLE_CREATOR} {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_CREATOR_DUMP]}'
        f' #[options...]'
    )
    pcdg1 = pcd.add_argument_group(title='options')
    pcdg1.add_argument('-i', '--indent', metavar='1..4', default=INDENT_DEFAULT, help=HELP_ARG_INDENT, type=valid_indent)
    #  rip
    pcr = parsers[PARSER_TITLE_CREATOR_RIP]
    # pcr.usage = (
    #     f'\n{INDENT}{MODULE} {PARSER_TITLE_CREATOR} {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_CREATOR_RIP]}'  # TODO: complete this
    #     f' #[options...] #creator_id'
    # )
    # pcrg1 = pcr.add_argument_group(title='options')
    # pcrg1.add_argument('-i', '--indent', metavar='1..4', default=INDENT_DEFAULT, help=HELP_ARG_INDENT, type=valid_indent)

    # Posts
    pp = parsers[PARSER_TITLE_POST]
    pp.usage = (
        f'\n{INDENT}{MODULE} {PARSER_TITLE_POST} {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_POST_LIST]} ...'
        f'\n{INDENT}{MODULE} {PARSER_TITLE_POST} {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_POST_SCAN]} ...'
    )
    #  list
    ppl = parsers[PARSER_TITLE_POST_LIST]
    ppl.usage = (
        f'\n{INDENT}{MODULE} {PARSER_TITLE_POST} {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_POST_LIST]}'
        f' #[options...] #creator_id'
    )
    pplg1 = ppl.add_argument_group(title='options')
    pplg1.add_argument('creator_id', help=HELP_ARG_CREATOR_ID, type=positive_nonzero_int)
    #  scan
    pps = parsers[PARSER_TITLE_POST_SCAN]
    pps.usage = (
        f'\n{INDENT}{MODULE} {PARSER_TITLE_POST} {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_POST_SCAN]}'
        f' {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_POST_SCAN_ID]} ...'
        f'\n{INDENT}{MODULE} {PARSER_TITLE_POST} {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_POST_SCAN]}'
        f' {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_POST_SCAN_URL]} ...'
        f'\n{INDENT}{MODULE} {PARSER_TITLE_POST} {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_POST_SCAN]}'
        f' {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_POST_SCAN_FILE]} ...'
    )
    #   scan ids
    ppsi = parsers[PARSER_TITLE_POST_SCAN_ID]
    ppsi.usage = (
        f'\n{INDENT}{MODULE} {PARSER_TITLE_POST} {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_POST_SCAN]}'
        f' {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_POST_SCAN_ID]}'
        f' #[options...] [--creator-id #user_id] #post_id [post_id ...]'
    )
    ppsig1 = ppsi.add_argument_group(title='options')
    ppsig1.add_argument('post_id', metavar='post_id [post_id ...]', nargs=ONE_OR_MORE, help=HELP_ARG_POST_ID, type=positive_nonzero_int)
    ppsig1.add_argument('--creator-id', nargs=OPTIONAL, default=0, help=HELP_ARG_CREATOR_ID, type=positive_nonzero_int)
    #   scan URL
    ppsu = parsers[PARSER_TITLE_POST_SCAN_URL]
    ppsu.usage = (
        f'\n{INDENT}{MODULE} {PARSER_TITLE_POST} {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_POST_SCAN]}'
        f' {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_POST_SCAN_URL]}'
        f' #[options...] #URL [URL ...]'
    )
    ppsug1 = ppsu.add_argument_group(title='options')
    ppsug1.add_argument('links', metavar='URL [URL ...]', nargs=ONE_OR_MORE, help=HELP_ARG_POST_URL, type=valid_post_url)
    #   scan file
    ppsf = parsers[PARSER_TITLE_POST_SCAN_FILE]
    ppsf.usage = (
        f'\n{INDENT}{MODULE} {PARSER_TITLE_POST} {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_POST_SCAN]}'
        f' {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_POST_SCAN_FILE]}'
        f' #[options...] #file'
    )
    ppsfg1 = ppsf.add_argument_group(title='options')
    ppsfg1.add_argument('file', help=HELP_ARG_POST_FILE, type=valid_file_path)
    #  rip
    ppr = parsers[PARSER_TITLE_POST_RIP]
    # ppr.usage = (
    #     f'\n{INDENT}{MODULE} {PARSER_TITLE_POST} {PARSER_TITLE_NAMES_REMAP[PARSER_TITLE_POST_RIP]}'  # TODO: complete this
    #     f' #[options...] #post_id [post_id ...]'
    # )
    # pprg1 = ppr.add_argument_group(title='options')
    # pprg1.add_argument('links', metavar='URL [URL ...]', nargs=ONE_OR_MORE, help=HELP_ARG_POST_URL, type=valid_post_url)

    [add_common_args(_) for _ in (parser_root, pcl, pcd, pcr, ppl, ppsi, ppsu, ppsf, ppr, pcfc, pcfm)]
    [add_logging_args(_) for _ in parsers.values()]
    [add_help(_, _ == parser_root) for _ in parsers.values()]
    return execute_parser(parser_root, args)


def prepare_arglist(args: Sequence[str]) -> None:
    parsed = parse_arglist(args)
    for pp in vars(parsed):
        param = Config.NAMESPACE_VARS_REMAP.get(pp, pp)
        if param in vars(Config):
            if not getattr(Config, param):
                setattr(Config, param, getattr(parsed, pp, getattr(Config, param)))
        else:
            Log.error(f'Argument list param {param} was not consumed!')

#
#
#########################################

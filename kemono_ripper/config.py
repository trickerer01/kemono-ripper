# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from __future__ import annotations

import inspect
import pathlib
from typing import TypedDict

from aiohttp import ClientTimeout

from .defs import (
    COMMENT_PATH_FORMAT,
    CONFIG_NAME_DEFAULT,
    CONNECT_TIMEOUT_SOCKET_READ,
    NUM_EXTERNAL_SITES,
    DateRange,
    NumRange,
    SupportedExternalWebsites,
)

if False is True:  # for hinting only
    from .api import APIAddress, APIService, PostPageScanResult  # noqa: I001

__all__ = ('Config', 'ExternalURLHandlerConfig')


class DownloaderConfig(TypedDict):
    proxy: str


def download_config_default(config: Config) -> DownloaderConfig:
    return DownloaderConfig(
        proxy=config.proxy,
    )


class ConfigJSON(TypedDict):
    api_address: str
    service: str
    skip_cache: bool
    force_cache: bool
    max_jobs: int
    dest_base: pathlib.Path
    _path_format_comment: str
    path_format: str
    indent: int
    proxy: str
    logging_flags: int
    disable_log_colors: bool
    no_external_links: bool
    timeout: int
    retries: int
    extra_headers: list[tuple[str, str]]
    extra_cookies: list[tuple[str, str]]
    per_website_config: dict[str, DownloaderConfig]


PER_WEBSITE_CONFIG_DEFAULT = dict.fromkeys((_.value for _ in SupportedExternalWebsites.__members__.values()), DownloaderConfig(proxy=''))
assert len(PER_WEBSITE_CONFIG_DEFAULT) == NUM_EXTERNAL_SITES


class BaseConfig:
    NAMESPACE_VARS_REMAP = {
        'file': 'src_file',
        'path': 'dest_base',
        'log_level': 'logging_flags',
        'header': 'extra_headers',
        'cookie': 'extra_cookies',
        'post_id': 'post_ids',
        'lines': 'filter_file_lines',
        'ids': 'filter_post_ids',
        'notag': 'filter_post_tags',
        'nouser': 'filter_user_id',
        'imported': 'filter_post_imported',
        'published': 'filter_post_published',
        'ext': 'filter_extensions',
    }

    def __init__(self) -> None:
        self.subcommand_1: str = ''
        self.subcommand_2: str = ''
        self.subcommand_3: str = ''
        self.api_address: APIAddress | None = None
        self.service: APIService | None = None
        self.search_string: str | None = None
        self.search_tags: list[str] | None = None
        self.post_ids: list[str] | None = None
        '''post scan id, post rip id'''
        self.creator_id: str | None = None
        '''post scan id, post rip id'''
        self.same_creator: bool | None = None
        '''same creator for all posts being scanned see `post list`'''
        self.links: list[PostPageScanResult] | None = None
        '''post scan link, post rip link'''
        self.pattern: str | None = None
        '''creator list pattern'''
        self.skip_cache: bool | None = None
        '''json caches'''
        self.force_cache: bool | None = None
        '''json caches'''
        self.indent: int | None = None
        '''indentation for saved json files'''
        self.prune: bool | None = None
        '''prune extra info from dumps'''
        self.filter_file_lines: NumRange | None = None
        self.filter_filesize: NumRange | None = None
        self.filter_filename: str | None = None
        self.filter_post_ids: NumRange | None = None
        self.filter_post_tags: list[str] | None = None
        self.filter_post_imported: DateRange | None = None
        self.filter_post_published: DateRange | None = None
        self.filter_extensions: list[str] | None = None
        self.filter_user_id: list[str] | None = None
        self.src_file: pathlib.Path | None = None
        self.max_jobs: int | None = None
        self.path_format: str | None = None
        # no args
        self.per_website_config: dict[str, DownloaderConfig] = PER_WEBSITE_CONFIG_DEFAULT.copy()
        # common
        self.dest_base: pathlib.Path | None = None
        self.proxy: str | None = None
        self.download_mode: str | None = None
        self.logging_flags: int | None = None
        self.disable_log_colors: bool | None = None
        self.no_external_links: bool | None = None
        self.timeout: ClientTimeout | None = None
        self.retries: int | None = None
        self.extra_headers: list[tuple[str, str]] | None = None
        self.extra_cookies: list[tuple[str, str]] | None = None
        # extra (not configurable)
        self.nodelay: bool = False
        self.noconfirm: bool = True

    def _reset(self) -> None:
        self.__init__()  # noqa: PLC2801

    def get_action_string(self) -> str:
        action_name = ' '.join(getattr(self, _) for _ in vars(self) if _.startswith('subcommand')).strip()
        return action_name

    def to_json(self) -> ConfigJSON:
        return ConfigJSON(
            api_address=self.api_address,
            service=self.service,
            skip_cache=self.skip_cache,
            force_cache=self.force_cache,
            max_jobs=self.max_jobs,
            dest_base=self.dest_base,
            _path_format_comment=COMMENT_PATH_FORMAT,
            path_format=self.path_format,
            indent=self.indent,
            proxy=self.proxy,
            logging_flags=self.logging_flags,
            disable_log_colors=self.disable_log_colors,
            no_external_links=self.no_external_links,
            timeout=int(self.timeout.connect),
            retries=self.retries,
            extra_headers=self.extra_headers,
            extra_cookies=self.extra_cookies,
            per_website_config=self.per_website_config,
        )

    def from_json(self, json_: ConfigJSON) -> None:
        for param in inspect.get_annotations(ConfigJSON).keys().mapping:
            if param.endswith('_comment'):
                continue
            assert param in json_, f'Missing config param: {param}!'
        for k, v in json_.items():
            if k.endswith('_comment'):
                continue
            if k == 'dest_base':
                v = pathlib.Path(v)
            elif k == 'timeout':
                v = ClientTimeout(total=None, connect=v, sock_connect=v, sock_read=float(CONNECT_TIMEOUT_SOCKET_READ))
            setattr(self, k, v)

    @staticmethod
    def default_config_path() -> pathlib.Path:
        root_path = pathlib.Path(__file__).parent.parent
        return root_path / CONFIG_NAME_DEFAULT


class ExternalURLHandlerConfig:
    # MEGA, Mediafire
    filter_filesize: NumRange | None
    # MEGA, Mediafire
    filter_filename: str | None
    # MEGA, Mediafire
    filter_extensions: list[str] | None
    # MEGA, Mediafire
    dump_links: bool | None
    # MEGA, Mediafire
    dump_structure: bool | None
    # MEGA, Mediafire
    links_file: pathlib.Path | None
    # MEGA, Mediafire
    links: list[str] | None
    # MEGA, Mediafire
    max_jobs: int | None
    # MEGA, Mediafire
    dest_base: pathlib.Path | None
    # MEGA, Mediafire
    proxy: str | None
    # MEGA, Mediafire
    download_mode: str | None
    # MEGA, Mediafire
    logging_flags: int
    # MEGA, Mediafire
    nocolors: bool | None
    # MEGA, Mediafire
    timeout: ClientTimeout | None
    # MEGA, Mediafire
    retries: int
    # MEGA, Mediafire
    extra_headers: list[tuple[str, str]] | None
    # MEGA, Mediafire
    extra_cookies: list[tuple[str, str]] | None
    # MEGA, Mediafire
    nodelay: bool
    # MEGA, Mediafire
    noconfirm: bool

    def __init__(self, config: BaseConfig, host: str, **overrides) -> None:
        self.dump_links: bool | None = False
        self.dump_structure: bool | None = False
        self.links_file: pathlib.Path | None = None
        self.filter_filesize: NumRange | None = overrides.pop('filter_filesize', config.filter_filesize)
        self.filter_filename: str | None = overrides.pop('filter_filename', config.filter_filename)
        self.filter_extensions: list[str] | None = overrides.pop('filter_extensions', config.filter_extensions)
        self.links: list[str] | None = overrides.pop('links', config.links)
        self.max_jobs: int | None = overrides.pop('max_jobs', config.max_jobs)
        self.dest_base: pathlib.Path | None = overrides.pop('dest_base', config.dest_base)
        self.proxy: str | None = overrides.pop('proxy', config.per_website_config.get(host, download_config_default(config))['proxy'])
        self.download_mode: str | None = overrides.pop('download_mode', config.download_mode)
        self.logging_flags: int = overrides.pop('logging_flags', config.logging_flags)
        self.nocolors: bool | None = overrides.pop('nocolors', config.disable_log_colors)
        self.timeout: ClientTimeout | None = overrides.pop('timeout', config.timeout)
        self.retries: int = overrides.pop('retries', config.retries)
        self.extra_headers: list[tuple[str, str]] | None = overrides.pop('extra_headers', config.extra_headers)
        self.extra_cookies: list[tuple[str, str]] | None = overrides.pop('extra_cookies', config.extra_cookies)
        self.nodelay: bool = overrides.pop('nodelay', config.nodelay)
        self.noconfirm: bool = overrides.pop('noconfirm', True)


Config: BaseConfig = BaseConfig()

#
#
#########################################

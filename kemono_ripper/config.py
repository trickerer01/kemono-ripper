# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import inspect
import pathlib
from typing import Protocol, TypedDict

from aiohttp import ClientTimeout

from .defs import CONFIG_NAME_DEFAULT, CONNECT_TIMEOUT_SOCKET_READ, NumRange

if False is True:  # for hinting only
    from .api import APIAddress, APIService, PostPageScanResult  # noqa: I001

__all__ = ('Config', 'ExternalURLHandlerConfig', 'MegaConfig')


class ConfigJSON(TypedDict):
    api_address: str
    service: str
    skip_cache: bool
    max_jobs: int
    dest_base: str
    proxy: str
    logging_flags: int
    disable_log_colors: bool
    timeout: int
    retries: int
    extra_headers: list[tuple[str, str]]
    extra_cookies: list[tuple[str, str]]


class BaseConfig:
    NAMESPACE_VARS_REMAP = {
        'file': 'src_file',
        'path': 'dest_base',
        'log_level': 'logging_flags',
        'header': 'extra_headers',
        'cookie': 'extra_cookies',
        'post_id': 'post_ids',
    }

    def __init__(self) -> None:
        # new new
        self.subcommand_1: str = ''
        self.subcommand_2: str = ''
        self.subcommand_3: str = ''
        self.api_address: APIAddress | None = None
        self.service: APIService | None = None
        self.post_ids: list[int] | None = None
        '''post scan id, post rip id'''
        self.creator_id: int | None = None
        '''post scan id, post rip id'''
        self.same_creator: bool | None = None
        '''same creator for all posts being scanned see `post list`'''
        self.links: list[PostPageScanResult] | None = None
        '''post scan link, post rip link'''
        self.pattern: str | None = None
        '''creator list pattern'''
        self.skip_cache: bool | None = None
        '''creator list cache'''
        self.indent: int | None = None
        '''indentation for saved json files'''
        self.prune: bool | None = None
        '''prune extra info from dumps'''
        # new
        self.filter_filesize: NumRange | None = None
        self.filter_filename: str | None = None
        self.src_file: pathlib.Path | None = None
        self.max_jobs: int | None = None
        # common
        self.dest_base: pathlib.Path | None = None
        self.proxy: str | None = None
        self.download_mode: str | None = None
        self.logging_flags: int | None = None
        self.disable_log_colors: bool | None = None
        self.timeout: ClientTimeout | None = None
        self.retries: int | None = None
        self.extra_headers: list[tuple[str, str]] | None = None
        self.extra_cookies: list[tuple[str, str]] | None = None
        # extra (not configurable)
        self.nodelay: bool = False

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
            max_jobs=self.max_jobs,
            dest_base=self.dest_base.as_posix(),
            proxy=self.proxy,
            logging_flags=self.logging_flags,
            disable_log_colors=self.disable_log_colors,
            timeout=int(self.timeout.connect),
            retries=self.retries,
            extra_headers=self.extra_headers,
            extra_cookies=self.extra_cookies,
        )

    def from_json(self, json_: ConfigJSON) -> None:
        num_keys = len(inspect.get_annotations(ConfigJSON))
        assert len(json_) >= num_keys, f'Invalid settings file format ({len(json_):d} keys found, expected {num_keys:d})!'
        for k, v in json_.items():
            if k not in vars(self):
                raise KeyError(f'Invalid setting key \'{k}\' found with value \'{v!s}\'!')
            if k == 'dest_base':
                v = pathlib.Path(v)
            elif k == 'timeout':
                v = ClientTimeout(total=None, connect=v, sock_connect=v, sock_read=float(CONNECT_TIMEOUT_SOCKET_READ))
            setattr(self, k, v)

    @staticmethod
    def default_config_path() -> pathlib.Path:
        root_path = pathlib.Path(__file__).parent.parent
        return root_path / CONFIG_NAME_DEFAULT


class ExternalURLHandlerConfig(Protocol):
    filter_filesize: NumRange | None
    filter_filename: str | None
    dump_links: bool | None
    dump_structure: bool | None
    links_file: pathlib.Path | None
    links: list[str] | None
    max_jobs: int | None
    dest_base: pathlib.Path | None
    proxy: str | None
    download_mode: str | None
    logging_flags: int
    nocolors: bool | None
    timeout: ClientTimeout | None
    retries: int
    extra_headers: list[tuple[str, str]] | None
    extra_cookies: list[tuple[str, str]] | None
    nodelay: bool


class MegaConfig:
    def __init__(self, config: BaseConfig, **overrides) -> None:
        self.dump_links: bool | None = False
        self.dump_structure: bool | None = False
        self.links_file: pathlib.Path | None = None
        self.filter_filesize: NumRange | None = overrides.pop('filter_filesize', config.filter_filesize)
        self.filter_filename: str | None = overrides.pop('filter_filename', config.filter_filename)
        self.links: list[str] | None = overrides.pop('links', config.links)
        self.max_jobs: int | None = overrides.pop('max_jobs', config.max_jobs)
        self.dest_base: pathlib.Path | None = overrides.pop('dest_base', config.dest_base)
        self.proxy: str | None = ''
        self.download_mode: str | None = overrides.pop('download_mode', config.download_mode)
        self.logging_flags: int = overrides.pop('logging_flags', config.logging_flags)
        self.nocolors: bool | None = overrides.pop('nocolors', config.disable_log_colors)
        self.timeout: ClientTimeout | None = overrides.pop('timeout', config.timeout)
        self.retries: int = overrides.pop('retries', config.retries)
        self.extra_headers: list[tuple[str, str]] | None = overrides.pop('extra_headers', config.extra_headers)
        self.extra_cookies: list[tuple[str, str]] | None = overrides.pop('extra_cookies', config.extra_cookies)
        self.nodelay: bool = overrides.pop('nodelay', config.nodelay)


Config: BaseConfig = BaseConfig()

#
#
#########################################

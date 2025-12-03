# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

if False is True:  # for hinting only
    import pathlib  # noqa: I001
    from aiohttp import ClientTimeout  # noqa: I001
    from .api import APIAddress, APIService  # noqa: I001
    from .defs import NumRange, PostPageScanResult

__all__ = ('Config',)


class BaseConfig:
    NAMESPACE_VARS_REMAP = {
        'file': 'links_file',
        'path': 'dest_base',
        'log_level': 'logging_flags',
        'disable_log_colors': 'nocolors',
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
        self.pattern: str | None = None
        self.post_ids: list[int] | None = None
        self.creator_id: int | None = None
        self.links: list[PostPageScanResult] | None = None
        self.skip_cache: bool | None = None
        # new
        self.filter_filesize: NumRange | None = None
        self.filter_filename: str | None = None
        self.links_file: pathlib.Path | None = None  # TODO: post scan file, post rip file
        self.max_jobs: int | None = None
        # common
        self.dest_base: pathlib.Path | None = None
        self.proxy: str | None = None
        self.download_mode: str | None = None
        self.logging_flags: int = 0
        self.nocolors: bool | None = None
        self.timeout: ClientTimeout | None = None
        self.retries: int = 0
        self.extra_headers: list[tuple[str, str]] | None = None
        self.extra_cookies: list[tuple[str, str]] | None = None
        # extra (not configurable)
        self.nodelay: bool = False

    def _reset(self) -> None:
        self.__init__()  # noqa: PLC2801


Config: BaseConfig = BaseConfig()

#
#
#########################################

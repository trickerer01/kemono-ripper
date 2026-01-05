# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import asyncio
import functools
import pathlib
from collections.abc import Callable
from io import StringIO
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from kemono_ripper import APP_NAME, APP_VERSION, main_sync
from kemono_ripper.analyzer import SUPPORTED_EXTENSIONS
from kemono_ripper.api import APIAddress, APIService, DownloadFlags, PostInfo, RequestQueue
from kemono_ripper.cache import Cache
from kemono_ripper.config import Config
from kemono_ripper.defs import UTF8
from kemono_ripper.logger import Log
from kemono_ripper.main import at_startup

COMMON_ARGS = ('-v', 'trace', '-j', '8')
COMMON_ARGS_C = (*COMMON_ARGS, '--skip-cache')
COMMON_ARGS_FC = (*COMMON_ARGS, '--force-cache')

RUN_CONN_TESTS = 0


def test_prepare(log=False) -> Callable[[], Callable[[], None]]:
    def invoke1(test_func: Callable[[...], None]) -> Callable[[], None]:
        @functools.wraps(test_func)
        def invoke_test(*args, **kwargs) -> None:
            def set_up_test() -> None:
                Log._disabled = not log
                Config._reset()
                RequestQueue._reset()
            set_up_test()
            test_func(*args, **kwargs)
        return invoke_test
    return invoke1


class DataIntegrityTests(TestCase):
    @test_prepare()
    def test_integrity_config(self):
        assert all(hasattr(Config, _) for _ in Config.NAMESPACE_VARS_REMAP.values())
        print(f'{self._testMethodName} passed')

    @test_prepare()
    def test_integrity_extensions(self):
        assert all(_.startswith('.') for _ in SUPPORTED_EXTENSIONS)
        print(f'{self._testMethodName} passed')


class CmdTests(TestCase):

    @test_prepare()
    def test_output_version(self):
        with patch('sys.stdout', new_callable=StringIO) as stdout:
            main_sync(['--version'])
            self.assertEqual(f'{APP_NAME} {APP_VERSION}', stdout.getvalue().strip('\n'))
        print(f'{self._testMethodName} passed')

    @test_prepare()
    def test_cmd_config(self):
        arglist1 = ['config', 'create']
        main_sync(arglist1)
        self.assertTrue(Config.default_config_path().is_file())
        arglist2 = ['config', 'modify', '--path-format', '{creator_id} - {post_id} - {post_title}']
        main_sync(arglist2)
        self.assertEqual('{creator_id} - {post_id} - {post_title}', Config.path_format)
        print(f'{self._testMethodName} passed')

    @test_prepare()
    def test_cmd_command_cl(self):
        if not RUN_CONN_TESTS:
            return
        with TemporaryDirectory(prefix=f'{APP_NAME}_{self._testMethodName}_') as tempdir:
            arglist1 = ['creator', 'list', 'xavie']
            arglist1.extend(('--path', tempdir, *COMMON_ARGS_C))
            main_sync(arglist1)
        print(f'{self._testMethodName} passed')

    @test_prepare()
    def test_cmd_command_cd(self):
        if not RUN_CONN_TESTS:
            return
        with TemporaryDirectory(prefix=f'{APP_NAME}_{self._testMethodName}_') as tempdir:
            arglist1 = ['creator', 'dump', '--prune']
            arglist1.extend(('--path', tempdir, *COMMON_ARGS))
            main_sync(arglist1)
        print(f'{self._testMethodName} passed')

    @test_prepare()
    def test_cmd_command_cr1(self):
        if not RUN_CONN_TESTS:
            return
        with TemporaryDirectory(prefix=f'{APP_NAME}_{self._testMethodName}_') as tempdir:
            arglist1 = [
                'creator', 'rip', '2318129271453', '--published', '2022-01-01..2022-06-01', '--service', 'gumroad', '--ext', '.fbx',
            ]
            arglist1.extend(('--path', tempdir, *COMMON_ARGS_C))
            main_sync(arglist1)
        print(f'{self._testMethodName} passed')

    @test_prepare()
    def test_cmd_command_cr2_cache(self):
        if not RUN_CONN_TESTS:
            return
        post_id = 'uitrim'
        creator_id = '2318129271453'
        service: APIService = 'gumroad'
        apiaddr = APIAddress.__args__[0]
        arglist1 = ['creator', 'rip', creator_id, '--published', '2022-01-01..2022-06-01', '--service', service, '--api-addr', apiaddr]
        at_startup(arglist1)
        asyncio.run(Cache().__aenter__(Cache()))  # noqa PLC2801
        asyncio.run(Cache.clear_post_info_cache((post_id,)))
        cache1: list[PostInfo] = asyncio.run(Cache.get_post_info_cache((post_id,)))
        asyncio.run(Cache().__aexit__(Cache(), None, None, None))
        with TemporaryDirectory(prefix=f'{APP_NAME}_{self._testMethodName}_') as tempdir:
            arglist1.extend(('--path', tempdir, *COMMON_ARGS))
            main_sync(arglist1)
        asyncio.run(Cache().__aenter__(Cache()))  # noqa PLC2801
        cache2: list[PostInfo] = asyncio.run(Cache.get_post_info_cache((post_id,)))
        asyncio.run(Cache().__aexit__(Cache(), None, None, None))
        self.assertEqual(0, len(cache1))
        self.assertEqual(1, len(cache2))
        self.assertEqual(post_id, cache2[0].post_id)
        self.assertTrue(bool(cache2[0].status.flags & DownloadFlags.COMPLETED))
        print(f'{self._testMethodName} passed')

    @test_prepare()
    def test_cmd_command_pl(self):
        if not RUN_CONN_TESTS:
            return
        with TemporaryDirectory(prefix=f'{APP_NAME}_{self._testMethodName}_') as tempdir:
            arglist1 = [
                'post', 'list', '2318129271453', '--published', '2022-01-01..2022-06-01', '--service', 'gumroad',
            ]
            arglist1.extend(('--path', tempdir, *COMMON_ARGS_C))
            main_sync(arglist1)
        print(f'{self._testMethodName} passed')

    @test_prepare()
    def test_cmd_command_pse1(self):
        if not RUN_CONN_TESTS:
            return
        with TemporaryDirectory(prefix=f'{APP_NAME}_{self._testMethodName}_') as tempdir:
            arglist1 = [
                'post', 'search', '', 'draenei', 'warcraft',
                '--notag', 'world*warcraft', '--notag', 'wow',
                '--notag', 'hmv', '--notag', 'pmv', '--notag', 'compilation',
            ]
            arglist1.extend(('--path', tempdir, *COMMON_ARGS_C))
            main_sync(arglist1)
        print(f'{self._testMethodName} passed')

    @test_prepare()
    def test_cmd_command_pse2(self):
        if not RUN_CONN_TESTS:
            return
        with TemporaryDirectory(prefix=f'{APP_NAME}_{self._testMethodName}_') as tempdir:
            arglist1 = [
                'post', 'search', 'draenei', 'fel',
                '--notag', '*warcraft*', '--notag', 'wow',
                '--notag', 'hmv', '--notag', 'pmv', '--notag', 'compilation',
            ]
            arglist1.extend(('--path', tempdir, *COMMON_ARGS_C))
            main_sync(arglist1)
        print(f'{self._testMethodName} passed')

    @test_prepare()
    def test_cmd_command_psi1(self):
        if not RUN_CONN_TESTS:
            return
        with TemporaryDirectory(prefix=f'{APP_NAME}_{self._testMethodName}_') as tempdir:
            arglist1 = [
                'post', 'scan', 'id', '84634191', '--creator-id', '5149963', '--service', 'patreon',
            ]
            arglist1.extend(('--path', tempdir, *COMMON_ARGS_C))
            main_sync(arglist1)
        print(f'{self._testMethodName} passed')

    @test_prepare()
    def test_cmd_command_psi2(self):
        if not RUN_CONN_TESTS:
            return
        with TemporaryDirectory(prefix=f'{APP_NAME}_{self._testMethodName}_') as tempdir:
            arglist1 = [
                'post', 'scan', 'id', '84926322', '85027233', '--same-creator', '--service', 'patreon',
            ]
            arglist1.extend(('--path', tempdir, *COMMON_ARGS_C))
            main_sync(arglist1)
        print(f'{self._testMethodName} passed')

    @test_prepare()
    def test_cmd_command_psu(self):
        if not RUN_CONN_TESTS:
            return
        with TemporaryDirectory(prefix=f'{APP_NAME}_{self._testMethodName}_') as tempdir:
            apiaddr: str = APIAddress.__args__[0]
            arglist1 = [
                'post', 'scan', 'url', f'https://{apiaddr}/patreon/user/104244/post/88397782',
            ]
            arglist1.extend(('--path', tempdir, *COMMON_ARGS_C))
            main_sync(arglist1)
        print(f'{self._testMethodName} passed')

    @test_prepare()
    def test_cmd_command_psf(self):
        if not RUN_CONN_TESTS:
            return
        with TemporaryDirectory(prefix=f'{APP_NAME}_{self._testMethodName}_') as tempdir:
            apiaddr: str = APIAddress.__args__[0]
            tempfile_path = pathlib.Path(tempdir).joinpath('posts.list')
            with open(tempfile_path, 'wt', encoding=UTF8, newline='\n') as outfile_posts:
                outfile_posts.writelines((
                    f'https://{apiaddr}/patreon/user/104244/post/86579270 \'Boss Rush Friday - July 7th\', file: \'boss rush 899.jpg\'\n',
                    f'https://{apiaddr}/patreon/user/104244/post/89510439 \'Boss Rush Friday - Sep 5th\', file: \'boss rush 929.jpg\'\n',
                ))
            arglist1 = [
                'post', 'scan', 'file', tempfile_path.as_posix(),
            ]
            arglist1.extend(('--path', tempdir, *COMMON_ARGS_C))
            main_sync(arglist1)
        print(f'{self._testMethodName} passed')

    @test_prepare()
    def test_cmd_command_pri(self):
        if not RUN_CONN_TESTS:
            return
        with TemporaryDirectory(prefix=f'{APP_NAME}_{self._testMethodName}_') as tempdir:
            arglist1 = [
                'post', 'rip', 'id', '123238453', '--service', 'patreon', '--ext', '.jpg',
            ]
            arglist1.extend(('--path', tempdir, *COMMON_ARGS_C))
            main_sync(arglist1)
        print(f'{self._testMethodName} passed')

    @test_prepare()
    def test_cmd_command_pru(self):
        if not RUN_CONN_TESTS:
            return
        with TemporaryDirectory(prefix=f'{APP_NAME}_{self._testMethodName}_') as tempdir:
            apiaddr: str = APIAddress.__args__[0]
            arglist1 = [
                'post', 'rip', 'url', f'https://{apiaddr}/patreon/user/104244/post/136184617', '--ext', '.jpg',
            ]
            arglist1.extend(('--path', tempdir, *COMMON_ARGS_C))
            main_sync(arglist1)
        print(f'{self._testMethodName} passed')

    @test_prepare()
    def test_cmd_command_prf(self):
        if not RUN_CONN_TESTS:
            return
        with TemporaryDirectory(prefix=f'{APP_NAME}_{self._testMethodName}_') as tempdir:
            apiaddr: str = APIAddress.__args__[0]
            tempfile_path = pathlib.Path(tempdir).joinpath('posts.list')
            with open(tempfile_path, 'wt', encoding=UTF8, newline='\n') as outfile_posts:
                outfile_posts.writelines((
                    f'https://{apiaddr}/patreon/user/695492/post/62459364 \'The Invasion of Rohk\'aka - Epilogue\', file: \'None\'\n',
                    f'https://{apiaddr}/patreon/user/104244/post/98471435 \'Boss Rush Friday - Jan 19th\', file: \'boss rush 977.jpg\'\n',
                ))
            arglist1 = [
                'post', 'rip', 'file', tempfile_path.as_posix(),
            ]
            arglist1.extend(('--path', tempdir, *COMMON_ARGS_C))
            main_sync(arglist1)
        print(f'{self._testMethodName} passed')

    @test_prepare()
    def test_cmd_command_ptd(self):
        if not RUN_CONN_TESTS:
            return
        with TemporaryDirectory(prefix=f'{APP_NAME}_{self._testMethodName}_') as tempdir:
            arglist1 = ['post', 'tags', 'dump', '--service', 'patreon']
            arglist1.extend(('--path', tempdir, *COMMON_ARGS))
            main_sync(arglist1)
        print(f'{self._testMethodName} passed')

#
#
#########################################

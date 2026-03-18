# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import itertools
from collections import namedtuple
from collections.abc import Iterable, Sequence
from typing import TypeAlias

from yarl import URL

from .api import DownloadStatus, FormattablePost, PostInfo, PostLinkInfo, SQLSchema, UserInfo
from .config import Config
from .defs import CACHE_DB_NAME_DEFAULT
from .formatter import format_path
from .logger import Log

try:
    import sqlite3
    DBConnection: TypeAlias = sqlite3.Connection
except ImportError:
    from typing import Generic, TypeAlias, TypeVar
    T_co = TypeVar('T_co', covariant=True)

    class DummyMethod(Generic[T_co]):
        _ret_type: T_co

        # PyCharm doesn't recognize 3.10+ hinting for 'type[TYPE]'
        # noinspection PyUnresolvedReferences
        def __init__(self, ret_type: type[T_co]) -> None:
            self.__class__._ret_type = ret_type

        def __call__(self, *args, **kwargs) -> T_co:
            return self._ret_type()

    class DummySqlite3Connection:
        __enter__ = __exit__ = execute = executemany = close = DummyMethod(type(None))

    class DummySqlite3:
        connect = DummyMethod(DummySqlite3Connection)

    sqlite3 = DummySqlite3
    DBConnection: TypeAlias = DummySqlite3Connection

__all__ = ('Cache',)

QueryResult: TypeAlias = list[tuple[str | int | float | bool | None, ...]]
SchemaDumpRow = namedtuple('SchemaDumpRow', ('cid', 'col_name', 'data_type', 'not_null', 'default', 'is_pk'))

TableSchemas = (PostInfo, PostLinkInfo, UserInfo)


def _make_schema_string(schema: SQLSchema) -> str:
    fields = [
        f'`{col.name}` {col.data_type}{"" if not col.not_null else " NOT NULL"}{"" if not col.default else f" DEFAULT {col.default}"}'
        for col in schema.columns
    ]
    pk_cols = (','.join(f'`{_}`' for _ in schema.primary_key),) if schema.primary_key else ()
    pk = f',\n     PRIMARY KEY ({",".join(pk_cols)})' if pk_cols else ''
    fields_str = ',\n    '.join(fields)
    schema_str = f'`{schema.table_name}` (\n    {fields_str}{pk}\n)'
    return schema_str


def _verify_schema(schema: SQLSchema, schema_dump: QueryResult) -> bool:
    if len(schema.columns) != len(schema_dump):
        return False
    for idx, r in enumerate(schema_dump):
        row = SchemaDumpRow(*r)
        schema_col = schema.columns[idx]
        if row.col_name != schema_col.name:
            return False
        if row.data_type != schema_col.data_type:
            return False
        if bool(row.not_null) is not schema_col.not_null:
            return False
        if row.default != schema_col.default:
            return False
        if row.is_pk and row.col_name not in schema.primary_key:
            return False
    return True


class Cache:
    _db: DBConnection | None = None

    @classmethod
    async def __aenter__(cls, _self) -> None:  # noqa PLE0302
        assert cls._db is None
        Log.debug(f'Opening cache DB \'{CACHE_DB_NAME_DEFAULT}\'...')
        cls._db = sqlite3.connect(f'{Config.default_config_path().with_name(CACHE_DB_NAME_DEFAULT).as_posix()}', isolation_level=None)
        if not hasattr(cls._db, 'in_transaction'):
            Log.warn('Warning: sqlite3 module in unavailable! Caching will be disabled!')
            return
        await cls._ensure_db_schema()

    @classmethod
    async def __aexit__(cls, _self, exc_type, exc_val, exc_tb) -> None:  # noqa PLE0302
        cls._db.close()
        cls._db = None

    @staticmethod
    def _table_name_from_schema(schema: str) -> str:
        return schema[:schema.find(' ')].strip('`')

    @staticmethod
    async def _ensure_db_schema() -> None:
        for tab in TableSchemas:
            schema = _make_schema_string(tab.sql_schema)
            await Cache._execute_one((f'CREATE TABLE IF NOT EXISTS {schema}', ()))
            table_name = Cache._table_name_from_schema(schema)
            schema_existing = await Cache._dump_table_schema(table_name)
            assert _verify_schema(tab.sql_schema, schema_existing), (
                f'Invalid table {table_name} schema detected!\n\'\'\'\n{schema_existing!s}\n\'\'\'\nExpected:\n\'\'\'\n{schema!s}\n\'\'\''
                f'\nDelete outdated schema DB or fix it manually!'
            )

    @staticmethod
    async def _dump_table_schema(table_name: str) -> QueryResult:
        # results = await Cache._query("SELECT `sql` FROM `sqlite_master` WHERE `type`='table' AND `name`=?", (table_name,))
        results = await Cache._query(f"PRAGMA TABLE_INFO('{table_name}')")
        return results

    @staticmethod
    async def _execute_one(*queries: tuple[str, Sequence[str | int | float | bool]]) -> None:
        assert Cache._db
        with Cache._db:
            [Cache._db.execute(query, params) for query, params in queries]

    @staticmethod
    async def _execute_many(*queries: tuple[str, Sequence[Sequence[str | int | float | bool]]]) -> None:
        if not queries:
            return
        assert Cache._db
        with Cache._db:
            [Cache._db.executemany(query, params) for query, params in queries]

    @staticmethod
    async def _query(query: str, params: Sequence[str | int | float | bool] = ()) -> QueryResult:
        assert Cache._db
        with Cache._db:
            return Cache._db.execute(f'{query};', params).fetchall()

    @staticmethod
    async def get_post_info_cache(post_ids_: Iterable[str]) -> dict[str, PostInfo]:
        post_ids = ','.join(f'\'{_}\'' for _ in post_ids_)
        presults = await Cache._query(
            'SELECT {columns} FROM `cache_post` '
            'WHERE `post_id` IN ({ids})'
            .format(columns=','.join(f'`{_.name}`' for _ in PostInfo.sql_schema.columns), ids=post_ids), ())
        plresults = await Cache._query(
            'SELECT {columns} FROM `cache_post_link` '
            'WHERE `post_id` IN ({ids}) ORDER BY `post_id`'
            .format(columns=','.join(f'`{_.name}`' for _ in PostLinkInfo.sql_schema.columns), ids=post_ids), ())
        post_infos: dict[str, PostInfo] = {}
        for pr in presults:
            fp = FormattablePost(post_id=pr[0], user_id=pr[1], service=pr[2], title=pr[3], added=pr[4], published=pr[5],
                                 user_name=(await Cache.get_user_info_cache(pr[1], pr[2])).user_name)
            post_infos[pr[0]] = PostInfo(pr[0], pr[1], pr[2], pr[3], pr[4], pr[5], pr[6], pr[7].split(','), pr[8],
                                         Config.dest_base.joinpath(format_path(fp, Config.path_format)), [], DownloadStatus(flags=pr[9]))
        for plr in plresults:
            pi = post_infos.get(plr[0])
            if pi is None:
                continue
            pi.links.append(PostLinkInfo(plr[0], plr[1], URL(plr[2]),
                                         pi.dest.joinpath(plr[1]), DownloadStatus(expected_size=plr[3], flags=plr[4])))
        return post_infos

    @staticmethod
    async def store_post_info_cache(post_infos: Iterable[PostInfo]) -> None:
        await Cache._execute_many(
            (f'REPLACE INTO `cache_post` ({",".join(_.name for _ in PostInfo.sql_schema.columns)})\n'
             f'VALUES\n({",".join("?" * len(PostInfo.sql_schema.columns))})',
             [
                 (_.post_id, _.creator_id, _.service, _.title, _.imported, _.published, _.edited,
                  ','.join(_.tags), _.content, int(_.status.flags))
                 for _ in post_infos
             ],
             ),
        )

        await Cache._execute_many(
            (f'REPLACE INTO `cache_post_link` ({",".join(_.name for _ in PostLinkInfo.sql_schema.columns)})\n'
             f'VALUES\n({",".join("?" * len(PostLinkInfo.sql_schema.columns))})',
             [
                 (_.post_id, _.name, str(_.url), _.status.size, int(_.status.flags))
                 for _ in list[PostLinkInfo](itertools.chain(*(_.links for _ in post_infos)))
             ],
             ),
        )

    @staticmethod
    async def update_post_info_cache(post_info: PostInfo) -> None:
        await Cache._execute_one(('UPDATE `cache_post` SET `flags`=? WHERE `post_id`=?',
                                  (int(post_info.status.flags), post_info.post_id)))

    @staticmethod
    async def update_post_link_info_cache(post_link_info: PostLinkInfo) -> None:
        await Cache._execute_one(('UPDATE `cache_post_link` SET `size`=?, `flags`=? WHERE `post_id`=? AND `name`=?',
                                  (post_link_info.status.size, int(post_link_info.status.flags),
                                   post_link_info.post_id, post_link_info.name)))

    @staticmethod
    async def clear_post_info_cache(post_ids_: Iterable[str]) -> None:
        post_ids = ','.join(f'\'{_}\'' for _ in post_ids_)
        await Cache._execute_one((f'DELETE FROM `cache_post` WHERE `post_id` IN ({post_ids})', ()))
        await Cache._execute_one((f'DELETE FROM `cache_post_link` WHERE `post_id` IN ({post_ids})', ()))

    @staticmethod
    async def get_user_info_cache(user_id: str, service: str) -> UserInfo:
        uresults = await Cache._query(
            'SELECT {columns} FROM `cache_user` '
            'WHERE `service`=\'{service}\' AND `user_id`=\'{user_id}\''
            .format(columns=','.join(f'`{_.name}`' for _ in UserInfo.sql_schema.columns), user_id=user_id, service=service), ())
        if uresults:
            assert len(uresults) == 1
            uresult = uresults[0]
            return UserInfo(uresult[0], uresult[1], uresult[2])
        return UserInfo(user_id, user_id, service)

    @staticmethod
    async def get_user_infos_cache() -> list[UserInfo]:
        results = []
        uresults = await Cache._query(
            'SELECT {columns} FROM `cache_user`'.format(columns=','.join(f'`{_.name}`' for _ in UserInfo.sql_schema.columns)), ())
        if uresults:
            results.extend(UserInfo(_[0], _[1], _[2]) for _ in uresults)
        return results

    @staticmethod
    async def store_user_info_cache(user_infos: Iterable[UserInfo]) -> None:
        await Cache._execute_many(
            (f'INSERT OR IGNORE INTO `cache_user` ({",".join(_.name for _ in UserInfo.sql_schema.columns)})\n'
             f'VALUES\n({",".join("?" * len(UserInfo.sql_schema.columns))})',
             [(_.user_id, _.user_name, _.service) for _ in user_infos]),
        )

#
#
#########################################

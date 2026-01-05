# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

import itertools
import pathlib
from collections import defaultdict, namedtuple
from collections.abc import Iterable, Sequence
from typing import TypeAlias

from yarl import URL

from .api import DownloadStatus, PostInfo, PostLinkInfo, SQLSchema
from .config import Config
from .defs import CACHE_DB_NAME_DEFAULT
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
        for ntup in (PostInfo, PostLinkInfo):
            schema = _make_schema_string(ntup.sql_schema)
            await Cache._execute_one((f'CREATE TABLE IF NOT EXISTS {schema}', ()))
            table_name = Cache._table_name_from_schema(schema)
            schema_existing = await Cache._dump_table_schema(table_name)
            assert _verify_schema(ntup.sql_schema, schema_existing), (
                f'Invalid table {table_name} schema detected!\n\'\'\'\n{schema}\n\'\'\'\nExpected:\n\'\'\'\n{schema_existing!s}\n\'\'\''
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
    async def get_post_info_cache(post_ids_: Iterable[str]) -> list[PostInfo]:
        post_ids = ','.join(post_ids_)
        presults = await Cache._query(
            'SELECT {columns} FROM `cache_post` '
            'WHERE `post_id` IN ({ids})'
            .format(columns=','.join(_.name for _ in PostInfo.sql_schema.columns), ids=post_ids), ())
        plresults = await Cache._query(
            'SELECT {columns} FROM `cache_post_link` '
            'WHERE `post_id` IN ({ids}) ORDER BY `post_id`'
            .format(columns=','.join(_.name for _ in PostLinkInfo.sql_schema.columns), ids=post_ids), ())
        post_links: dict[str, list[PostLinkInfo]] = defaultdict(list[PostLinkInfo])
        for plr in plresults:
            post_links[plr[0]].append(
                PostLinkInfo(plr[0], plr[1], URL(plr[2]), pathlib.Path(plr[3]), DownloadStatus(expected_size=plr[4], flags=plr[5])),
            )
        post_infos: list[PostInfo] = []
        for pr in presults:
            post_info = PostInfo(pr[0], pr[1], pr[2], pr[3], pr[4], pr[5], pr[6], pr[7].split(','), pr[8],
                                 pathlib.Path(pr[9]), list(post_links.get(pr[0], [])), DownloadStatus(flags=pr[10]))
            post_infos.append(post_info)
        return post_infos

    @staticmethod
    async def store_post_info_cache(post_infos: Sequence[PostInfo]) -> None:
        await Cache._execute_many(
            (f'REPLACE INTO `cache_post` ({",".join(_.name for _ in PostInfo.sql_schema.columns)})\n'
             f'VALUES\n({",".join("?" * len(PostInfo.sql_schema.columns))})',
             [
                 (_.post_id, _.creator_id, _.service, _.title, _.imported, _.published, _.edited,
                  ','.join(_.tags), _.content, _.dest.as_posix(), int(_.status.flags))
                 for _ in post_infos
             ],
             ),
        )

        await Cache._execute_many(
            (f'REPLACE INTO `cache_post_link` ({",".join(_.name for _ in PostLinkInfo.sql_schema.columns)})\n'
             f'VALUES\n({",".join("?" * len(PostLinkInfo.sql_schema.columns))})',
             [
                 (_.post_id, _.name, str(_.url), _.path.as_posix(), _.status.size, int(_.status.flags))
                 for _ in list[PostLinkInfo](itertools.chain(*(_.links for _ in post_infos)))
             ],
             ),
        )

    @staticmethod
    async def update_post_info_cache(post_info: PostInfo) -> None:
        await Cache._execute_one(('UPDATE `cache_post` SET `dest`=?, `flags`=? WHERE `post_id`=?',
                                  (post_info.dest.as_posix(), int(post_info.status.flags), post_info.post_id)))

    @staticmethod
    async def update_post_link_info_cache(post_link_info: PostLinkInfo) -> None:
        await Cache._execute_one(('UPDATE `cache_post_link` SET `path`=?, `size`=?, `flags`=? WHERE `post_id`=? AND `name`=?',
                                  (post_link_info.path.as_posix(), post_link_info.status.size, int(post_link_info.status.flags),
                                   post_link_info.post_id, post_link_info.name)))

    @staticmethod
    async def clear_post_info_cache(post_ids_: Iterable[str]) -> None:
        post_ids = ','.join(post_ids_)
        await Cache._execute_one((f'DELETE FROM `cache_post` WHERE `post_id` IN ({post_ids})', ()))
        await Cache._execute_one((f'DELETE FROM `cache_post_link` WHERE `post_id` IN ({post_ids})', ()))

#
#
#########################################

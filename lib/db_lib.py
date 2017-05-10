#coding=utf8
"""https://aiomysql.readthedocs.io/en/latest/connection.html
"""
from itertools import islice
#-#import asyncio
import aiomysql
from asyncio import sleep
from asyncio import Lock
from asyncio import wait_for
from lib.conf_lib import conf
from lib.tools_lib import pcformat
from lib.applog import app_log
info, debug, error, warn = app_log.info, app_log.debug, app_log.error, app_log.warning
pcformat


class MySqlDb(object):
    """mysql连接封装

    提供额外的high level功能
    """
    D_CUR_TYPE = {'': aiomysql.Cursor,
                  'dict': aiomysql.DictCursor,
                  's': aiomysql.SSCursor,
                  None: aiomysql.Cursor,
                  }

    def __init__(self, conn):
        self.conn = conn
        self.cur = None  # used in transaction

    async def getAll(self, sql, args=None, cur_type=None):
        """获取多条记录
        """
        rcds = None
        cur = None
        cur_type = MySqlDb.D_CUR_TYPE.get(cur_type, '')
        try:
            cur = await self.conn.cursor(cur_type)
            await cur.execute(sql, args)
            rcds = await cur.fetchall()
        except:
            if cur:
                cur.close()
        return rcds

    async def texecute(self, sql, args=None, need_insertid=False):
        """事务内执行sql

        首个sql自动触发进入事务模式(非自动提交)
        """
        if self.get_autocommit():
            self.autocommit(False)
            self.cur = self.conn.cursor()

        r, insertid = None, None
        try:
            r = await self.cur.execute(sql, args)
            if need_insertid:
                insertid = self.cur.lastrowid
        except:
            error('got except executing sql %s args %s', sql, args, exc_info=True)
        return (r, insertid)

    async def begin(self):
        """开始事务模式
        """
        if self.cur:
            warn('transaction already began')
        else:
            if self.conn.get_autocommit():
                self.conn.autocommit(False)
                self.cur = self.conn.cursor()

    async def commit(self):
        """提交事务
        """
        if self.cur:
            try:
                self.conn.commit()
            finally:
                try:
                    self.cur.close()
                finally:
                    self.cur = None
        else:
            warn('transaction not begin')

    async def rollback(self):
        """回滚事务
        """
        if self.cur:
            try:
                self.conn.rollback()
            finally:
                try:
                    self.cur.close()
                finally:
                    self.cur = None
        else:
            warn('transaction not begin')

    async def getOne(self, sql, args=None, cur_type=None):
        """获取一条记录
        """
        rcds = None
        cur = None
        cur_type = MySqlDb.D_CUR_TYPE.get(cur_type, '')
        try:
            cur = await self.conn.cursor(cur_type)
            await cur.execute(sql, args)
            rcds = await cur.fetchone()
        finally:
            if cur:
                cur.close()
        return rcds

    async def execute(self, sql, args=None, need_insertid=False):
        """执行sql语句

        ``need_insertid`` 标示是否需要获取insertid
        """
        rcds, cur, insertid = None, None, None
        try:
            cur = await self.conn.cursor()
            await cur.execute(sql, args)
            rcds = await cur.fetchone()
            if need_insertid:
                insertid = cur.lastrowid
        finally:
            if cur:
                cur.close()
        return (rcds, insertid)

    async def batchExceute(self, sql, args, batch_count=5000):
        """批量执行多条sql

        每批执行 ``batch_count`` 条
        """
        l_batch = [args[i: i + batch_count] for i in xrange(0, len(args), batch_count)]
        nr_batch = len(l_batch)
        info('split to %d part(s)', nr_batch)
        cur, total_r = None, 0
        try:
            cur = await self.conn.cursor()
            for _i, l_args in enumerate(l_batch, 1):
                try:
                    r = await cur.executemany(sql, l_args)
                    info('%4d/%d batch execute return %s', _i, nr_batch, r)
                    total_r += int(r)
                except:
                    info('except ', exc_info=True)
        finally:
            if cur:
                cur.close()
        return total_r

    async def batchExceute1(self, sql, args, batch_count=5000):
        """批量执行多条sql 另外一种实现

        每批执行 ``batch_count`` 条
        """
        l_batch = [args[i: i + batch_count] for i in xrange(0, len(args), batch_count)]
        nr_batch = len(l_batch)
        info('split to %d part(s)', nr_batch)
        cur, total_r = None, 0
        try:
            cur = await self.conn.cursor()
            i = 1
            while 1:
                try:
                    l_args = l_batch.pop(0)
                except IndexError:
                    break
                else:
                    try:
                        r = await cur.executemany(sql, l_args)
                        info('%4d/%d batch execute return %s', i, nr_batch, r)
                        total_r += int(r)
                    except:
                        info('except ', exc_info=True)
                    finally:
                        i += 1
        finally:
            if cur:
                cur.close()
        return total_r

    async def batchExceuteEx(self, sql, args, batch_count=5000):
        """批量执行多条sql 另外一种实现，``args`` 用迭代器方式处理，支持超大 ``args``

        每批执行 ``batch_count`` 条
        """
        cur, total_r = None, 0
        it = iter(args)
        try:
            cur = await self.conn.cursor()
            i, nr_total = 1, 0
            while 1:
                l_args = tuple(islice(it, 0, batch_count))
                if not l_args:
                    info('total %s part(s) %s record(s) return %s', i, nr_total, total_r)
                    break
                nr_total += len(l_args)
                try:
                    r = await cur.executemany(sql, l_args)
                    info('%4d/???(total %s) batch execute return %s', i, nr_total, r)
                    total_r += int(r)
                except:
                    info('except ', exc_info=True)
                finally:
                    i += 1
        finally:
            if cur:
                cur.close()
        return total_r

    def close(self):
        """不真正关闭数据库 只处理未提交/回滚事务 为还回连接池做准备
        """
        if self.cur:
            warn('自动回滚未处理的事务!!!')
            self.rollback()

    def getConn(self):
        """获取底层真正的aiomysql连接对象
        """
        return self.conn


class MySqlManager(object):
    """aiomysql连接池封装，支持数据库自命名
    """
    POOL = {}
    LOCK = Lock()

    @staticmethod
    async def getConn(db_name='default'):
        """从连接池中获取数据库连接
        """
        while 1:
            pool = MySqlManager.POOL.get(db_name)
            if pool:
                break
            try:
                await wait_for(MySqlManager.LOCK.acquire(), 0.1)
            except TimeoutError:
                await sleep(0.1)
#-#                info('timeout waiting for lock %s', MySqlManager.LOCK)
            else:
                try:
                    cfg = conf['database'][db_name]
                    pool = await aiomysql.create_pool(host=cfg['host'], port=cfg['port'], user=cfg['user'], password=cfg['password'], db=cfg['db_name'], minsize=0, maxsize=200, loop=conf['loop'])
                    MySqlManager.POOL[db_name] = pool
                finally:
                    try:
                        MySqlManager.LOCK.release()
                    except RuntimeError:
                        info('lock %s already in unlocked stat ?', MySqlManager.LOCK)
                    finally:
                        break
        conn = await pool.acquire()
        conn_obj = MySqlDb(conn)
#-#        info('acquired %s %s', db_name, conn)
#-#        MySqlManager.info(db_name)
        return conn_obj

    @staticmethod
    def info(db_name='default'):
        pool = MySqlManager.POOL[db_name]
        info('mysql pool stat: %s total %s free %s', db_name, pool.size, pool.freesize)

    @staticmethod
    def releaseConn(db_name, conn_obj):
        """将数据库连接还回连接池，一般由框架自动处理，不用自己调用
        """
        pool = MySqlManager.POOL.get(db_name)
        if pool:
#-#            info('release %s %s', db_name, conn_obj.getConn())
            pool.release(conn_obj.getConn())
            del conn_obj
#-#            MySqlManager.info(db_name)

    @staticmethod
    async def close():
        """关闭连接池连接
        """
        while 1:
            try:
                _db_name, _pool = MySqlManager.POOL.popitem()
#-#                info('mysql pool stat: %s total %s free %s', _db_name, _pool.size, _pool.freesize)
            except KeyError:
                break
            else:
                _pool.close()
                await _pool.wait_closed()
                info('pool %s closed %s', _db_name, _pool)


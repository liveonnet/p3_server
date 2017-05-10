#coding=utf8
""" https://aioredis.readthedocs.io/en/v0.2.9/api_reference.html
"""
#-#import asyncio
import json
from datetime import date
import aioredis
#-#from asyncio import sleep
from asyncio import Lock
#-#from asyncio import wait_for
#-#from asyncio import TimeoutError
#-#from asyncio import Task
from applib.conf_lib import conf
from applib.tools_lib import pcformat
from applib.tools_lib import CJsonEncoder
from applib.applog import app_log
info, debug, error, warn = app_log.info, app_log.debug, app_log.error, app_log.warning
pcformat


class K(object):
    """缓存key定义
    """
    _UINFO_ = '_U_I_'


class Redis(object):
    """redis连接封装

    提供额外的high level功能
    """
    def __init__(self, conn):
        self.conn = conn

    def __getattr__(self, name):
        """直接访问底层redis连接的方法
        """
        obj = getattr(self.conn, name)
        if obj:
#-#            info('%s found in redis conn obj', repr(name))
            return obj
        raise AttributeError('can\'t find attribute %s in %s', repr(name), self)

    async def getObj(self, key):
        """获取json对象
        """
        s = await self.conn.get(key)
        if s:
            return json.loads(s.decode('utf8'))
        return None

    async def setObj(self, key, obj, ex):
        """保存json对象
        """
        s = json.dumps(obj, cls=CJsonEncoder)
        await self.conn.set(key, s, expire=ex)

    async def checkCounting(self, key, interval, default_cooltime=1, onmonth=0):
        """ 计数器功能

        只适用于累计不跨天的计数 间隔检查
        """
        today = str(date.today()) if not onmonth else str(date.today())[:7]
        r_cool_key = key + "_" + today
        rcooltime = await self.conn.incr(r_cool_key)
        if rcooltime == 1:
            await self.conn.expire(r_cool_key, interval)
        if default_cooltime != 1:
            if rcooltime > default_cooltime:
                return True
        elif rcooltime != 1:
            return True
        return False

    async def delCounting(self, key, onmonth=0):
        """删除 ``get_counting(...)`` 创建的计数器
        """
        today = str(date.today()) if not onmonth else str(date.today())[:7]
        r_cool_key = key + "_" + today
        await self.conn.delete(r_cool_key)

    async def getHashAllObj(self, name):
        """获取名为 ``name`` 的hash 的键和值，以dict格式返回
        支持值为非字符串对象
        """
        ret = {}
        d = await self.con.hgetall(name)
        for _k, _v in d.iteritems():
            try:
                ret[_k] = json.loads(_v.decode('utf8'))
            except:
                info('%s %s', _k, pcformat(_v), exc_info=True)
                try:
                    _tmp = _v.replace("'", '"')
                    _obj = json.loads(_tmp.decode('utf8'))
                    ret[_k] = _obj
                except:
                    info('%s %s', _k, pcformat(_tmp), exc_info=True)
                    ret[_k] = _v
        return ret

    async def getHashObjValue(self, name, key):
        """获取名为 ``name`` 的hash中key为 ``key`` 的值
        支持值为非字符串对象
        """
        s = await self.conn.hget(name, key)
        if s:
            try:
                s = json.loads(s.decode('utf8'))
            except:
                try:
                    _tmp = s.replace("'", '"')
                    s = json.loads(_tmp.decode('utf8'))
                except:
                    error('name %s key %s', name, key, exc_info=True)
        return s

    async def getHashObjMultiValue(self, name, l_key):
        """取名为 ``name`` 的hash中多个key的值，以列表形式返回。``l_key`` 为包含多个key的列表
        支持值为非字符串对象
        """
        l_s = await self.conn.hmget(name, l_key)
        l_rslt = []
        for _i, s in enumerate(l_s):
            if s:
                try:
                    s = json.loads(s)
                except:
                    try:
                        _tmp = s.replace("'", '"')
                        s = json.loads(_tmp)
                    except:
                        s = None
                        error('name %s key %s', name, l_key[_i], exc_info=True)
            l_rslt.append(s)
        return l_rslt

    async def setHashObjValue(self, name, key, value, ex=None):
        """设置名为 ``name`` 的hash中key为 ``key`` 的值为 ``value``
        支持值为非字符串对象
        """
        s = value
        if s:
            try:
                _tmp = json.dumps(s, cls=CJsonEncoder)
                s = _tmp
            except:
                error('', exc_info=True)
                pass
        ret = await self.conn.hset(name, key, s)
        if ex:
            await self.conn.expire(name, ex)
        return ret

    async def setHashAllObj(self, name, dict_obj, ex=None):
        """设置名为 ``name`` 的hash 的键和值为 ``dict_obj`` 中的键和值
        支持值为非字符串对象
        """
        _obj = {}
        for _k, _v in dict_obj.iteritems():
            try:
                _tmp = json.dumps(_v, cls=CJsonEncoder)
            except:
                _tmp = _v
            _obj[_k] = _tmp
        ret = await self.conn.hmset(name, _obj)
        if ex:
            await self.conn.expire(name, ex)
        return ret

    def getConn(self):
        """获取底层真正的redis连接对象
        """
        return self.conn


class RedisManager(object):
    """aioredis连接池管理封装，支持缓存库自命名
    """
    POOL = {}
    LOCK = Lock()

    @staticmethod
    async def getConn(redis_name='default'):
        """从连接池中获取redis连接
        """
        pool = RedisManager.POOL.get(redis_name)
        if not pool:
            with (await RedisManager.LOCK):
                pool = RedisManager.POOL.get(redis_name)
                if not pool:
                    cfg = conf['cache'][redis_name]
                    info('loop: %s', conf['loop'])
                    pool = await aioredis.create_pool((cfg['host'], cfg['port']), db=cfg['db'], password=cfg['password'] or None, minsize=0, maxsize=500, loop=conf['loop'])
                    RedisManager.POOL[redis_name] = pool

#-#        nr_try = 1
#-#        while 1:
#-#            pool = RedisManager.POOL.get(redis_name)
#-#            if pool:
#-#                break
#-#            try:
#-#                await wait_for(RedisManager.LOCK.acquire(), 0.1)
#-#            except TimeoutError:
#-#                info('%s %s timeout waiting for lock %s', id(Task.current_task()), nr_try, id(RedisManager.LOCK))
#-#                await sleep(0.1)
#-#                nr_try += 1
#-#            else:
#-#                if nr_try > 1:
#-#                    info('xxxxxxxxx %s %s %s', id(Task.current_task()), nr_try, id(pool))
#-#                try:
#-#                    pool = RedisManager.POOL.get(redis_name)  # double check
#-#                    if pool:
#-#                        break
#-#                    cfg = conf['cache'][redis_name]
#-#                    pool = await aioredis.create_pool((cfg['host'], cfg['port']), db=cfg['db'], password=cfg['password'] or None, minsize=0, maxsize=500, loop=conf['loop'])
#-#                    RedisManager.POOL[redis_name] = pool
#-#                finally:
#-#                    try:
#-#                        RedisManager.LOCK.release()
#-#                    except RuntimeError:
#-#                        info('lock %s already in unlocked stat ?', RedisManager.LOCK)
#-#                    finally:
#-#                        break

        conn = await pool.acquire()
        conn_obj = Redis(conn)
#-#        info('acquired %s %s', redis_name, conn)
#-#        RedisManager.info(redis_name)
        return conn_obj

    @staticmethod
    def info(redis_name='default'):
        pool = RedisManager.POOL[redis_name]
        info('redis pool stat: %s total %s free %s', redis_name, pool.size, pool.freesize)

    @staticmethod
    def releaseConn(redis_name, conn_obj):
        """将redis连接还回连接池，一般由框架自动处理，不用自己调用
        """
        pool = RedisManager.POOL.get(redis_name)
        if pool:
#-#            info('release %s %s', redis_name, conn_obj.getConn())
#-#            info('redis pool stat: %s total %s free %s', redis_name, pool.size, pool.freesize)
            pool.release(conn_obj.getConn())
            del conn_obj
#-#            RedisManager.info(redis_name)

    @staticmethod
    async def close():
        """关闭连接池连接
        """
        while 1:
            try:
                _redis_name, _pool = RedisManager.POOL.popitem()
                info('redis pool stat: %s total %s free %s', _redis_name, _pool.size, _pool.freesize)
            except KeyError:
                break
            else:
                _pool.close()
                await _pool.wait_closed()
                info('pool %s closed %s %s', _redis_name, _pool, _pool.closed)



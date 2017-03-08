import json
from functools import partial
#-#from functools import wraps
import time
#-#from datetime import date
#-#from datetime import datetime
from aiohttp import web
from asyncio import CancelledError
#-#from asyncio import iscoroutine
from asyncio import iscoroutinefunction
from applib.tools_lib import CJsonEncoder
from applib.conf_lib import conf
from applib.db_lib import MySqlManager
from applib.cache_lib import RedisManager
from applib.applog import app_log
info, debug, error, warn = app_log.info, app_log.debug, app_log.error, app_log.warning
conf


class CommonHandler(object):
    """资源管理类
    """
    def __init__(self, req):
        self.request = req
        self.db = {}
        self.cache = {}

    async def getDB(self, db_name='default'):
        """维护本次请求用到的数据库连接
        """
        conn_obj = self.db.get(db_name)
        if not conn_obj:
            conn_obj = await MySqlManager.getConn(db_name)
            self.db[db_name] = conn_obj
        else:
            info('hit per-request conn %s', conn_obj)
        return conn_obj

    async def getCache(self, cache_name):
        """维护本次请求用到的缓存连接
        """
        conn_obj = self.cache.get(cache_name)
        if not conn_obj:
            conn_obj = await RedisManager.getConn(cache_name)
            self.cache[cache_name] = conn_obj
        else:
            info('hit per-request conn %s', conn_obj)
        return conn_obj

    def clean(self):
        """释放本次请求用到的数据库连接、缓存连接
        """
        while 1:
            try:
                _db_name, _conn = self.db.popitem()
            except KeyError:
                break
            else:
                MySqlManager.releaseConn(_db_name, _conn)

        while 1:
            try:
                _cache_name, _conn = self.cache.popitem()
            except KeyError:
                break
            else:
                RedisManager.releaseConn(_cache_name, _conn)


dumpsex = partial(json.dumps, cls=CJsonEncoder)


#-#def route(method, path):
#-#    def decorator(func):
#-#        @wraps(func)
#-#        def wrapper(*args, **kw):
#-#            return func(*args, **kw)
#-#        wrapper.__method__ = method
#-#        wrapper.__route__ = path
#-#        return wrapper
#-#    return decorator


def route(path):
    u'''设置接口处理类的路径(修改类属性 ``PATH`` )
    '''
    def wrapper(cls):
        cls.PATH = path
        return cls
    return wrapper


class BaseHandler(object):
    """请求的基类

    根据不同http类型请求调用相应的响应函数
    GET 获取/查询
    POST 创建
    PUT 更新(提供所有字段信息)
    PATCH 更新(提供部分字段信息)
    DELETE 删除

    """
    def writeJson(self, obj, code=0, msg=''):
        """返回json格式数据
        """
        if not obj:
            obj = {}
        obj.update({'rcode': code, 'rmsg': msg})
        return web.json_response(obj, dumps=dumpsex)

    async def handle(self, request):
        u'''挂通用处理模块
        保证资源释放
        '''
        a = time.time()
        request['common'] = CommonHandler(request)
        method = request.method.lower()
        func = getattr(self, method)
        resp = None
        try:
            if func:
                resp = func(request)
                if iscoroutinefunction(func):
                    try:
                        resp = await resp
                    except CancelledError:
                        info('user canceled')
                        resp = web.Response(text="")
            else:
                warn('func %s not found in %s', method, self)
                resp = web.Response(text='hehe')
        finally:
            request['common'].clean()
            info('%.3fms', (time.time() - a) * 1000)

        return resp


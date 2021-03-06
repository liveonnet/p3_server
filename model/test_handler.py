#-#from aiohttp import web
#-#from asyncio import CancelledError
from random import randrange
#-#from random import choice
from aiohttp import web
#-#from asyncio import sleep
from lib.tools_lib import pcformat
from aiohttp.web import View
#-#from lib.tools_lib import check_wx_auth
#-#from lib.tools_lib import get_wx_auth
from lib.handler_lib import BaseHandler
from lib.handler_lib import route
from lib.cache_lib import K
from lib.applog import app_log
info, debug, error, warn = app_log.info, app_log.debug, app_log.error, app_log.warning
pcformat


@route('/user/{uid}')
class UserHandler(BaseHandler):
#-#    def __init__(self):
        # uc -ACNqse "select uid from z_user" > /tmp/1.csv
#-#        self.l_uid = [int(x) for x in open('/tmp/1.csv').read().split('\n') if x]
#-#        self.l_uid = self.l_uid[:400]
#-#        info('l_uid %s', len(self.l_uid))

    async def get(self):
#-#        uid = request.match_info.get('uid', '0')
        uid = randrange(10000000, 99999999)

#-#        uid = choice(self.l_uid)
        c_k = K._UINFO_ + str(uid)
        r = await self.getCache('ad')
        data = await r.getObj(c_k)
        if data is None:
            conn = await self.getDB('uc_read')
            data = await conn.getOne('select * from z_user where uid=%s', (uid, ), 'dict')
            await r.setObj(c_k, data, 60)
        else:
            info('cache hit %s', c_k)
#-#            await sleep(3)

#-#        data = {'uid': uid}

        return self.writeJson(data)
#-#        return web.Response(text="this is aio project.")


@route('/empty')
class EmptyHandler(View):
    async def get(self):
#-#        info('hehe %s', id(self))
#-#        info('self %s', pcformat(dir(self.request)))
#-#        info(pcformat(list(x for x in dir(self) if not x.startswith('_'))))
        return web.Response(text='ok')


@route('/test')
class TestHandler(BaseHandler):
    async def get(self):
        return web.Response(text='test ok')



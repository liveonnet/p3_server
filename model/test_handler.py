#-#from aiohttp import web
#-#from asyncio import CancelledError
#-#from random import randrange
from random import choice
from aiohttp import web
#-#from asyncio import sleep
from applib.tools_lib import pcformat
from applib.handler_lib import BaseHandler
from applib.handler_lib import route
from applib.cache_lib import K
from applib.applog import app_log
info, debug, error, warn = app_log.info, app_log.debug, app_log.error, app_log.warning
pcformat


@route('/user/{uid}')
class TestHandler(BaseHandler):
    def __init__(self):
        super().__init__()
        # uc -ACNqse "select uid from z_user" > /tmp/1.csv
        self.l_uid = [int(x) for x in open('/tmp/1.csv').read().split('\n') if x]
        self.l_uid = self.l_uid[:400]
        info('l_uid %s', len(self.l_uid))

    async def get(self, request):
#-#        uid = request.match_info.get('uid', '0')
#-#        uid = randrange(10000000, 99999999)

        uid = choice(self.l_uid)
        c_k = K._UINFO_ + str(uid)
        r = await request['common'].getCache('ad')
        data = await r.getObj(c_k)
        if data is None:
            conn = await request['common'].getDB('uc_read')
            data = await conn.getOne('select * from z_user where uid=%s', (uid, ), 'dict')
            await r.setObj(c_k, data, 60)
        else:
            info('cache hit %s', c_k)
#-#            await sleep(3)

#-#        data = {'uid': uid}

        return self.writeJson(data)
#-#        return web.Response(text="this is aio project.")


@route('/empty')
class EmptyHandler(BaseHandler):
    async def get(self, request):
        return web.Response(text='ok')

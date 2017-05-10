#-#from aiohttp import web
#-#from asyncio import CancelledError
#-#from random import randrange
#-#from random import choice
from aiohttp import web
#-#from asyncio import sleep
from applib.wx_lib import WXManager
from applib.tools_lib import pcformat
from applib.tools_lib import check_wx_auth
from applib.conf_lib import conf
from applib.tools_lib import get_wx_auth
from applib.handler_lib import BaseHandler
from applib.handler_lib import route
#-#from applib.cache_lib import K
from applib.applog import app_log
info, debug, error, warn = app_log.info, app_log.debug, app_log.error, app_log.warning
pcformat


@route('/wx_auth')
class WxHandler(BaseHandler):
    async def get(self, request):
        ch = request['common']
        (sig, timestamp, nonce, echostr), l_err = ch.get_my_arg('signature', 'timestamp', 'nonce', 'echostr')
        token = conf['wx_token']
        if check_wx_auth(token, timestamp, nonce, sig):
            info('auth ok!')
            return web.Response(text=echostr)
        else:
            info('my sig %s', get_wx_auth(token, timestamp, nonce))
        return web.Response(text='test ok')

    async def post(self, request):
        ch = request['common']
        mgr = WXManager(conf['loop'], ch)
        request['wx_mgr'] = mgr  # 让外层负责释放资源

        (nonce, encrypt_type, msg_sign, timestamp), l_err = ch.get_my_arg('nonce required&bytes', 'encrypt_type required&bytes', 'msg_signature required&bytes', 'timestamp required&bytes')
        d = mgr.extractXml(nonce, encrypt_type, msg_sign, timestamp, await request.text())
#-#        info('decrypted msg:\n%s', pcformat(d))
        info('%s -> %s %s', d['FromUserName'], d['ToUserName'], d['Content'])
        reply = 'test%s' % d['Content']
        resp = mgr.createText(nonce, encrypt_type, d['FromUserName'], d['ToUserName'], reply)
        info('%s -> %s %s', d['ToUserName'], d['FromUserName'], reply)
#-#        info('resp: %s', resp)
        return web.Response(headers={'Content-Type': 'application/xml'}, text=resp)

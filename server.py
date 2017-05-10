#coding=utf8
"""http://aiohttp.readthedocs.io/en/stable/web_reference.html
"""


#-#import sys
import logging
import setproctitle
import asyncio
import uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
#-#import ssl
from aiohttp import web
from applib.conf_lib import conf
from applib.load_handler import setup_routes
from middleware import l_middleware
from applib.db_lib import MySqlManager
from applib.cache_lib import RedisManager
from applib.tools_lib import pcformat
pcformat
from applib.applog import app_log
info, debug, error, warn = app_log.info, app_log.debug, app_log.error, app_log.warning

setproctitle.setproctitle(conf['proc_title'])  # change process name...

loop = asyncio.get_event_loop()
if conf['debug']:
    info('start in debug mode')
    import aiohttp_debugtoolbar
    from aiohttp_debugtoolbar import toolbar_middleware_factory
    loop.set_debug(True)
    logging.basicConfig(level=logging.DEBUG)
    logging.captureWarnings(True)
#-#info('loop: %s', loop)
conf['loop'] = loop


async def on_prepare(request, response):
    pass
    response.headers['hehe'] = 'test'
#-#    info('before resp ...')

async def on_startup(app):
    info('starting ...')

async def on_shutdown(app):
    info('shuting down ...')

async def on_cleanup(app):
    info('cleaning up ...')
    await MySqlManager.close()
    await RedisManager.close()
#-#    info('cleaning up waiting ...')
#-#    await asyncio.sleep(2)
    info('cleaning up done')

if conf['debug']:
    app = web.Application(loop=loop, middlewares=[toolbar_middleware_factory] + l_middleware)
    aiohttp_debugtoolbar.setup(app)
else:
    app = web.Application(loop=loop, middlewares=l_middleware)


app.on_startup.append(on_startup)
app.on_response_prepare.append(on_prepare)
app.on_shutdown.append(on_shutdown)
app.on_cleanup.append(on_cleanup)
app['cfg'] = conf
#-#info('conf: %s', pcformat(app['cfg']))

#-#info('resources: ')
#-#for _r in app.router.resources():
#-#    info('\t%s', _r)
setup_routes(app)

#-#ssl_context = ssl.SSLContext(ssl.PROTOCOL_SSLv23)
#-#ssl_context.load_cert_chain(conf['ssl_crt'], conf['ssl_key'])  # load certificate and private key data
#-#web.run_app(app, host=conf['host'], port=conf['port'], ssl_context=ssl_context, access_log=app_log, access_log_format='[code %s] %t [pid %P] [remote %{X-Real-Ip}i] [resp %b/%O] "%r" %D microseconds')
web.run_app(app, host=conf['host'], port=conf['port'], access_log=app_log, access_log_format='[code %s] %t [pid %P] [remote %{X-Real-Ip}i] [resp %b/%O] "%r" %D microseconds')


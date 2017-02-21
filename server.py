#coding=utf8
"""http://aiohttp.readthedocs.io/en/stable/web_reference.html
"""


#-#import sys
import logging
import setproctitle
import asyncio
import uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
from aiohttp import web
from applib.conf_lib import conf
#-#from applib.handler_lib import BaseHandler
from model.test_handler import TestHandler
from model.test_handler import EmptyHandler
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
    app = web.Application(loop=loop, middlewares=[toolbar_middleware_factory])
    aiohttp_debugtoolbar.setup(app)
else:
    app = web.Application(loop=loop)


app.on_startup.append(on_startup)
app.on_response_prepare.append(on_prepare)
app.on_shutdown.append(on_shutdown)
app.on_cleanup.append(on_cleanup)
app['config'] = conf
info('conf: %s', pcformat(app['config']))
#-#test_hdl = TestHandler()
#-#app.router.add_get('/', test_hdl.handle)
#-#app.router.add_get('/{name}', test_hdl.handle)

app.router.add_route('*', '/user/{uid}', TestHandler().handle)
app.router.add_route('*', '/empty', EmptyHandler().handle)

#-#app.router.add_get('/user/xxx', test_hdl.get)
#-#app.router.add_static('/prefix', path_to_static_folder, show_index=True, follow_symlinks=True)
#-#info('resources: ')
#-#for _r in app.router.resources():
#-#    info('\t%s', _r)

web.run_app(app, port=conf['port'], access_log=app_log, access_log_format='[code %s] %t [pid %P] [remote %a] [resp %b/%O] "%r" %D microseconds')
#-#web.run_app(app, host='127.0.0.1', port=int(sys.argv[1]))

